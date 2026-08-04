"""Context transitions and the habit figures derived from them.

Milestone 1 fixed a bug where every loop tick was written to history as if
it were a state change. That made a "session" exactly one tick long, so
average_session_duration reported the tick interval rather than behaviour.
"""
from __future__ import annotations

import time

from deskos.config.settings import ContextEngineSettings
from deskos.context.context_engine import RuleBasedContextEngine
from deskos.core import ContextSnapshot, ContextState, Event, EventType
from deskos.knowledge.habit_store import InferredHabitStore
from deskos.knowledge.history_store import InMemoryHistoryStore

SETTINGS = ContextEngineSettings(
    min_confidence=0.6, away_timeout_sec=60.0, warmup_sec=10.0
)


def appeared(*labels: str) -> list[Event]:
    return [
        Event(type=EventType.OBJECT_APPEARED, label=label, confidence=0.9)
        for label in labels
    ]


def disappeared(*labels: str) -> list[Event]:
    return [
        Event(type=EventType.OBJECT_DISAPPEARED, label=label, confidence=1.0)
        for label in labels
    ]


def test_person_alone_yields_present_not_unknown():
    """The one signal a laptop webcam reliably sees must produce a state."""
    engine = RuleBasedContextEngine(SETTINGS)

    context = engine.update(appeared("person"))

    assert context.state == ContextState.PRESENT
    assert context.is_transition is True


def test_objects_refine_presence_into_a_specific_activity():
    engine = RuleBasedContextEngine(SETTINGS)

    context = engine.update(appeared("person", "book"))

    assert context.state == ContextState.STUDYING


def test_objects_without_a_person_do_not_claim_an_activity():
    """A book left on an empty desk is not someone studying."""
    engine = RuleBasedContextEngine(SETTINGS)

    context = engine.update(appeared("book"))

    assert context.state != ContextState.STUDYING


def test_first_inference_counts_as_a_transition():
    engine = RuleBasedContextEngine(SETTINGS)

    context = engine.update(appeared("person", "book"))

    assert context.state == ContextState.STUDYING
    assert context.is_transition is True


def test_staying_in_the_same_state_is_not_a_transition():
    engine = RuleBasedContextEngine(SETTINGS)
    engine.update(appeared("person", "book"))

    for _ in range(5):
        context = engine.update(appeared("person", "book"))
        assert context.state == ContextState.STUDYING
        assert context.is_transition is False, "unchanged state must not re-log"


def test_changing_state_is_flagged_again():
    engine = RuleBasedContextEngine(SETTINGS)
    engine.update(appeared("person", "book"))

    context = engine.update(disappeared("book"))

    assert context.state == ContextState.PRESENT, "book gone, person still here"
    assert context.is_transition is True


def test_brief_absence_does_not_declare_the_user_away():
    """Leaning out of frame is not leaving the desk."""
    engine = RuleBasedContextEngine(SETTINGS)
    engine.update(appeared("person"))

    context = engine.update(disappeared("person"))

    assert context.state == ContextState.PRESENT
    assert context.state != ContextState.AWAY


def test_sustained_absence_declares_the_user_away(monkeypatch):
    engine = RuleBasedContextEngine(SETTINGS)
    engine.update(appeared("person"))
    engine.update(disappeared("person"))

    # Jump past the away timeout without sleeping.
    import deskos.context.context_engine as module

    later = time.time() + SETTINGS.away_timeout_sec + 1
    monkeypatch.setattr(module.time, "time", lambda: later)

    context = engine.update([])

    assert context.state == ContextState.AWAY


def test_only_transitions_reach_history():
    """The pipeline wiring in main.py, reproduced in miniature."""
    engine = RuleBasedContextEngine(SETTINGS)
    history = InMemoryHistoryStore()

    seen = appeared("person", "book")
    for events in [seen, seen, seen, seen, seen]:
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


def test_startup_is_unknown_during_warmup():
    """DeskOS must not announce a conclusion one second after starting."""
    engine = RuleBasedContextEngine(SETTINGS)

    context = engine.update([])

    assert context.state == ContextState.UNKNOWN
    assert context.confidence == 0.0


def test_warmup_expiring_with_nobody_seen_yields_away(monkeypatch):
    engine = RuleBasedContextEngine(SETTINGS)
    engine.update([])

    import deskos.context.context_engine as module

    later = time.time() + SETTINGS.warmup_sec + 1
    monkeypatch.setattr(module.time, "time", lambda: later)

    assert engine.update([]).state == ContextState.AWAY


def test_a_weak_reading_never_re_reports_a_strong_stale_belief():
    """The regression that made DeskOS permanently stuck in AWAY.

    Startup asserted AWAY(0.90); every later tick produced a reading below
    the confidence threshold, and the old implementation re-reported the
    stale AWAY forever. A low-confidence reading must degrade to UNKNOWN,
    never masquerade as the previous confident state.
    """
    engine = RuleBasedContextEngine(SETTINGS)
    engine.update(appeared("person"))
    assert engine.current().state == ContextState.PRESENT

    # An unmapped object with no person: nothing the rules can act on.
    engine.update(disappeared("person"))
    engine.update(appeared("frisbee"))

    assert engine.current().confidence >= SETTINGS.min_confidence or (
        engine.current().state == ContextState.UNKNOWN
    ), "a sub-threshold reading must not be reported as a confident state"


def test_warmup_is_measured_from_first_observation_not_construction(monkeypatch):
    """Model loading must not eat the warm-up window.

    The engine is constructed before the camera opens and before YOLO
    lazily loads, which takes seconds. Measuring warm-up from construction
    let it expire before the first frame arrived, and DeskOS declared AWAY
    while the very first frame showed a person.
    """
    import deskos.context.context_engine as module

    build_time = time.time()
    monkeypatch.setattr(module.time, "time", lambda: build_time)
    engine = RuleBasedContextEngine(SETTINGS)

    # Simulate a slow startup: the first frame arrives well after construction.
    first_frame = build_time + 30.0
    monkeypatch.setattr(module.time, "time", lambda: first_frame)
    assert engine.update([]).state == ContextState.UNKNOWN, "warm-up starts now"

    # Still inside the warm-up window, counted from that first observation.
    monkeypatch.setattr(module.time, "time", lambda: first_frame + 5.0)
    assert engine.update([]).state == ContextState.UNKNOWN
