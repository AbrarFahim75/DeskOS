"""MVP Decision Engine.

Enforces, in order: confidence threshold -> cooldown/repetition suppression.
Anything that survives both becomes an Action. This is deliberately the
only place these rules live (see product principles 1-3, 6).

Decision is pure policy: it reads history to make a judgement but never
writes to it. Recording that a suggestion was *shown* happens in the
Services layer, once something was actually shown - otherwise a service
that fails or skips would still burn the cooldown on a suggestion the user
never saw.
"""
from __future__ import annotations

from deskos.config.settings import DecisionEngineSettings
from deskos.core import Action, ActionType, Suggestion, SuggestionType, UserValue
from deskos.decision.interfaces import DecisionMaker
from deskos.knowledge.interfaces import HistoryStore
from deskos.observability import SuggestionOutcome, SuppressionReason

_SUGGESTION_TO_ACTION: dict[SuggestionType, ActionType] = {
    SuggestionType.TAKE_BREAK: ActionType.SHOW_WIDGET,
    SuggestionType.RESUME_FOCUS: ActionType.SHOW_WIDGET,
    SuggestionType.PAUSE_TIMER: ActionType.PAUSE_TIMER,
    SuggestionType.RESUME_TIMER: ActionType.RESUME_TIMER,
    SuggestionType.PLAY_FOCUS_MUSIC: ActionType.PLAY_MUSIC,
}

# Suggestion types where doing nothing has no real cost - MVP's proxy for
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
        """Return the Actions approved from `suggestions`.

        The public contract is unchanged: only approved Actions come back.
        Use `evaluate()` when the rejections and their reasons are also
        wanted (diagnostics); `decide()` is `evaluate()` with the rejections
        dropped, so the two can never disagree.
        """
        return [action for action, _ in self.evaluate(suggestions) if action is not None]

    def evaluate(
        self, suggestions: list[Suggestion]
    ) -> list[tuple[Action | None, SuggestionOutcome]]:
        """Judge each suggestion, returning both the Action (or None) and an
        outcome record explaining approval or the reason for silence.
        """
        results: list[tuple[Action | None, SuggestionOutcome]] = []
        for suggestion in suggestions:
            results.append(self._judge(suggestion))
        return results

    def _judge(self, suggestion: Suggestion) -> tuple[Action | None, SuggestionOutcome]:
        stype = suggestion.type

        if suggestion.confidence < self._settings.min_confidence_to_act:
            return None, self._rejected(stype, SuppressionReason.LOW_CONFIDENCE)

        since_last = self._history.seconds_since_last_suggestion(stype)
        if since_last is not None and since_last < self._settings.suggestion_cooldown_sec:
            return None, self._rejected(stype, SuppressionReason.IN_COOLDOWN)

        if not self._passes_user_value_check(suggestion):
            return None, self._rejected(stype, SuppressionReason.LOW_USER_VALUE)

        action_type = _SUGGESTION_TO_ACTION.get(stype)
        if action_type is None:
            return None, self._rejected(stype, SuppressionReason.NO_ACTION_MAPPING)

        approval = self._approval_reason(suggestion, since_last)
        action = Action(
            type=action_type,
            payload={
                "suggestion_type": stype.name,
                "reason": suggestion.reason,
                "mood": suggestion.mood.name,
            },
            approval_reason=approval,
        )
        return action, SuggestionOutcome(suggestion_type=stype, approved=True, reason=approval)

    @staticmethod
    def _rejected(stype: SuggestionType, reason: SuppressionReason) -> SuggestionOutcome:
        return SuggestionOutcome(suggestion_type=stype, approved=False, reason=reason.name)

    def _passes_user_value_check(self, suggestion: Suggestion) -> bool:
        """"If I do nothing right now, will the user lose meaningful
        value?" A LOW-value suggestion for a low-stakes type answers "no" -
        prefer silence.
        """
        if suggestion.type in _LOW_STAKES_IF_SKIPPED and suggestion.estimated_value == UserValue.LOW:
            return False
        return True

    def _approval_reason(self, suggestion: Suggestion, since_last: float | None) -> str:
        """Internal-only explainability string - never shown to the user."""
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
