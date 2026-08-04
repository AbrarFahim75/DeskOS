"""Smoke test: pipeline runs end-to-end with mock camera and no detections.

TODO: add per-layer unit tests (EventEngine debounce, ContextEngine rules,
DecisionEngine cooldown/confidence gating) as those modules stabilize.
"""
from deskos.config.settings import load_settings
from deskos.context.context_engine import RuleBasedContextEngine
from deskos.core import ContextState
from deskos.decision.decision_engine import DecisionEngine
from deskos.events.event_engine import EventEngine
from deskos.knowledge.history_store import InMemoryHistoryStore
from deskos.perception.pipeline import PerceptionPipeline


def test_empty_pipeline_yields_unknown_not_away() -> None:
    """Seeing nothing at startup means "not looked yet", not "user left".

    This previously asserted AWAY, which was the bug: an empty first frame
    declared the user absent at 0.90 confidence and that belief then stuck
    permanently.
    """
    settings = load_settings()
    perception = PerceptionPipeline(detectors=[])
    event_engine = EventEngine(settings.event_engine)
    context_engine = RuleBasedContextEngine(settings.context_engine)

    detections = perception.process(frame=None)  # no detectors registered
    events = event_engine.process(detections)
    context = context_engine.update(events)

    assert context.state == ContextState.UNKNOWN


def test_decision_engine_suppresses_low_confidence() -> None:
    from deskos.core import ContextSnapshot, Suggestion, SuggestionType

    settings = load_settings()
    decision_engine = DecisionEngine(settings.decision_engine, InMemoryHistoryStore())
    low_confidence_suggestion = Suggestion(
        type=SuggestionType.TAKE_BREAK,
        context=ContextSnapshot(state=ContextState.BREAK, confidence=0.5),
        confidence=0.5,
    )

    actions = decision_engine.decide([low_confidence_suggestion])

    assert actions == []
