"""The single owner of the Tk root and its event loop.

Tk has two hard rules that shape this whole module: there must be exactly
one `Tk()` root per process, and every widget call must happen on the
thread running its event loop. Before this, the chat bubble and the
suggestion widget each created their own root on different threads, so
they could not run together at all.

`UIHost` fixes that by owning the one root and the one `mainloop()`, on the
main thread. Everything else - the bubble, the suggestion toast, the
perception loop - is a guest. Guests that live on other threads (the
perception worker) never touch a widget directly; they hand work to
`post()`, which runs it on the UI thread via Tk's `after()`.
"""
from __future__ import annotations

import logging
import queue
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


class UIHost:
    """Owns the process-wide Tk root and marshals work onto the UI thread.

    Construct on the main thread, register widgets, then call `run()` which
    blocks until the app exits. Any thread may call `post()` to schedule a
    callable to run on the UI thread; this is the only safe way for a
    background thread to affect the interface.
    """

    def __init__(self) -> None:
        self._root: Any = None
        self._tk: Any = None
        self._pending: queue.Queue[Callable[[], None]] = queue.Queue()
        self._on_ready: list[Callable[[Any], None]] = []
        self._available = self._probe_tk()

    @property
    def available(self) -> bool:
        """False when tkinter cannot be imported or no display exists."""
        return self._available

    def _probe_tk(self) -> bool:
        try:
            import tkinter  # noqa: F401
        except ImportError:
            logger.info("tkinter not available; UI will not start")
            return False
        return True

    def on_ready(self, callback: Callable[[Any], None]) -> None:
        """Register a widget builder to run once the root exists.

        The callback receives the Tk root and should build its widgets as
        children of it. Called on the UI thread, in registration order,
        before the event loop starts processing user input.
        """
        self._on_ready.append(callback)

    def post(self, func: Callable[[], None]) -> None:
        """Schedule `func` to run on the UI thread as soon as possible.

        Safe to call from any thread. If the UI is not running, the call is
        dropped with a debug log rather than raising, so a background loop
        never crashes just because the display went away.
        """
        if not self._available:
            logger.debug("post() ignored; UI not available")
            return
        self._pending.put(func)

    def run(self) -> None:
        """Build the root, run every on_ready builder, then block on the loop."""
        if not self._available:
            logger.info("UIHost.run() called but no UI is available; returning")
            return

        import tkinter as tk

        self._tk = tk
        self._root = tk.Tk()
        self._root.withdraw()  # the root is just the loop owner; it draws nothing

        for build in self._on_ready:
            try:
                build(self._root)
            except Exception:
                logger.exception("A UI builder failed during startup")

        self._root.after(50, self._drain)
        self._root.mainloop()

    def _drain(self) -> None:
        """Run everything queued by post(), then reschedule itself."""
        try:
            while True:
                func = self._pending.get_nowait()
                try:
                    func()
                except Exception:
                    logger.exception("A posted UI callback failed")
        except queue.Empty:
            pass
        if self._root is not None:
            self._root.after(50, self._drain)

    def stop(self) -> None:
        """Ask the event loop to exit. Safe to call from any thread."""
        if self._root is not None:
            self.post(self._root.quit)
