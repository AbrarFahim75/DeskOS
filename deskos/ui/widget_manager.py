"""Enforces "one widget at a time" and fade timing; delegates actual
rendering to a WidgetRenderer implementation.
"""
from __future__ import annotations

from collections.abc import Callable

from deskos.config.settings import UISettings
from deskos.core import FeedbackType, WidgetMood
from deskos.ui.interfaces import WidgetRenderer


class WidgetManager:
    def __init__(self, renderer: WidgetRenderer, settings: UISettings) -> None:
        self._renderer = renderer
        self._settings = settings

    def show(
        self,
        message: str,
        mood: WidgetMood = WidgetMood.NEUTRAL,
        on_feedback: Callable[[FeedbackType], None] | None = None,
        duration_sec: float = 5.0,
    ) -> None:
        # Product principle 4: small floating widgets only, never stacked.
        self._renderer.dismiss()
        self._renderer.show(message, duration_sec, mood, on_feedback)
