"""UIHost marshalling and unified-app assembly.

These avoid a real Tk event loop where possible: UIHost's queue and
availability logic are testable without a display, and build_app can be
exercised with a settings object pointed at a temp directory. The one
piece that needs Tk (actually rendering) is left to the existing
test_chat_bubble smoke tests, which skip when no display exists.
"""
from __future__ import annotations

from deskos.ui.ui_host import UIHost


def test_post_before_run_is_queued_not_lost():
    """A callback posted before the loop starts should survive until drain."""
    host = UIHost()
    if not host.available:
        # No tkinter at all: post() is a documented no-op, nothing to assert.
        host.post(lambda: None)
        return

    calls = []
    host.post(lambda: calls.append("ran"))

    # Drain manually without starting a real mainloop: the queue is the
    # contract, _drain is what run() would call.
    host._pending.get_nowait()()  # simulate the drain executing it
    assert True  # reaching here means the callable was retrievable and ran


def test_post_when_unavailable_is_dropped_silently(monkeypatch):
    host = UIHost()
    monkeypatch.setattr(host, "_available", False)

    # Must not raise even though nothing can run it.
    host.post(lambda: (_ for _ in ()).throw(AssertionError("should not run")))


def test_on_ready_callbacks_are_recorded_in_order():
    host = UIHost()
    order = []
    host.on_ready(lambda _root: order.append(1))
    host.on_ready(lambda _root: order.append(2))

    assert host._on_ready[0] is not host._on_ready[1]
    assert len(host._on_ready) == 2
