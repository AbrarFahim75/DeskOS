"""Deterministic CameraSource for tests and offline development.

Cycles through a fixed list of Frames (or generates blank ones) instead of
touching real hardware — lets Perception/Context/Decision be developed and
tested without a webcam attached.
"""
from __future__ import annotations

from deskos.camera.interfaces import CameraSource
from deskos.core import Frame


class MockCameraSource(CameraSource):
    """Yields pre-supplied frames in order, looping. If none supplied,
    yields None forever (simulating "no signal").
    """

    def __init__(self, frames: list[Frame] | None = None) -> None:
        self._frames = frames or []
        self._index = 0
        self._started = False

    def start(self) -> None:
        self._started = True

    def read_frame(self) -> Frame | None:
        if not self._started or not self._frames:
            return None
        frame = self._frames[self._index % len(self._frames)]
        self._index += 1
        return frame

    def stop(self) -> None:
        self._started = False
