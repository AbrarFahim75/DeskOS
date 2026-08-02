"""Event Engine layer contract."""
from __future__ import annotations

from abc import ABC, abstractmethod

from deskos.core import Detection, Event


class EventSource(ABC):
    """Turns a batch of per-frame Detections into zero or more debounced
    Events. Implementations own their own internal streak/state tracking.
    """

    @abstractmethod
    def process(self, detections: list[Detection]) -> list[Event]:
        """Feed one frame's worth of Detections; returns newly confirmed
        Events (usually empty — most frames confirm nothing new).
        """
        raise NotImplementedError
