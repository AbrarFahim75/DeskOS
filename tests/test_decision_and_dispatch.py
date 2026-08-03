"""Decision gating, and where a suggestion's cooldown actually starts.

Milestone 1 moved the "suggestion was shown" write out of the Decision
Engine and into the Service Registry, so a service that fails or skips no
longer silences that suggestion for the next ten minutes.
"""
from __future__ import annotations

from deskos.config.settings import DecisionEngineSettings
from deskos.core import (
    Action,
    ActionType,
    ContextSnapshot,
    ContextState,
    ExecutionResult,
    ExecutionStatus,
    Suggestion,
    SuggestionType,
)
from deskos.decision.decision_engine import DecisionEngine
from deskos.knowledge.history_store import InMemoryHistoryStore
from deskos.services.interfaces import Service
from deskos.services.service_registry import ServiceRegistry

SETTINGS = DecisionEngineSettings(
    suggestion_cooldown_sec=600.0,
    min_confidence_to_act=0.75,
)


def suggestion(confidence: float = 0.9) -> Suggestion:
    return Suggestion(
        type=SuggestionType.TAKE_BREAK,
        context=ContextSnapshot(state=ContextState.BREAK, confidence=confidence),
        confidence=confidence,
    )


class StubService(Service):
    """A service whose outcome the test chooses."""

    def __init__(self, status: ExecutionStatus) -> None:
        self._status = status
        self.calls = 0

    @property
    def name(self) -> str:
        return "stub"

    @property
    def handles(self) -> set[ActionType]:
        return {ActionType.SHOW_WIDGET}

    def execute(self, action: Action) -> ExecutionResult:
        self.calls += 1
        if self._status == ExecutionStatus.FAILED:
            raise RuntimeError("stub failure")
        return ExecutionResult(
            action=action, service_name=self.name, status=self._status, duration_sec=0.0
        )


def test_low_confidence_suggestion_is_suppressed():
    engine = DecisionEngine(SETTINGS, InMemoryHistoryStore())

    assert engine.decide([suggestion(confidence=0.5)]) == []


def test_confident_suggestion_becomes_an_action():
    engine = DecisionEngine(SETTINGS, InMemoryHistoryStore())

    actions = engine.decide([suggestion()])

    assert len(actions) == 1
    assert actions[0].type == ActionType.SHOW_WIDGET
    assert actions[0].payload["suggestion_type"] == SuggestionType.TAKE_BREAK.name


def test_deciding_does_not_write_to_history():
    """Decision is pure policy. Only delivery starts a cooldown."""
    history = InMemoryHistoryStore()
    engine = DecisionEngine(SETTINGS, history)

    engine.decide([suggestion()])

    assert history.seconds_since_last_suggestion(SuggestionType.TAKE_BREAK) is None


def test_successful_delivery_starts_the_cooldown():
    history = InMemoryHistoryStore()
    engine = DecisionEngine(SETTINGS, history)
    registry = ServiceRegistry([StubService(ExecutionStatus.SUCCESS)], history)

    registry.dispatch(engine.decide([suggestion()]))

    assert history.seconds_since_last_suggestion(SuggestionType.TAKE_BREAK) is not None


def test_skipped_delivery_does_not_burn_the_cooldown():
    history = InMemoryHistoryStore()
    engine = DecisionEngine(SETTINGS, history)
    registry = ServiceRegistry([StubService(ExecutionStatus.SKIPPED)], history)

    registry.dispatch(engine.decide([suggestion()]))

    assert history.seconds_since_last_suggestion(SuggestionType.TAKE_BREAK) is None
    assert engine.decide([suggestion()]) != [], "user never saw it, so retry is allowed"


def test_failed_delivery_does_not_burn_the_cooldown():
    history = InMemoryHistoryStore()
    engine = DecisionEngine(SETTINGS, history)
    registry = ServiceRegistry([StubService(ExecutionStatus.FAILED)], history)

    registry.dispatch(engine.decide([suggestion()]))

    assert history.seconds_since_last_suggestion(SuggestionType.TAKE_BREAK) is None


def test_delivered_suggestion_is_not_repeated_within_the_cooldown():
    history = InMemoryHistoryStore()
    engine = DecisionEngine(SETTINGS, history)
    registry = ServiceRegistry([StubService(ExecutionStatus.SUCCESS)], history)

    registry.dispatch(engine.decide([suggestion()]))

    assert engine.decide([suggestion()]) == [], "must not repeat itself"


def test_a_failing_service_never_crashes_the_loop():
    history = InMemoryHistoryStore()
    service = StubService(ExecutionStatus.FAILED)
    registry = ServiceRegistry([service], history)

    registry.dispatch([Action(type=ActionType.SHOW_WIDGET, payload={})])

    assert service.calls == 1
