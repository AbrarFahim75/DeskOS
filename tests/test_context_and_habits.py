"""Context transitions and the habit figures derived from them.

Milestone 1 fixed a bug where every loop tick was written to history as if
it were a state change. That made a "session" exactly one tick long, so
average_session_duration reported the tick interval rather than behaviour.
"""
from __future__ import annotations

from deskos.config.settings import ContextEngineSettings
from deskos.context.context_engine import RuleBasedContextEngine
from deskos.core import ContextSnapshot, ContextState, Event, EventType
from deskos.knowledge.habit_store import InferredHabitStore
from deskos.knowledge.history_store import InMemoryHistoryStore

SETTINGS = ContextEngineSettings(min_confidence=0.6, away_timeout_sec=60.0)


def appeared(label: str) -> list[Event]:
    return [Event(type=EventType.OBJECT_APPEARED, label=label, confidence=0.9)]


def test_first_inference_counts_as_a_transition():
    engine = RuleBasedContextEngine(SETTINGS)

    context = engine.update(appeared("book"))

    assert context.state == ContextState.STUDYING
    assert context.is_transition is True


def test_staying_in_the_same_state_is_not_a_transition():
    engine = RuleBasedContextEngine(SETTINGS)
    engine.update(appeared("book"))

    for _ in range(5):
        context = engine.update([])
        assert context.state == ContextState.STUDYING
        assert context.is_transition is False, "unchanged state must not re-log"


def test_changing_state_is_flagged_again():
    engine = RuleBasedContextEngine(SETTINGS)
    engine.update(appeared("book"))
    engine.update([])

    context = engine.update(
        [Event(type=EventType.OBJECT_DISAPPEARED, label="book", confidence=1.0)]
    )

    assert context.state == ContextState.AWAY
    assert context.is_transition is True


def test_only_transitions_reach_history():
    """The pipeline wiring in main.py, reproduced in miniature."""
    engine = RuleBasedContextEngine(SETTINGS)
    history = InMemoryHistoryStore()

    for events in [appeared("book"), [], [], [], []]:
        context = engine.update(events)
        if context.is_transition:
            history.record_context_transition(context)

    assert len(history.get_context_transitions()) == 1


def test_average_session_duration_measures_real_sessions():
    """A one-hour session must report roughly one hour, not one tick."""
    history = InMemoryHistoryStore()
    start = 1_000.0

    history.record_context_transition(
        ContextSnapshot(state=ContextState.CODING, confidence=0.9, timestamp=start)
    )
    history.record_context_transition(
        ContextSnapshot(state=ContextState.BREAK, confidence=0.9, timestamp=start + 3600)
    )

    habits = InferredHabitStore(history)

    assert habits.average_session_duration("CODING") == 3600.0


def test_acceptance_rate_ignores_small_samples():
    """Personalisation must not fire on a couple of interactions."""
    from deskos.core import FeedbackType, SuggestionFeedback, SuggestionType

    history = InMemoryHistoryStore()
    for _ in range(3):
        history.record_feedback(
            SuggestionFeedback(
                suggestion_type=SuggestionType.TAKE_BREAK,
                feedback=FeedbackType.NOT_HELPFUL,
            )
        )

    habits = InferredHabitStore(history)

    assert habits.acceptance_rate("TAKE_BREAK") is None
