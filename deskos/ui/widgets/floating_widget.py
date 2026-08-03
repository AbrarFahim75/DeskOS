"""Tkinter-based floating widget skeleton.

Runs its own persistent background thread with a real Tk event loop —
tkinter windows never render or process input without one, and the app's
own loop (in main.py) is a plain sleep-based tick, not a GUI event loop.
Commands (show/dismiss) are handed to that thread via a thread-safe queue.

Deliberately minimal beyond that: fades in/holds/fades out, remembers the
user-moved position across launches, applies a subtle mood-based accent,
and reveals feedback controls on hover so the resting state stays ambient.
TODO: replace with a proper OS-native overlay (e.g. pywebview) for polish.
"""
from __future__ import annotations

import json
import logging
import queue
import threading
from collections.abc import Callable
from pathlib import Path

from deskos.core import FeedbackType, WidgetMood
from deskos.ui.interfaces import WidgetRenderer

logger = logging.getLogger(__name__)

_MOOD_ACCENT: dict[WidgetMood, str] = {
    WidgetMood.NEUTRAL: "#3a3a3c",
    WidgetMood.POSITIVE: "#2f6f4f",
    WidgetMood.IMPORTANT: "#7a4a1f",
}

_FADE_STEP_MS = 15
_FADE_STEPS = 12  # ~180ms fade in/out — smooth, never flashy


class FloatingWidget(WidgetRenderer):
    def __init__(self, position_file: Path | None = None) -> None:
        self._position_file = position_file
        self._commands: queue.Queue[tuple] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()

    def _ensure_thread_running(self) -> bool:
        if self._thread is not None:
            return True
        try:
            import tkinter  # noqa: F401  — fail fast on the caller's thread
        except ImportError:
            logger.info("tkinter not available; widget will not be shown")
            return False
        self._thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self._thread.start()
        self._ready.wait(timeout=5)
        return True

    def show(
        self,
        message: str,
        duration_sec: float,
        mood: WidgetMood = WidgetMood.NEUTRAL,
        on_feedback: Callable[[FeedbackType], None] | None = None,
    ) -> None:
        if not self._ensure_thread_running():
            return
        self._commands.put(("show", message, duration_sec, mood, on_feedback))

    def dismiss(self) -> None:
        if self._thread is not None:
            self._commands.put(("dismiss",))

    def _run_event_loop(self) -> None:
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()  # hidden root exists only to own the event loop
        state: dict = {"toplevel": None, "dismiss_job": None}

        def poll_commands() -> None:
            try:
                while True:
                    cmd = self._commands.get_nowait()
                    if cmd[0] == "show":
                        _, message, duration_sec, mood, on_feedback = cmd
                        self._open_widget(tk, root, state, message, duration_sec, mood, on_feedback)
                    elif cmd[0] == "dismiss":
                        self._close_widget(state)
            except queue.Empty:
                pass
            root.after(50, poll_commands)

        root.after(50, poll_commands)
        self._ready.set()
        root.mainloop()

    def _open_widget(self, tk, root, state, message, duration_sec, mood, on_feedback) -> None:
        self._close_widget(state, animate=False)

        top = tk.Toplevel(root)
        top.overrideredirect(True)
        top.attributes("-topmost", True)
        top.attributes("-alpha", 0.0)
        x, y = self._load_position()
        top.geometry(f"+{x}+{y}")
        accent = _MOOD_ACCENT.get(mood, _MOOD_ACCENT[WidgetMood.NEUTRAL])

        container = tk.Frame(top, bg=accent)
        container.pack()
        label = tk.Label(container, text=message, font=("Helvetica", 14), padx=16, pady=10, fg="white", bg=accent)
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
                command=lambda ft=feedback_type: self._feedback_clicked(state, ft, on_feedback),
            ).pack(side="left", padx=4)

        container.bind("<Enter>", lambda _e: controls.pack(pady=(0, 6)))
        container.bind("<Leave>", lambda _e: controls.pack_forget())
        label.bind("<ButtonPress-1>", lambda e: top.geometry(f"+{e.x_root}+{e.y_root}"))
        top.bind("<ButtonRelease-1>", lambda e: self._save_position(top.winfo_x(), top.winfo_y()))

        state["toplevel"] = top
        self._fade(top, 0.0, 1.0, on_done=lambda: self._schedule_auto_dismiss(top, state, duration_sec))

    def _feedback_clicked(self, state, feedback_type: FeedbackType, on_feedback: Callable | None) -> None:
        if on_feedback is not None:
            on_feedback(feedback_type)
        self._close_widget(state)  # any feedback dismisses immediately, never waits out the timer

    def _schedule_auto_dismiss(self, top, state, duration_sec: float) -> None:
        if state.get("toplevel") is top:
            state["dismiss_job"] = top.after(int(duration_sec * 1000), lambda: self._close_widget(state))

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

    def _close_widget(self, state, animate: bool = True) -> None:
        top = state.get("toplevel")
        if top is None:
            return
        if state.get("dismiss_job") is not None:
            try:
                top.after_cancel(state["dismiss_job"])
            except Exception:
                pass
            state["dismiss_job"] = None

        def destroy():
            try:
                top.destroy()
            except Exception:
                pass
            if state.get("toplevel") is top:
                state["toplevel"] = None

        state["toplevel"] = None  # prevent double-close races
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
