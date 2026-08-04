"""Persistent, always-on-top chat bubble widget.

Unlike `floating_widget.FloatingWidget` (a transient suggestion toast that
fades in/out on its own), this widget stays visible on screen permanently
as a small transparent circle. Clicking it expands into a minimal chat
panel; clicking the panel's collapse control returns it to the bubble.

Runs as a guest inside a Tk root owned by `UIHost`, so it can coexist with
the suggestion widget and the perception loop in one process. Call
`attach(root)` once on the UI thread to build it; it draws into that root
rather than creating its own.

Transparency uses Tk's `-transparentcolor` window attribute (Windows-only):
any pixel left at that exact color becomes both invisible and click-through,
so the square window can host a round, transparent-cornered bubble. On
platforms where that attribute isn't supported, we fall back to a plain
translucent square -- less pretty, still functional.
"""
from __future__ import annotations

import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_BUBBLE_SIZE = 64
_PANEL_WIDTH = 320
_PANEL_HEIGHT = 400
_TRANSPARENT_KEY = "#ff00fe"  # arbitrary, unlikely-to-collide magenta
_ACCENT = "#3a3a7c"
_PANEL_BG = "#1e1e24"
_DRAG_THRESHOLD_PX = 4


class ChatBubble:
    def __init__(
        self,
        position_file: Path | None = None,
        on_message: Callable[[str], str] | None = None,
    ) -> None:
        self._position_file = position_file
        self._on_message = on_message or (lambda _text: "(no assistant connected yet)")
        self._expanded = False
        self._supports_transparency = False
        self._drag = {"x": 0, "y": 0, "moved": False}
        self._root: Any = None

    def attach(self, root: Any) -> None:
        """Build the bubble as a child of a shared Tk root.

        Call once, on the UI thread. Replaces the old `run()`, which created
        and owned its own root - incompatible with hosting other widgets.
        """
        self._root = root
        self._build()

    def _build(self) -> None:
        """Constructs the window and widgets without entering the event
        loop. Uses the shared root given via `attach()`. Split out so tests
        can build and inspect the widget tree without a running loop.
        """
        import tkinter as tk

        self._tk = tk
        root = self._root if self._root is not None else tk.Tk()
        if self._root is None:
            # Standalone/test fallback: no host supplied one, so make a
            # private hidden root purely to parent the window.
            root.withdraw()
        self._root = root

        self._window = tk.Toplevel(root)
        self._window.overrideredirect(True)
        self._window.attributes("-topmost", True)
        self._supports_transparency = self._try_enable_transparency(self._window)

        x, y = self._load_position()
        self._window.geometry(f"{_BUBBLE_SIZE}x{_BUBBLE_SIZE}+{x}+{y}")

        self._build_collapsed()
        self._build_expanded()
        self._show_collapsed()

    def _try_enable_transparency(self, window) -> bool:
        try:
            window.attributes("-transparentcolor", _TRANSPARENT_KEY)
            return True
        except Exception:
            try:
                window.attributes("-alpha", 0.92)
            except Exception:
                pass
            return False

    def _build_collapsed(self) -> None:
        tk = self._tk
        bg = _TRANSPARENT_KEY if self._supports_transparency else _ACCENT
        self._collapsed_frame = tk.Frame(self._window, bg=bg)
        canvas = tk.Canvas(
            self._collapsed_frame, width=_BUBBLE_SIZE, height=_BUBBLE_SIZE,
            bg=bg, highlightthickness=0, cursor="hand2",
        )
        pad = 4
        canvas.create_oval(pad, pad, _BUBBLE_SIZE - pad, _BUBBLE_SIZE - pad, fill=_ACCENT, outline="")
        canvas.create_text(
            _BUBBLE_SIZE / 2, _BUBBLE_SIZE / 2, text="AI", fill="white",
            font=("Helvetica", 14, "bold"),
        )
        canvas.pack()
        self._bind_drag(canvas)

    def _build_expanded(self) -> None:
        tk = self._tk
        self._expanded_frame = tk.Frame(self._window, bg=_PANEL_BG)

        header = tk.Frame(self._expanded_frame, bg=_ACCENT, height=32, cursor="fleur")
        header.pack(fill="x")
        tk.Label(
            header, text="DeskOS", bg=_ACCENT, fg="white", font=("Helvetica", 11, "bold"),
        ).pack(side="left", padx=10)
        collapse_btn = tk.Label(
            header, text="-", bg=_ACCENT, fg="white", font=("Helvetica", 14, "bold"),
            cursor="hand2",
        )
        collapse_btn.pack(side="right", padx=10)
        collapse_btn.bind("<Button-1>", lambda _e: self._show_collapsed())
        self._bind_drag(header)

        self._output = tk.Text(
            self._expanded_frame, width=36, height=16, bg=_PANEL_BG, fg="white",
            wrap="word", relief="flat", state="disabled", font=("Helvetica", 10),
        )
        self._output.pack(fill="both", expand=True, padx=8, pady=(8, 4))
        self._append_line("DeskOS: Hi! Type a message below.")

        entry_row = tk.Frame(self._expanded_frame, bg=_PANEL_BG)
        entry_row.pack(fill="x", padx=8, pady=(0, 8))
        self._entry = tk.Entry(entry_row, font=("Helvetica", 10))
        self._entry.pack(side="left", fill="both", expand=True)
        self._entry.bind("<Return>", self._on_send)
        tk.Button(entry_row, text="Send", command=self._on_send).pack(side="left", padx=(6, 0))

    def _bind_drag(self, widget) -> None:
        widget.bind("<ButtonPress-1>", self._on_press)
        widget.bind("<B1-Motion>", self._on_motion)
        widget.bind("<ButtonRelease-1>", self._on_release)

    def _on_press(self, event) -> None:
        self._drag = {"x": event.x_root, "y": event.y_root, "moved": False}

    def _on_motion(self, event) -> None:
        dx = event.x_root - self._drag["x"]
        dy = event.y_root - self._drag["y"]
        if abs(dx) > _DRAG_THRESHOLD_PX or abs(dy) > _DRAG_THRESHOLD_PX:
            self._drag["moved"] = True
            new_x = self._window.winfo_x() + dx
            new_y = self._window.winfo_y() + dy
            self._window.geometry(f"+{new_x}+{new_y}")
            self._drag["x"] = event.x_root
            self._drag["y"] = event.y_root

    def _on_release(self, _event) -> None:
        if not self._drag["moved"] and not self._expanded:
            self._show_expanded()
        self._save_position(self._window.winfo_x(), self._window.winfo_y())

    def _show_collapsed(self) -> None:
        self._expanded_frame.pack_forget()
        if self._supports_transparency:
            self._window.attributes("-transparentcolor", _TRANSPARENT_KEY)
        x, y = self._window.winfo_x(), self._window.winfo_y()
        self._window.geometry(f"{_BUBBLE_SIZE}x{_BUBBLE_SIZE}+{x}+{y}")
        self._collapsed_frame.pack()
        self._expanded = False

    def _show_expanded(self) -> None:
        self._collapsed_frame.pack_forget()
        if self._supports_transparency:
            self._window.attributes("-transparentcolor", "")
        x, y = self._window.winfo_x(), self._window.winfo_y()
        self._window.geometry(f"{_PANEL_WIDTH}x{_PANEL_HEIGHT}+{x}+{y}")
        self._expanded_frame.pack(fill="both", expand=True)
        self._expanded = True
        self._entry.focus_set()

    def _on_send(self, _event=None) -> None:
        text = self._entry.get().strip()
        if not text:
            return
        self._entry.delete(0, "end")
        self._append_line(f"You: {text}")
        try:
            reply = self._on_message(text)
        except Exception:
            logger.exception("on_message handler raised")
            reply = "(something went wrong handling that)"
        self._append_line(f"DeskOS: {reply}")

    def _append_line(self, line: str) -> None:
        self._output.configure(state="normal")
        self._output.insert("end", line + "\n")
        self._output.see("end")
        self._output.configure(state="disabled")

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
            logger.warning("Could not persist bubble position", exc_info=True)
