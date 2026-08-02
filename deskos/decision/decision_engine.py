"""MVP Decision Engine.

Enforces, in order: confidence threshold -> cooldown/repetition suppression.
Anything that survives both becomes an Action. This is deliberately the
only place these rules live (see product principles 1-3, 6).
"""
from __future__ import annotations

import time

from deskos.config.settings import DecisionEngineSettings
from deskos.core import Action, ActionType, Suggestion, SuggestionType, UserValue
from deskos.decision.interfaces import DecisionMaker
from deskos.knowledge.interfaces import HistoryStore

_SUGGESTION_TO_ACTION: dict[SuggestionType, ActionType] = {
    SuggestionType.TAKE_BREAK: ActionType.SHOW_WIDGET,
    SuggestionType.RESUME_FOCUS: ActionType.SHOW_WIDGET,
    SuggestionType.PAUSE_TIMER: ActionType.PAUSE_TIMER,
    SuggestionType.RESUME_TIMER: ActionType.RESUME_TIMER,
    SuggestionType.PLAY_FOCUS_MUSIC: ActionType.PLAY_MUSIC,
}

# Suggestion types where doing nothing has no real cost — MVP's proxy for
# "would the user lose meaningful value if we stayed silent?". TODO: make
# this data-driven (e.g. weigh UserValue + habit context) once enough
# feedback exists; a static allowlist is a deliberately conservative start.
_LOW_STAKES_IF_SKIPPED: frozenset[SuggestionType] = frozenset({
    SuggestionType.RESUME_FOCUS,
})


class DecisionEngine(DecisionMaker):
    def __init__(
        self,
        settings: DecisionEngineSettings,
        history: HistoryStore,
    ) -> None:
        self._settings = settings
        self._history = history

    def decide(self, suggestions: list[Suggestion]) -> list[Action]:
        actions: list[Action] = []

        for suggestion in suggestions:
            if suggestion.confidence < self._settings.min_confidence_to_act:
                continue  # rule 3: only react with high confidence

            since_last = self._history.seconds_since_last_suggestion(suggestion.type)
            if since_last is not None and since_last < self._settings.suggestion_cooldown_sec:
                continue  # rules 1 & 2: never repeat, never interrupt

            if not self._passes_user_value_check(suggestion):
                continue  # golden rule: don't act unless doing nothing costs the user something real

            action_type = _SUGGESTION_TO_ACTION.get(suggestion.type)
            if action_type is None:
                continue  # TODO: extend mapping as new SuggestionTypes land

            self._history.record_suggestion_shown(suggestion.type, time.time())
            actions.append(
                Action(
                    type=action_type,
                    payload={
                        "suggestion_type": suggestion.type.name,
                        "reason": suggestion.reason,
                        "mood": suggestion.mood.name,
                    },
                    approval_reason=self._approval_reason(suggestion, since_last),
                )
            )

        return actions

    def _passes_user_value_check(self, suggestion: Suggestion) -> bool:
        """"If I do nothing right now, will the user lose meaningful
        value?" A LOW-value suggestion for a low-stakes type answers "no" —
        prefer silence.
        """
        if suggestion.type in _LOW_STAKES_IF_SKIPPED and suggestion.estimated_value == UserValue.LOW:
            return False
        return True

    def _approval_reason(self, suggestion: Suggestion, since_last: float | None) -> str:
        """Internal-only explainability string — never shown to the user."""
        reasons = []
        if suggestion.confidence >= 0.9:
            reasons.append("high confidence")
        if since_last is None:
            reasons.append("first occurrence")
        else:
            reasons.append("cooldown expired")
        if suggestion.estimated_value == UserValue.HIGH:
            reasons.append("high estimated value")
        return ", ".join(reasons)
