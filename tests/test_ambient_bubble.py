"""Ambient bubble smoke tests.

These need a real display, so they skip on headless CI runners. What they
pin is structural: the bubble rests as a dot, becomes a card when there is
something to say, and returns to a dot afterwards - the mechanism behind
"only one widget visible at a time".
"""
from __future__ import annotations

import pytest

from deskos.core import FeedbackType, WidgetMood
from deskos.ui.widgets.ambient_bubble import AmbientBubble

tk = pytest.importorskip("tkinter")


@pytest.fixture
def root():
    try:
        r = tk.Tk()
    except tk.TclError:
        pytest.skip("no display available")
    r.withdraw()
    yield r
    r.destroy()


@pytest.fixture
def bubble(root):
    b = AmbientBubble()
    b.attach(root)
    return b


def test_bubble_rests_as_a_dot(bubble):
    """At rest there is no card, only the canvas holding the dot."""
    assert bubble._card is None
    assert bubble._canvas is not None


def test_showing_a_suggestion_expands_into_a_card(bubble, root):
    bubble.show("Break?", duration_sec=60, mood=WidgetMood.POSITIVE)
    root.update()

    assert bubble._card is not None, "a suggestion should expand the bubble"


def test_the_message_is_rendered_somewhere_in_the_card(bubble, root):
    bubble.show("You have been here 45 minutes", duration_sec=60)
    root.update()

    texts = []

    def walk(widget):
        for child in widget.winfo_children():
            try:
                texts.append(child.cget("text"))
            except Exception:
                pass
            walk(child)

    walk(bubble._card)
    assert any("45 minutes" in str(t) for t in texts)


def test_feedback_is_forwarded_and_dismisses_the_card(bubble, root):
    received = []
    bubble.show("Break?", duration_sec=60, on_feedback=received.append)
    root.update()

    bubble._feedback(FeedbackType.HELPFUL, received.append)
    root.update()

    assert FeedbackType.HELPFUL in received


def test_only_one_card_exists_after_repeated_shows(bubble, root):
    """Showing twice must replace, never stack."""
    bubble.show("First", duration_sec=60)
    root.update()
    first = bubble._card

    bubble.show("Second", duration_sec=60)
    root.update()

    assert bubble._card is not first, "the card should have been replaced"
    assert len([w for w in bubble._window.winfo_children() if isinstance(w, tk.Frame)]) <= 1


def test_quit_callback_is_invoked(root):
    called = []
    b = AmbientBubble(on_quit=lambda: called.append(True))
    b.attach(root)

    b._quit()

    assert called == [True]
