"""Tkinter suggestion toast: a small widget that fades in, holds, fades out.

This is a *renderer*, not an application. It draws into a Tk root owned by
`UIHost` and assumes every method is called on the UI thread (UIHost.post
guarantees that for callers on other threads). It no longer creates its own
root or background thread - that was the source of the two-Tk-roots bug.

Beyond that it is deliberately minimal: fades, remembers the user-moved
position across launches, applies a subtle mood accent, and reveals
feedback controls on hover so the resting state stays ambient.
TODO: replace with an OS-native overlay (e.g. pywebview) for polish.
"""
from __future__ import annotations

import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from deskos.core import FeedbackType, WidgetMood
from deskos.ui.interfaces import WidgetRenderer

logger = logging.getLogger(__name__)

_MOOD_ACCENT: dict[WidgetMood, str] = {
    WidgetMood.NEUTRAL: "#3a3a3c",
    WidgetMood.POSITIVE: "#2f6f4f",
    WidgetMood.IMPORTANT: "#7a4a1f",
}

_FADE_STEP_MS = 15
_FADE_STEPS = 12  # ~180ms fade in/out - smooth, never flashy


class FloatingWidget(WidgetRenderer):
    """Renders one transient suggestion toast at a time into a shared root.

    Pass the Tk root via `attach()` before the first `show()`. All calls
    must be on the UI thread; background callers go through `UIHost.post`.
    """

    def __init__(self, position_file: Path | None = None) -> None:
        self._position_file = position_file
        self._tk: Any = None
        self._root: Any = None
        self._toplevel: Any = None
        self._dismiss_job: Any = None

    def attach(self, root: Any) -> None:
        """Give the widget the shared Tk root to draw into. Call once, on the UI thread."""
        import tkinter as tk

        self._tk = tk
        self._root = root

    def show(
        self,
        message: str,
        duration_sec: float,
        mood: WidgetMood = WidgetMood.NEUTRAL,
        on_feedback: Callable[[FeedbackType], None] | None = None,
    ) -> None:
        if self._root is None:
            logger.debug("FloatingWidget.show() before attach(); ignoring")
            return
        self._open(message, duration_sec, mood, on_feedback)

    def dismiss(self) -> None:
        self._close()

    def _open(self, message, duration_sec, mood, on_feedback) -> None:
        self._close(animate=False)
        tk = self._tk

        top = tk.Toplevel(self._root)
        top.overrideredirect(True)
        top.attributes("-topmost", True)
        top.attributes("-alpha", 0.0)
        x, y = self._load_position()
        top.geometry(f"+{x}+{y}")
        accent = _MOOD_ACCENT.get(mood, _MOOD_ACCENT[WidgetMood.NEUTRAL])

        container = tk.Frame(top, bg=accent)
        container.pack()
        label = tk.Label(
            container, text=message, font=("Helvetica", 14),
            padx=16, pady=10, fg="white", bg=accent,
        )
        label.pack()

        controls = tk.Frame(container, bg=accent)
        for glyph, feedback_type in (
            ("\U0001F44D", FeedbackType.HELPFUL),
            ("\U0001F44E", FeedbackType.NOT_HELPFUL),
            ("\u2716", FeedbackType.DISMISSED),
            ("\u23F0", FeedbackType.REMIND_LATER),
        ):
            tk.Button(
                controls, text=glyph, bg=accent, fg="white", bd=0, font=("Helvetica", 11),
                command=lambda ft=feedback_type: self._feedback_clicked(ft, on_feedback),
            ).pack(side="left", padx=4)

        container.bind("<Enter>", lambda _e: controls.pack(pady=(0, 6)))
        container.bind("<Leave>", lambda _e: controls.pack_forget())
        label.bind("<ButtonPress-1>", lambda e: top.geometry(f"+{e.x_root}+{e.y_root}"))
        top.bind("<ButtonRelease-1>", lambda e: self._save_position(top.winfo_x(), top.winfo_y()))

        self._toplevel = top
        self._fade(top, 0.0, 1.0, on_done=lambda: self._schedule_auto_dismiss(top, duration_sec))

    def _feedback_clicked(self, feedback_type: FeedbackType, on_feedback: Callable | None) -> None:
        if on_feedback is not None:
            on_feedback(feedback_type)
        self._close()  # any feedback dismisses immediately, never waits out the timer

    def _schedule_auto_dismiss(self, top, duration_sec: float) -> None:
        if self._toplevel is top:
            self._dismiss_job = top.after(int(duration_sec * 1000), self._close)

    def _fade(self, widget, start: float, end: float, on_done: Callable | None = None, step: int = 0) -> None:
        progress = step / _FADE_STEPS
        alpha = start + (end - start) * min(progress, 1.0)
        try:
            widget.attributes("-alpha", alpha)
        except Exception:
            return  # window already destroyed mid-fade
        if step >= _FADE_STEPS:
            if on_done:
                on_done()
            return
        widget.after(_FADE_STEP_MS, lambda: self._fade(widget, start, end, on_done, step + 1))

    def _close(self, animate: bool = True) -> None:
        top = self._toplevel
        if top is None:
            return
        if self._dismiss_job is not None:
            try:
                top.after_cancel(self._dismiss_job)
            except Exception:
                pass
            self._dismiss_job = None

        self._toplevel = None  # prevent double-close races

        def destroy():
            try:
                top.destroy()
            except Exception:
                pass

        if animate:
            self._fade(top, 1.0, 0.0, on_done=destroy)
        else:
            destroy()

    def _load_position(self) -> tuple[int, int]:
        if self._position_file and self._position_file.exists():
            try:
                data = json.loads(self._position_file.read_text())
                return int(data["x"]), int(data["y"])
            except Exception:
                pass
        return 40, 40  # default: top-left corner, out of the way

    def _save_position(self, x: int, y: int) -> None:
        if not self._position_file:
            return
        try:
            self._position_file.parent.mkdir(parents=True, exist_ok=True)
            self._position_file.write_text(json.dumps({"x": x, "y": y}))
        except Exception:
            logger.warning("Could not persist widget position", exc_info=True)
