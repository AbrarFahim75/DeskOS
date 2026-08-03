"""Camera layer contract.

A CameraSource's only job is producing Frames. It must not resize for
detection purposes, run any model, or know that Perception exists.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from deskos.core import Frame


class CameraSource(ABC):
    """Abstract source of raw frames. Implementations: webcam, video file,
    screen capture, virtual/mock source for tests.
    """

    @abstractmethod
    def start(self) -> None:
        """Open the underlying device/stream. Idempotent."""
        raise NotImplementedError

    @abstractmethod
    def read_frame(self) -> Frame | None:
        """Return the latest Frame, or None if unavailable this tick."""
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        """Release the underlying device/stream. Idempotent."""
        raise NotImplementedError

    def __enter__(self) -> CameraSource:
        self.start()
        return self

    def __exit__(self, *_exc_info) -> None:
        self.stop()
