"""The one visible surface DeskOS has: an ambient bubble.

At rest it is a small dot in the corner of your screen, doing nothing and
saying nothing. When there is something genuinely worth telling you, the
same bubble expands into a short suggestion card with feedback controls,
then collapses back on its own.

Why one widget rather than two: DeskOS previously had a persistent chat
bubble *and* a separate suggestion toast, which broke the "one widget at a
time" principle and meant two things could be on screen at once. Making the
bubble itself the renderer keeps that promise structurally, rather than by
remembering to enforce it.

The chat panel that used to live here was removed deliberately. It replied
with a canned placeholder string, which dressed a non-feature up as a
feature, and it framed DeskOS as a chatbot - the one thing the product
says it is not. It can come back when there is something real behind it.

Toolkit honesty: Tk cannot do per-pixel alpha, so the resting dot uses
colour-key transparency and its edge is slightly aliased. Genuine frosted
glass needs a different toolkit; that is a deliberate future change, not an
oversight.
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

_TRANSPARENT_KEY = "#ff00fe"  # arbitrary magenta, unlikely to appear in the UI

_DOT_SIZE = 44
_CARD_WIDTH = 300
_CARD_HEIGHT = 104

_SURFACE = "#17171a"
_TEXT = "#f2f2f4"
_MUTED = "#8b8b94"

# The accent is the only colour that changes with mood, and it is used
# sparingly: a thin bar, not a whole panel. Loud surfaces are not calm.
_MOOD_ACCENT: dict[WidgetMood, str] = {
    WidgetMood.NEUTRAL: "#5b6572",
    WidgetMood.POSITIVE: "#3f8f6b",
    WidgetMood.IMPORTANT: "#b0763a",
}

_FADE_STEPS = 10
_FADE_STEP_MS = 16
_RESTING_ALPHA = 0.55   # present but easy to ignore
_ACTIVE_ALPHA = 0.97
_DRAG_THRESHOLD_PX = 4


class AmbientBubble(WidgetRenderer):
    """A dot that becomes a suggestion and then a dot again.

    Renders into a Tk root owned by UIHost. Every method must run on the UI
    thread; background callers go through `UIHost.post`.
    """

    def __init__(
        self,
        position_file: Path | None = None,
        on_quit: Callable[[], None] | None = None,
    ) -> None:
        self._position_file = position_file
        self._on_quit = on_quit
        self._tk: Any = None
        self._root: Any = None
        self._window: Any = None
        self._canvas: Any = None
        self._card: Any = None
        self._dismiss_job: Any = None
        self._drag = {"x": 0, "y": 0, "moved": False}

    # --- lifecycle -----------------------------------------------------

    def attach(self, root: Any) -> None:
        """Build the bubble as a child of the shared Tk root. Call once."""
        import tkinter as tk

        self._tk = tk
        self._root = root

        window = tk.Toplevel(root)
        window.overrideredirect(True)
        window.attributes("-topmost", True)
        try:
            window.attributes("-transparentcolor", _TRANSPARENT_KEY)
            window.configure(bg=_TRANSPARENT_KEY)
        except Exception:
            # Not supported off Windows: fall back to an opaque square.
            window.configure(bg=_SURFACE)
        window.attributes("-alpha", _RESTING_ALPHA)

        x, y = self._load_position()
        window.geometry(f"{_DOT_SIZE}x{_DOT_SIZE}+{x}+{y}")
        self._window = window

        self._canvas = tk.Canvas(
            window, width=_DOT_SIZE, height=_DOT_SIZE,
            bg=_TRANSPARENT_KEY, highlightthickness=0, bd=0,
        )
        self._canvas.pack()
        self._draw_dot()
        self._bind_drag(self._canvas)
        self._bind_menu(self._canvas)

    def _draw_dot(self) -> None:
        c = self._canvas
        c.delete("all")
        pad = 4
        c.create_oval(
            pad, pad, _DOT_SIZE - pad, _DOT_SIZE - pad,
            fill=_SURFACE, outline=_MUTED, width=1,
        )
        # A single small mark, not a label. "AI" written on a dot is a badge,
        # not a presence.
        centre = _DOT_SIZE // 2
        c.create_oval(
            centre - 3, centre - 3, centre + 3, centre + 3,
            fill=_MUTED, outline="",
        )

    # --- WidgetRenderer ------------------------------------------------

    def show(
        self,
        message: str,
        duration_sec: float,
        mood: WidgetMood = WidgetMood.NEUTRAL,
        on_feedback: Callable[[FeedbackType], None] | None = None,
    ) -> None:
        if self._window is None:
            logger.debug("AmbientBubble.show() before attach(); ignoring")
            return
        self._cancel_dismiss()
        self._expand(message, mood, on_feedback)
        self._dismiss_job = self._window.after(
            int(duration_sec * 1000), self.dismiss
        )

    def dismiss(self) -> None:
        if self._window is None or self._card is None:
            return
        self._cancel_dismiss()
        self._collapse()

    # --- expand / collapse ---------------------------------------------

    def _expand(self, message: str, mood: WidgetMood, on_feedback) -> None:
        tk = self._tk
        accent = _MOOD_ACCENT.get(mood, _MOOD_ACCENT[WidgetMood.NEUTRAL])

        # A second suggestion must replace the first, never stack on it.
        # This is the "one widget at a time" principle enforced in the one
        # place that could break it.
        if self._card is not None:
            self._card.destroy()
            self._card = None

        self._canvas.pack_forget()
        card = tk.Frame(self._window, bg=_SURFACE)
        card.pack(fill="both", expand=True)

        tk.Frame(card, bg=accent, height=3).pack(fill="x")  # thin accent bar

        body = tk.Frame(card, bg=_SURFACE)
        body.pack(fill="both", expand=True, padx=16, pady=(12, 8))
        tk.Label(
            body, text=message, bg=_SURFACE, fg=_TEXT,
            font=("Segoe UI", 12), wraplength=_CARD_WIDTH - 40,
            justify="left", anchor="w",
        ).pack(fill="x")

        controls = tk.Frame(card, bg=_SURFACE)
        controls.pack(fill="x", padx=12, pady=(0, 10))
        for label, feedback in (
            ("Thanks", FeedbackType.HELPFUL),
            ("Not now", FeedbackType.REMIND_LATER),
            ("Not useful", FeedbackType.NOT_HELPFUL),
        ):
            tk.Label(
                controls, text=label, bg=_SURFACE, fg=_MUTED,
                font=("Segoe UI", 9), cursor="hand2", padx=8,
            ).pack(side="left")
            controls.winfo_children()[-1].bind(
                "<Button-1>",
                lambda _e, f=feedback: self._feedback(f, on_feedback),
            )

        self._card = card
        self._bind_drag(card)
        self._bind_drag(body)
        self._bind_menu(card)

        x, y = self._window.winfo_x(), self._window.winfo_y()
        self._window.geometry(f"{_CARD_WIDTH}x{_CARD_HEIGHT}+{x}+{y}")
        self._fade(_RESTING_ALPHA, _ACTIVE_ALPHA)

    def _collapse(self) -> None:
        def finish() -> None:
            if self._card is not None:
                self._card.destroy()
                self._card = None
            self._canvas.pack()
            x, y = self._window.winfo_x(), self._window.winfo_y()
            self._window.geometry(f"{_DOT_SIZE}x{_DOT_SIZE}+{x}+{y}")
            self._fade(_ACTIVE_ALPHA, _RESTING_ALPHA)

        self._fade(_ACTIVE_ALPHA, 0.0, on_done=finish)

    def _feedback(self, feedback: FeedbackType, on_feedback) -> None:
        if on_feedback is not None:
            on_feedback(feedback)
        self.dismiss()  # any answer ends it; never make the user wait it out

    # --- interaction ---------------------------------------------------

    def _bind_drag(self, widget: Any) -> None:
        widget.bind("<ButtonPress-1>", self._drag_start, add="+")
        widget.bind("<B1-Motion>", self._drag_move, add="+")
        widget.bind("<ButtonRelease-1>", self._drag_end, add="+")

    def _drag_start(self, event) -> None:
        self._drag = {"x": event.x, "y": event.y, "moved": False}

    def _drag_move(self, event) -> None:
        dx = event.x - self._drag["x"]
        dy = event.y - self._drag["y"]
        if abs(dx) > _DRAG_THRESHOLD_PX or abs(dy) > _DRAG_THRESHOLD_PX:
            self._drag["moved"] = True
        self._window.geometry(
            f"+{self._window.winfo_x() + dx}+{self._window.winfo_y() + dy}"
        )

    def _drag_end(self, _event) -> None:
        if self._drag["moved"]:
            self._save_position(self._window.winfo_x(), self._window.winfo_y())

    def _bind_menu(self, widget: Any) -> None:
        """Right-click to quit.

        Without this the only way to stop DeskOS is Ctrl+C in a terminal,
        which then asks 'Terminate batch job (Y/N)?'. A companion you cannot
        politely dismiss is not calm.
        """
        tk = self._tk
        menu = tk.Menu(self._window, tearoff=0)
        menu.add_command(label="Quit DeskOS", command=self._quit)
        widget.bind("<Button-3>", lambda e: menu.tk_popup(e.x_root, e.y_root), add="+")

    def _quit(self) -> None:
        if self._on_quit is not None:
            self._on_quit()

    # --- animation and persistence -------------------------------------

    def _fade(self, start: float, end: float, on_done=None, step: int = 0) -> None:
        alpha = start + (end - start) * min(step / _FADE_STEPS, 1.0)
        try:
            self._window.attributes("-alpha", alpha)
        except Exception:
            return
        if step >= _FADE_STEPS:
            if on_done:
                on_done()
            return
        self._window.after(
            _FADE_STEP_MS, lambda: self._fade(start, end, on_done, step + 1)
        )

    def _cancel_dismiss(self) -> None:
        if self._dismiss_job is not None:
            try:
                self._window.after_cancel(self._dismiss_job)
            except Exception:
                pass
            self._dismiss_job = None

    def _load_position(self) -> tuple[int, int]:
        if self._position_file and self._position_file.exists():
            try:
                data = json.loads(self._position_file.read_text())
                return int(data["x"]), int(data["y"])
            except Exception:
                pass
        return 60, 60

    def _save_position(self, x: int, y: int) -> None:
        if not self._position_file:
            return
        try:
            self._position_file.parent.mkdir(parents=True, exist_ok=True)
            self._position_file.write_text(json.dumps({"x": x, "y": y}))
        except Exception:
            logger.warning("Could not persist bubble position", exc_info=True)
