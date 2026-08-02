"""OpenCV-backed webcam implementation of CameraSource."""
from __future__ import annotations

import logging
import sys

from deskos.camera.interfaces import CameraSource
from deskos.config.settings import CameraSettings
from deskos.core import Frame

logger = logging.getLogger(__name__)


class WebcamSource(CameraSource):
    """Reads frames from a local webcam via OpenCV.

    Kept intentionally dumb: no retries/backoff policy here yet.
    TODO: add reconnect-on-failure once running unattended for days.
    """

    def __init__(self, settings: CameraSettings) -> None:
        self._settings = settings
        self._capture = None  # type: ignore[assignment]  # cv2.VideoCapture, lazily imported

    def start(self) -> None:
        if self._capture is not None:
            return
        import cv2  # local import: keep cv2 out of modules that don't need it

        # Windows' default MSMF backend frequently fails to grab frames on
        # some webcam drivers ("can't grab frame" / MSMF errors); DirectShow
        # is far more reliable there. Other platforms use OpenCV's default.
        backend = cv2.CAP_DSHOW if sys.platform.startswith("win") else cv2.CAP_ANY
        capture = cv2.VideoCapture(self._settings.device_index, backend)
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, self._settings.frame_width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self._settings.frame_height)
        capture.set(cv2.CAP_PROP_FPS, self._settings.fps)
        if not capture.isOpened():
            raise RuntimeError(
                f"Could not open camera at index {self._settings.device_index}"
            )
        # Warm-up read: some drivers need a frame or two before real ones flow.
        capture.read()
        self._capture = capture
        logger.info("Camera started (device=%d)", self._settings.device_index)

    def read_frame(self) -> Frame | None:
        if self._capture is None:
            raise RuntimeError("Camera not started; call start() first")
        ok, image = self._capture.read()
        if not ok:
            logger.warning("Failed to read frame from camera")
            return None
        return Frame(image=image)

    def stop(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None
            logger.info("Camera stopped")
