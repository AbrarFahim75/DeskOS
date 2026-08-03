"""Rule-based Event Engine: time-based confirmation, absence grace, debounce.

Design note: confirmation is measured in *wall-clock seconds*, not in frames.
Frame counting made the engine's behaviour depend on how fast the main loop
happened to tick, so the same config meant 6 seconds or 30 depending on an
unrelated setting. Seconds are what a human actually cares about ("has the
laptop been there long enough to be real?"), and the rule stays correct if
the tick rate ever changes.

A label is also allowed to vanish briefly without losing its progress.
Object detectors flicker constantly on real webcam input - a hand passes
over the keyboard, the lighting shifts - and treating one missed frame as
"the object is gone" meant a streak could almost never survive long enough
to be confirmed.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from deskos.config.settings import EventEngineSettings
from deskos.core import Detection, Event, EventType
from deskos.events.interfaces import EventSource


@dataclass
class _LabelStreak:
    """Progress toward confirming one label as a real Event."""

    first_seen_at: float
    last_seen_at: float
    confirmed: bool = False
    last_emitted_at: float = 0.0
    confidences: list[float] = field(default_factory=list)

    @property
    def average_confidence(self) -> float:
        if not self.confidences:
            return 0.0
        return sum(self.confidences) / len(self.confidences)


class EventEngine(EventSource):
    """Turns a noisy per-frame Detection stream into confirmed Events.

    A label becomes an Event once it has been seen continuously for
    `confirm_after_sec`, tolerating gaps shorter than `absence_grace_sec`.
    Once confirmed it re-emits at most once per `event_debounce_sec`, which
    acts as a heartbeat keeping the Context Engine's view of the label fresh.
    """

    def __init__(self, settings: EventEngineSettings) -> None:
        self._settings = settings
        self._streaks: dict[str, _LabelStreak] = {}

    def process(self, detections: list[Detection]) -> list[Event]:
        now = time.time()
        events: list[Event] = []
        seen_labels = {d.label for d in detections}

        for detection in detections:
            events.extend(self._observe(detection, now))

        events.extend(self._expire_absent(seen_labels, now))
        return events

    def _observe(self, detection: Detection, now: float) -> list[Event]:
        """Record one sighting, emitting an Event if it confirms or is due."""
        streak = self._streaks.get(detection.label)
        if streak is None:
            streak = _LabelStreak(first_seen_at=now, last_seen_at=now)
            self._streaks[detection.label] = streak

        streak.last_seen_at = now
        streak.confidences.append(detection.confidence)

        held_for = now - streak.first_seen_at
        just_confirmed = not streak.confirmed and held_for >= self._settings.confirm_after_sec
        due_again = (
            streak.confirmed
            and (now - streak.last_emitted_at) >= self._settings.event_debounce_sec
        )

        if not (just_confirmed or due_again):
            return []

        streak.confirmed = True
        streak.last_emitted_at = now
        return [
            Event(
                type=EventType.OBJECT_APPEARED,
                label=detection.label,
                confidence=streak.average_confidence,
                timestamp=now,
            )
        ]

    def _expire_absent(self, seen_labels: set[str], now: float) -> list[Event]:
        """Drop labels absent longer than the grace period.

        Anything absent for less than `absence_grace_sec` keeps its progress,
        so a brief detector flicker does not reset a nearly-confirmed streak.
        """
        events: list[Event] = []
        for label in list(self._streaks):
            if label in seen_labels:
                continue
            streak = self._streaks[label]
            if (now - streak.last_seen_at) < self._settings.absence_grace_sec:
                continue
            if streak.confirmed:
                events.append(
                    Event(
                        type=EventType.OBJECT_DISAPPEARED,
                        label=label,
                        confidence=1.0,
                        timestamp=now,
                    )
                )
            del self._streaks[label]
        return events
