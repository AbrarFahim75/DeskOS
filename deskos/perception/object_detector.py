"""Object detector backed by a real YOLO model (ultralytics).

Maps COCO class names to the labels the Context Engine's MVP rules
understand. Two pragmatic MVP approximations, called out explicitly since
COCO has no "notebook" or "empty_chair" classes:
- STUDYING is inferred from "book" alone (Context Engine no longer
  requires a paired "notebook" detection).
- "empty chair" is inferred by Context (chair present + no person), not
  here — Perception only reports what it literally sees.
"""
from __future__ import annotations

import logging

from deskos.core import Detection, DetectionType, Frame
from deskos.perception.interfaces import Detector

logger = logging.getLogger(__name__)

# COCO class name -> DeskOS label. Anything not listed is ignored.
_COCO_LABEL_MAP: dict[str, str] = {
    "laptop": "laptop",
    "keyboard": "keyboard",
    "book": "book",
    "cup": "coffee_cup",
    "cell phone": "phone",
    "person": "person",
    "chair": "chair",
}


class ObjectDetector(Detector):
    """Wraps a YOLO model (ultralytics). Loads lazily on first `detect()`
    call so constructing a pipeline never requires a model file to exist
    (e.g. in unit tests using zero detectors).
    """

    def __init__(self, model_path: str = "yolov8n.pt", confidence_threshold: float = 0.5) -> None:
        self._model_path = model_path
        self._confidence_threshold = confidence_threshold
        self._model = None

    def _ensure_model_loaded(self) -> bool:
        if self._model is not None:
            return True
        try:
            from ultralytics import YOLO  # local import: keep heavy dep optional
        except ImportError:
            logger.warning("ultralytics not installed; ObjectDetector will detect nothing")
            return False
        try:
            self._model = YOLO(self._model_path)
        except Exception:
            logger.exception("Failed to load YOLO model at %s", self._model_path)
            return False
        return True

    def detect(self, frame: Frame) -> list[Detection]:
        if not self._ensure_model_loaded():
            return []

        results = self._model.predict(frame.image, verbose=False)[0]
        detections: list[Detection] = []
        for box in results.boxes:
            confidence = float(box.conf[0])
            if confidence < self._confidence_threshold:
                continue
            class_name = results.names[int(box.cls[0])]
            label = _COCO_LABEL_MAP.get(class_name)
            if label is None:
                continue
            detections.append(
                Detection(type=DetectionType.OBJECT, label=label, confidence=confidence)
            )
        return detections
