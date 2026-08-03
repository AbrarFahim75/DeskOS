"""MVP rule-based context inference.

Rules are intentionally simple and explicit (no learned weights) so they
are auditable and debuggable while the rest of the pipeline is validated.
TODO: replace with a learned/LLM-backed ContextInferer once enough labeled
usage data exists - this class's interface will not need to change.
"""
from __future__ import annotations

import time
from dataclasses import replace

from deskos.config.settings import ContextEngineSettings
from deskos.core import ContextSnapshot, ContextState, Event, EventType

# MVP label -> state rules. First matching rule wins; order matters.
# "book" alone implies STUDYING (COCO has no "notebook" class to pair it
# with - a pragmatic MVP approximation).
_LABEL_STATE_RULES: tuple[tuple[frozenset[str], ContextState], ...] = (
    (frozenset({"laptop", "keyboard"}), ContextState.CODING),
    (frozenset({"book"}), ContextState.STUDYING),
    (frozenset({"coffee_cup"}), ContextState.BREAK),
)


class RuleBasedContextEngine:
    """Tracks recently-seen event labels and maps them to a ContextState
    via `_LABEL_STATE_RULES`. Implements ContextInferer structurally.
    """

    def __init__(self, settings: ContextEngineSettings) -> None:
        self._settings = settings
        self._active_labels: dict[str, float] = {}  # label -> last-seen timestamp
        self._state_started_at = time.time()
        self._current = ContextSnapshot(state=ContextState.UNKNOWN, confidence=0.0)

    def update(self, events: list[Event]) -> ContextSnapshot:
        now = time.time()
        for event in events:
            if event.type == EventType.OBJECT_APPEARED:
                self._active_labels[event.label] = now
            elif event.type == EventType.OBJECT_DISAPPEARED:
                self._active_labels.pop(event.label, None)

        # Expire labels no AWAY-timeout has been configured against, so a
        # stale "coffee_cup" from an hour ago doesn't pin BREAK forever.
        stale_cutoff = now - self._settings.away_timeout_sec
        self._active_labels = {
            label: ts for label, ts in self._active_labels.items() if ts >= stale_cutoff
        }

        inferred_state, confidence = self._infer()
        if confidence < self._settings.min_confidence:
            # Not confident enough to revise our belief. Re-report the current
            # one, but never re-report it as a transition: a transition happens
            # once, and repeating the flag would make Knowledge log the same
            # state change on every tick.
            self._current = replace(self._current, is_transition=False)
            return self._current

        state_changed = inferred_state != self._current.state
        if state_changed:
            self._state_started_at = now

        self._current = ContextSnapshot(
            state=inferred_state,
            confidence=confidence,
            timestamp=now,
            duration_in_state=now - self._state_started_at,
            triggering_events=tuple(events),
            previous_context=self._current if state_changed else self._current.previous_context,
            is_transition=state_changed,
        )
        return self._current

    def current(self) -> ContextSnapshot:
        return self._current

    def _infer(self) -> tuple[ContextState, float]:
        active = set(self._active_labels.keys())

        if not active:
            return ContextState.AWAY, 0.9

        # "Empty chair" isn't a single detectable object (COCO has no such
        # class) - it's chair present + no person seen, so this is inferred
        # here rather than as a Perception label.
        if "chair" in active and "person" not in active:
            return ContextState.AWAY, 0.8

        for required_labels, state in _LABEL_STATE_RULES:
            if required_labels.issubset(active):
                # Simple confidence heuristic: exact single-signal rules are
                # slightly less certain than multi-signal corroboration.
                confidence = 0.7 if len(required_labels) == 1 else 0.85
                return state, confidence

        return ContextState.UNKNOWN, 0.0
