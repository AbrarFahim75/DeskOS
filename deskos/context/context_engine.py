"""Rule-based context inference, presence-first.

Design note, learned from running DeskOS against a real webcam:

A laptop's built-in camera cannot see the laptop it is mounted on, nor the
keyboard, nor the desk surface. Measured on a real desk, `person` scored
0.89 while `laptop` scored 0.12, below a background couch. The original
rules required `laptop + keyboard` for CODING, which made that state
literally unreachable on the most common hardware in existence, and left
`person` (the one reliable signal) out of the rules entirely.

So presence is now the foundation: if a person is at the desk, DeskOS says
PRESENT and stops pretending to know more. Objects *refine* that into
CODING/STUDYING/BREAK when a camera can actually see them, which is the
case for an external camera pointed at the desk from the side.

Two further corrections, both about not overclaiming:

- Startup is UNKNOWN, not AWAY. Seeing nothing in the first seconds means
  "DeskOS has not looked yet", not "the user has left". Previously an
  empty first frame asserted AWAY at 0.90 confidence.
- AWAY requires a *sustained* absence. A person leaning out of frame for a
  moment is not gone.

TODO: replace with a learned/LLM-backed ContextInferer once enough labeled
usage data exists - this class's interface will not need to change.
"""
from __future__ import annotations

import time

from deskos.config.settings import ContextEngineSettings
from deskos.core import ContextSnapshot, ContextState, Event, EventType

_PERSON = "person"

# Object refinements applied *on top of* a confirmed person. Each maps the
# labels that must all be present to the state they imply. First match wins,
# so order from most specific to least.
_REFINEMENTS: tuple[tuple[frozenset[str], ContextState, float], ...] = (
    (frozenset({"laptop", "keyboard"}), ContextState.CODING, 0.85),
    (frozenset({"book"}), ContextState.STUDYING, 0.80),
    (frozenset({"coffee_cup"}), ContextState.BREAK, 0.80),
)

_PRESENT_CONFIDENCE = 0.75   # "you are here" is knowable; the activity is not
_AWAY_CONFIDENCE = 0.85


class RuleBasedContextEngine:
    """Infers a ContextState from recently confirmed event labels.

    Implements ContextInferer structurally.
    """

    def __init__(self, settings: ContextEngineSettings) -> None:
        self._settings = settings
        self._active_labels: dict[str, float] = {}  # label -> last-seen timestamp
        # Set on the first update(), not here. Construction happens before
        # the camera opens and before YOLO lazily loads its model, which
        # takes seconds; measuring warm-up from construction let it expire
        # before a single frame had been seen, and DeskOS declared AWAY
        # while the very first frame showed a person.
        self._first_observation_at: float | None = None
        self._state_started_at = time.time()
        self._person_last_seen_at: float | None = None
        self._current = ContextSnapshot(state=ContextState.UNKNOWN, confidence=0.0)

    def update(self, events: list[Event]) -> ContextSnapshot:
        now = time.time()
        if self._first_observation_at is None:
            self._first_observation_at = now
        for event in events:
            if event.type == EventType.OBJECT_APPEARED:
                self._active_labels[event.label] = now
            elif event.type == EventType.OBJECT_DISAPPEARED:
                self._active_labels.pop(event.label, None)

        # Expire labels not seen recently, so a stale "coffee_cup" from an
        # hour ago does not pin BREAK forever.
        stale_cutoff = now - self._settings.away_timeout_sec
        self._active_labels = {
            label: ts for label, ts in self._active_labels.items() if ts >= stale_cutoff
        }
        if _PERSON in self._active_labels:
            self._person_last_seen_at = now

        state, confidence = self._infer(now)

        # A weak reading must never be reported as a strong old belief. The
        # previous implementation silently re-reported the last confident
        # state, which let a startup AWAY(0.90) persist forever once every
        # later tick fell below the threshold.
        if confidence < self._settings.min_confidence:
            state, confidence = ContextState.UNKNOWN, confidence

        state_changed = state != self._current.state
        if state_changed:
            self._state_started_at = now

        self._current = ContextSnapshot(
            state=state,
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

    def _infer(self, now: float) -> tuple[ContextState, float]:
        """Return the most specific state the evidence actually supports."""
        active = set(self._active_labels)

        if _PERSON in active:
            for required, state, confidence in _REFINEMENTS:
                if required.issubset(active):
                    return state, confidence
            return ContextState.PRESENT, _PRESENT_CONFIDENCE

        # No person visible. Distinguish "not looked yet" from "left".
        if self._person_last_seen_at is None:
            observing_for = now - (self._first_observation_at or now)
            if observing_for < self._settings.warmup_sec:
                return ContextState.UNKNOWN, 0.0  # still opening our eyes
            # Observed long enough with no person ever seen: genuinely away.
            return ContextState.AWAY, _AWAY_CONFIDENCE

        if (now - self._person_last_seen_at) >= self._settings.away_timeout_sec:
            return ContextState.AWAY, _AWAY_CONFIDENCE

        # Briefly out of frame: hold the previous belief but do not
        # strengthen it. Leaning back is not leaving.
        return self._current.state, self._current.confidence
