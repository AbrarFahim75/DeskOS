"""Pipeline observability: suppression reasons and terminal rendering.

The product's most important behaviour is staying silent. These tests pin
that every silence is attributable to a specific rule, and that attaching
an observer never changes what the pipeline decides.
"""
from __future__ import annotations

import io
import time

from deskos.config.settings import DecisionEngineSettings
from deskos.core import (
    ContextSnapshot,
    ContextState,
    Detection,
    DetectionType,
    Suggestion,
    SuggestionType,
    UserValue,
)
from deskos.decision.decision_engine import DecisionEngine
from deskos.knowledge.history_store import InMemoryHistoryStore
from deskos.observability import PipelineTrace, SuggestionOutcome
from deskos.observability.terminal_observer import TerminalObserver

SETTINGS = DecisionEngineSettings(
    suggestion_cooldown_sec=600.0,
    min_confidence_to_act=0.75,
)


def suggestion(
    stype: SuggestionType = SuggestionType.TAKE_BREAK,
    confidence: float = 0.9,
    value: UserValue = UserValue.MEDIUM,
) -> Suggestion:
    return Suggestion(
        type=stype,
        context=ContextSnapshot(state=ContextState.BREAK, confidence=confidence),
        confidence=confidence,
        estimated_value=value,
    )


# --- suppression reasons -------------------------------------------------


def test_low_confidence_is_reported_as_such():
    engine = DecisionEngine(SETTINGS, InMemoryHistoryStore())

    (action, outcome), = engine.evaluate([suggestion(confidence=0.5)])

    assert action is None
    assert outcome.approved is False
    assert outcome.reason == "LOW_CONFIDENCE"


def test_cooldown_is_reported_as_such():
    history = InMemoryHistoryStore()
    history.record_suggestion_shown(SuggestionType.TAKE_BREAK, time.time())
    engine = DecisionEngine(SETTINGS, history)

    (action, outcome), = engine.evaluate([suggestion()])

    assert action is None
    assert outcome.reason == "IN_COOLDOWN"


def test_low_user_value_is_reported_as_such():
    engine = DecisionEngine(SETTINGS, InMemoryHistoryStore())

    (action, outcome), = engine.evaluate(
        [suggestion(stype=SuggestionType.RESUME_FOCUS, value=UserValue.LOW)]
    )

    assert action is None
    assert outcome.reason == "LOW_USER_VALUE"


def test_approved_suggestion_carries_its_approval_reason():
    engine = DecisionEngine(SETTINGS, InMemoryHistoryStore())

    (action, outcome), = engine.evaluate([suggestion()])

    assert action is not None
    assert outcome.approved is True
    assert "first occurrence" in outcome.reason


def test_evaluate_and_decide_never_disagree():
    """decide() is evaluate() with rejections dropped; keep them in step."""
    history = InMemoryHistoryStore()
    engine = DecisionEngine(SETTINGS, history)
    proposals = [suggestion(), suggestion(confidence=0.3)]

    from_evaluate = [a for a, _ in engine.evaluate(proposals) if a is not None]

    history2 = InMemoryHistoryStore()
    from_decide = DecisionEngine(SETTINGS, history2).decide(proposals)

    assert len(from_evaluate) == len(from_decide) == 1


# --- terminal rendering --------------------------------------------------


def render(trace: PipelineTrace, verbose: bool = True) -> str:
    stream = io.StringIO()
    TerminalObserver(stream=stream, verbose=verbose).on_tick(trace)
    return stream.getvalue()


def test_silence_line_names_the_suppressing_rule():
    line = render(
        PipelineTrace(
            context=ContextSnapshot(state=ContextState.BREAK, confidence=0.9),
            outcomes=(
                SuggestionOutcome(
                    suggestion_type=SuggestionType.TAKE_BREAK,
                    approved=False,
                    reason="IN_COOLDOWN",
                ),
            ),
        )
    )

    assert "SILENT" in line
    assert "TAKE_BREAK" in line
    assert "in_cooldown" in line


def test_shown_line_names_the_suggestion():
    line = render(
        PipelineTrace(
            context=ContextSnapshot(state=ContextState.BREAK, confidence=0.9),
            outcomes=(
                SuggestionOutcome(
                    suggestion_type=SuggestionType.TAKE_BREAK,
                    approved=True,
                    reason="first occurrence",
                ),
            ),
        )
    )

    assert "SHOW" in line
    assert "TAKE_BREAK" in line


def test_detections_are_listed():
    line = render(
        PipelineTrace(
            detections=(
                Detection(type=DetectionType.OBJECT, label="laptop", confidence=0.9),
                Detection(type=DetectionType.OBJECT, label="keyboard", confidence=0.8),
            ),
            context=ContextSnapshot(state=ContextState.CODING, confidence=0.85),
        )
    )

    assert "laptop" in line and "keyboard" in line
    assert "CODING(0.85)" in line


def test_nothing_proposed_is_distinguished_from_a_suppressed_suggestion():
    line = render(
        PipelineTrace(
            context=ContextSnapshot(state=ContextState.CODING, confidence=0.85),
            outcomes=(),
        )
    )

    assert "nothing proposed" in line


def test_idle_ticks_are_hidden_unless_verbose():
    idle = PipelineTrace(
        context=ContextSnapshot(state=ContextState.UNKNOWN, confidence=0.0)
    )

    assert render(idle, verbose=False) == "", "idle ticks should not spam the terminal"
    assert render(idle, verbose=True) != "", "--debug-verbose should show them"


def test_trace_reports_whether_deskos_stayed_silent():
    silent = PipelineTrace(
        outcomes=(
            SuggestionOutcome(
                suggestion_type=SuggestionType.TAKE_BREAK,
                approved=False,
                reason="IN_COOLDOWN",
            ),
        )
    )
    acted = PipelineTrace(
        outcomes=(
            SuggestionOutcome(
                suggestion_type=SuggestionType.TAKE_BREAK,
                approved=True,
                reason="first occurrence",
            ),
        )
    )

    assert silent.stayed_silent is True
    assert acted.stayed_silent is False
