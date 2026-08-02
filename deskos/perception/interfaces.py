"""Perception layer contract."""
from __future__ import annotations

from abc import ABC, abstractmethod

from deskos.core import Detection, Frame


class Detector(ABC):
    """A single perception model (object detector, pose estimator, OCR, ...).

    Each Detector answers only "what do I see", never "what does it mean" —
    that judgment belongs to the Event/Context Engines.
    """

    @abstractmethod
    def detect(self, frame: Frame) -> list[Detection]:
        """Run this detector on one frame, returning zero or more Detections."""
        raise NotImplementedError
