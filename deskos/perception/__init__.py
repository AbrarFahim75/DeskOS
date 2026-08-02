"""Perception package: turns raw Frames into Detections. No business logic."""
from deskos.perception.interfaces import Detector
from deskos.perception.pipeline import PerceptionPipeline
from deskos.perception.object_detector import ObjectDetector

__all__ = ["Detector", "PerceptionPipeline", "ObjectDetector"]
