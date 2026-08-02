"""Fan-out pipeline running all configured detectors on each frame."""
from __future__ import annotations

from deskos.core import Detection, Frame
from deskos.perception.interfaces import Detector


class PerceptionPipeline:
    """Runs each registered Detector on a Frame and flattens the results.

    Detectors are independent and order-agnostic; add/remove without
    touching this class (open/closed principle).
    """

    def __init__(self, detectors: list[Detector]) -> None:
        self._detectors = detectors

    def process(self, frame: Frame) -> list[Detection]:
        detections: list[Detection] = []
        for detector in self._detectors:
            detections.extend(detector.detect(frame))
        return detections
