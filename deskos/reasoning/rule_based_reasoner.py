"""MVP rule-based Reasoner.

One suggestion per context state, mirroring the product philosophy examples
(coffee -> "Break?", empty chair -> pause timer). TODO: replace/augment
with an LLM-backed Reasoner once Decision-layer gating has been validated
to actually suppress noise well - Reasoning should stay free to propose,
Decision stays the sole gatekeeper.
"""
from __future__ import annotations

from deskos.core import (
    ContextSnapshot,
    ContextState,
    Suggestion,
    SuggestionType,
    UserValue,
    WidgetMood,
)
from deskos.knowledge.interfaces import HabitStore
from deskos.reasoning.interfaces import Reasoner

_STATE_SUGGESTION: dict[ContextState, SuggestionType] = {
    ContextState.BREAK: SuggestionType.TAKE_BREAK,
    ContextState.AWAY: SuggestionType.PAUSE_TIMER,
    ContextState.CODING: SuggestionType.RESUME_TIMER,
    ContextState.STUDYING: SuggestionType.PLAY_FOCUS_MUSIC,
    # PRESENT means "at the desk, activity unknown". The only thing worth
    # saying about bare presence is that it has gone on a long time, so the
    # suggestion is gated on duration in `reason()` rather than fired on
    # sight. UNKNOWN maps to nothing at all: DeskOS has no business
    # speaking before it knows anything.
    ContextState.PRESENT: SuggestionType.TAKE_BREAK,
}

_STATE_VALUE: dict[ContextState, UserValue] = {
    ContextState.PRESENT: UserValue.MEDIUM,
    ContextState.BREAK: UserValue.MEDIUM,
    ContextState.AWAY: UserValue.HIGH,
    ContextState.CODING: UserValue.LOW,
    ContextState.STUDYING: UserValue.MEDIUM,
}

_STATE_MOOD: dict[ContextState, WidgetMood] = {
    ContextState.PRESENT: WidgetMood.POSITIVE,
    ContextState.BREAK: WidgetMood.POSITIVE,
    ContextState.AWAY: WidgetMood.IMPORTANT,
    ContextState.CODING: WidgetMood.NEUTRAL,
    ContextState.STUDYING: WidgetMood.POSITIVE,
}


class RuleBasedReasoner(Reasoner):
    def __init__(self, long_session_sec: float = 2700.0) -> None:
        self._long_session_sec = long_session_sec

    def reason(self, context: ContextSnapshot, habits: HabitStore) -> list[Suggestion]:
        suggestion_type = _STATE_SUGGESTION.get(context.state)
        if suggestion_type is None:
            return []

        # Bare presence only becomes worth mentioning once it has lasted.
        # "You are at your desk" is not news; "you have been at your desk
        # for 45 minutes without a break" is.
        if (
            context.state == ContextState.PRESENT
            and context.duration_in_state < self._long_session_sec
        ):
            return []

        # Learn from explicit feedback: a suggestion type the user has
        # repeatedly marked NOT_HELPFUL should stop being proposed, once
        # there's enough signal to trust it (see HabitStore's min-sample
        # guard) - this is what makes reasoning personalize over time.
        acceptance = habits.acceptance_rate(suggestion_type.name)
        if acceptance is not None and acceptance < 0.3:
            return []

        return [
            Suggestion(
                type=suggestion_type,
                context=context,
                confidence=context.confidence,
                estimated_value=_STATE_VALUE.get(context.state, UserValue.MEDIUM),
                mood=_STATE_MOOD.get(context.state, WidgetMood.NEUTRAL),
                reason=self._describe(context),
            )
        ]

    def _describe(self, context: ContextSnapshot) -> str:
        if context.state == ContextState.PRESENT:
            minutes = int(context.duration_in_state // 60)
            return f"At the desk for {minutes} minutes without a break"
        return f"Context inferred as {context.state.name}"
