"""Camera package: raw frame acquisition only."""
from deskos.camera.interfaces import CameraSource
from deskos.camera.webcam_source import WebcamSource

__all__ = ["CameraSource", "WebcamSource"]
