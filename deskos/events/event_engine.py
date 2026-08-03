"""Rule-based Event Engine: streak-confirmation + debounce.

Design note: this is intentionally the "dumbest thing that works" - a
per-label streak counter. It has no ML and no memory of history beyond the
current streak. That keeps it easy to reason about and easy to replace
later with a smarter temporal model without touching any other layer.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

from deskos.config.settings import EventEngineSettings
from deskos.core import Detection, Event, EventType
from deskos.events.interfaces import EventSource


@dataclass
class _LabelStreak:
    consecutive_frames: int = 0
    confirmed: bool = False
    last_emitted_at: float = 0.0
    confidence_sum: float = 0.0


class EventEngine(EventSource):
    """Confirms a label as a real Event only after it survives
    `min_frames_to_confirm` consecutive frames, then debounces repeat
    emissions within `event_debounce_sec`.
    """

    def __init__(self, settings: EventEngineSettings) -> None:
        self._settings = settings
        self._streaks: dict[str, _LabelStreak] = {}

    def process(self, detections: list[Detection]) -> list[Event]:
        seen_labels = {d.label for d in detections}
        events: list[Event] = []
        now = time.time()

        for detection in detections:
            streak = self._streaks.setdefault(detection.label, _LabelStreak())
            streak.consecutive_frames += 1
            streak.confidence_sum += detection.confidence

            just_confirmed = (
                not streak.confirmed
                and streak.consecutive_frames >= self._settings.min_frames_to_confirm
            )
            debounce_elapsed = (now - streak.last_emitted_at) >= self._settings.event_debounce_sec

            if just_confirmed or (streak.confirmed and debounce_elapsed):
                avg_confidence = streak.confidence_sum / streak.consecutive_frames
                events.append(
                    Event(
                        type=EventType.OBJECT_APPEARED,
                        label=detection.label,
                        confidence=avg_confidence,
                    )
                )
                streak.confirmed = True
                streak.last_emitted_at = now

        # Any previously-tracked label absent this frame: reset its streak,
        # and emit a disappearance event if it had been confirmed.
        for label in list(self._streaks.keys()):
            if label in seen_labels:
                continue
            streak = self._streaks[label]
            if streak.confirmed:
                events.append(Event(type=EventType.OBJECT_DISAPPEARED, label=label, confidence=1.0))
            del self._streaks[label]

        return events
