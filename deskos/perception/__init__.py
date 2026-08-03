"""Perception package: turns raw Frames into Detections. No business logic."""
from deskos.perception.interfaces import Detector
from deskos.perception.object_detector import ObjectDetector
from deskos.perception.pipeline import PerceptionPipeline

__all__ = ["Detector", "PerceptionPipeline", "ObjectDetector"]
