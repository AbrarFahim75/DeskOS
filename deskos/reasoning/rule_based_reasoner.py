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
}

_STATE_VALUE: dict[ContextState, UserValue] = {
    ContextState.BREAK: UserValue.MEDIUM,
    ContextState.AWAY: UserValue.HIGH,
    ContextState.CODING: UserValue.LOW,
    ContextState.STUDYING: UserValue.MEDIUM,
}

_STATE_MOOD: dict[ContextState, WidgetMood] = {
    ContextState.BREAK: WidgetMood.POSITIVE,
    ContextState.AWAY: WidgetMood.IMPORTANT,
    ContextState.CODING: WidgetMood.NEUTRAL,
    ContextState.STUDYING: WidgetMood.POSITIVE,
}


class RuleBasedReasoner(Reasoner):
    def reason(self, context: ContextSnapshot, habits: HabitStore) -> list[Suggestion]:
        suggestion_type = _STATE_SUGGESTION.get(context.state)
        if suggestion_type is None:
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
                reason=f"Context inferred as {context.state.name}",
            )
        ]
