"""Event Engine behaviour: confirmation timing, flicker tolerance, debounce.

These pin the two bugs fixed in Milestone 1: confirmation used to be counted
in frames (so its real duration depended on the loop tick rate), and a single
missing frame used to destroy a nearly-confirmed streak.

Time is injected by monkeypatching the module clock rather than sleeping, so
the suite stays fast and deterministic.
"""
from __future__ import annotations

import pytest

from deskos.config.settings import EventEngineSettings
from deskos.core import Detection, DetectionType, EventType
from deskos.events import event_engine as event_engine_module
from deskos.events.event_engine import EventEngine

SETTINGS = EventEngineSettings(
    confirm_after_sec=6.0,
    event_debounce_sec=5.0,
    absence_grace_sec=3.0,
)


@pytest.fixture
def clock(monkeypatch):
    """A controllable stand-in for time.time() inside the event engine."""

    class Clock:
        def __init__(self) -> None:
            self.now = 1_000.0

        def advance(self, seconds: float) -> None:
            self.now += seconds

    c = Clock()
    monkeypatch.setattr(event_engine_module.time, "time", lambda: c.now)
    return c


def detection(label: str = "laptop", confidence: float = 0.9) -> list[Detection]:
    return [Detection(type=DetectionType.OBJECT, label=label, confidence=confidence)]


def test_label_is_not_confirmed_before_the_configured_delay(clock):
    engine = EventEngine(SETTINGS)

    events = engine.process(detection())
    clock.advance(5.0)
    events += engine.process(detection())

    assert events == []


def test_label_is_confirmed_once_it_has_persisted_long_enough(clock):
    engine = EventEngine(SETTINGS)

    engine.process(detection())
    clock.advance(SETTINGS.confirm_after_sec)
    events = engine.process(detection())

    assert len(events) == 1
    assert events[0].type == EventType.OBJECT_APPEARED
    assert events[0].label == "laptop"


def test_confirmation_depends_on_elapsed_time_not_frame_count(clock):
    """Two frames far apart confirm; many frames in quick succession do not.

    This is the regression guard for the old frame-counting behaviour, where
    the same config meant six seconds or thirty depending on the tick rate.
    """
    sparse = EventEngine(SETTINGS)
    sparse.process(detection())
    clock.advance(SETTINGS.confirm_after_sec)
    assert len(sparse.process(detection())) == 1

    clock.advance(100.0)

    busy = EventEngine(SETTINGS)
    for _ in range(50):
        clock.advance(0.01)
        assert busy.process(detection()) == []


def test_brief_flicker_does_not_reset_progress(clock):
    """A detector dropping one frame must not undo a nearly-confirmed streak.

    Simulates the real loop: one detection per second, with a single missed
    frame partway through, as happens when a hand crosses the keyboard.
    """
    engine = EventEngine(SETTINGS)
    events = []

    for tick in range(7):
        frame = [] if tick == 5 else detection()   # one dropped frame
        events += engine.process(frame)
        clock.advance(1.0)

    assert len(events) == 1, "streak should have survived the dropped frame"
    assert events[0].type == EventType.OBJECT_APPEARED


def test_absence_beyond_the_grace_period_drops_the_streak(clock):
    engine = EventEngine(SETTINGS)

    engine.process(detection())
    clock.advance(SETTINGS.absence_grace_sec + 1.0)
    engine.process([])          # gone long enough to count as gone

    clock.advance(SETTINGS.confirm_after_sec)
    assert engine.process(detection()) == [], "progress should have restarted"


def test_confirmed_label_disappearing_emits_a_disappearance_event(clock):
    engine = EventEngine(SETTINGS)

    engine.process(detection())
    clock.advance(SETTINGS.confirm_after_sec)
    engine.process(detection())

    clock.advance(SETTINGS.absence_grace_sec + 1.0)
    events = engine.process([])

    assert len(events) == 1
    assert events[0].type == EventType.OBJECT_DISAPPEARED
    assert events[0].label == "laptop"


def test_confirmed_label_is_debounced_between_repeat_emissions(clock):
    engine = EventEngine(SETTINGS)

    engine.process(detection())
    clock.advance(SETTINGS.confirm_after_sec)
    engine.process(detection())                     # confirmation

    clock.advance(1.0)
    assert engine.process(detection()) == [], "too soon to re-emit"

    clock.advance(SETTINGS.event_debounce_sec)
    assert len(engine.process(detection())) == 1, "heartbeat should resume"


def test_reported_confidence_is_averaged_across_sightings(clock):
    engine = EventEngine(SETTINGS)

    engine.process(detection(confidence=0.6))
    clock.advance(SETTINGS.confirm_after_sec)
    events = engine.process(detection(confidence=1.0))

    assert events[0].confidence == pytest.approx(0.8)
