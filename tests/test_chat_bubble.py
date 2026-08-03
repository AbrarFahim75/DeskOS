"""Smoke test for the chat bubble widget.

Skips entirely on systems with no tkinter or no display (e.g. headless
CI) -- this only verifies the widget builds and toggles state without
crashing, not visual rendering.
"""
from __future__ import annotations

import pytest

tk = pytest.importorskip("tkinter")


def _display_available() -> bool:
    try:
        root = tk.Tk()
        root.destroy()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _display_available(), reason="no display available for Tk")

from deskos.ui.widgets.chat_bubble import ChatBubble  # noqa: E402


def test_bubble_builds_collapsed_by_default():
    bubble = ChatBubble()
    bubble._build()
    try:
        assert bubble._expanded is False
    finally:
        bubble._root.destroy()


def test_bubble_toggles_between_collapsed_and_expanded():
    bubble = ChatBubble()
    bubble._build()
    try:
        bubble._show_expanded()
        assert bubble._expanded is True
        bubble._show_collapsed()
        assert bubble._expanded is False
    finally:
        bubble._root.destroy()


def test_on_message_callback_is_used_for_replies():
    received = []
    bubble = ChatBubble(on_message=lambda text: received.append(text) or "ok")
    bubble._build()
    try:
        bubble._entry.insert(0, "play my favorite song")
        bubble._on_send()
        assert received == ["play my favorite song"]
    finally:
        bubble._root.destroy()
