"""Enforces "one widget at a time" and marshals rendering onto the UI thread.

WidgetManager sits between the Services layer and the actual renderer. It
implements WidgetPresenter (the small contract Services depend on) and
delegates drawing to a WidgetRenderer. If given a UIHost, every render call
is posted onto the UI thread, so a service running on the perception worker
can safely ask for a widget without touching Tk from the wrong thread.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from deskos.config.settings import UISettings
from deskos.core import FeedbackType, WidgetMood
from deskos.ui.interfaces import WidgetPresenter, WidgetRenderer


class WidgetManager(WidgetPresenter):
    def __init__(
        self,
        renderer: WidgetRenderer,
        settings: UISettings,
        ui_host: Any = None,
    ) -> None:
        self._renderer = renderer
        self._settings = settings
        self._ui_host = ui_host

    def show(
        self,
        message: str,
        mood: WidgetMood = WidgetMood.NEUTRAL,
        on_feedback: Callable[[FeedbackType], None] | None = None,
        duration_sec: float = 5.0,
    ) -> None:
        def render() -> None:
            # Product principle: small floating widgets only, never stacked.
            self._renderer.dismiss()
            self._renderer.show(message, duration_sec, mood, on_feedback)

        if self._ui_host is not None:
            self._ui_host.post(render)
        else:
            render()
