"""The Services -> UI seam after Milestone 2.

Two things are pinned here: WidgetManager routes rendering through the UI
host (so a background thread never touches Tk directly), and
NotificationService depends only on the WidgetPresenter contract, not on
any concrete widget class.
"""
from __future__ import annotations

from deskos.config.settings import UISettings
from deskos.core import (
    Action,
    ActionType,
    FeedbackType,
    WidgetMood,
)
from deskos.knowledge.history_store import InMemoryHistoryStore
from deskos.services.notification_service import NotificationService
from deskos.ui.interfaces import WidgetPresenter, WidgetRenderer
from deskos.ui.widget_manager import WidgetManager

UI_SETTINGS = UISettings(widget_fade_ms=300, widget_max_visible=1)


class RecordingRenderer(WidgetRenderer):
    def __init__(self) -> None:
        self.shown: list[str] = []
        self.dismissed = 0

    def show(self, message, duration_sec, mood=WidgetMood.NEUTRAL, on_feedback=None) -> None:
        self.shown.append(message)

    def dismiss(self) -> None:
        self.dismissed += 1


class ImmediateHost:
    """A stand-in UIHost that runs posted callbacks synchronously."""

    def __init__(self) -> None:
        self.posts = 0

    def post(self, func) -> None:
        self.posts += 1
        func()


def test_manager_dismisses_then_shows_one_widget():
    renderer = RecordingRenderer()
    manager = WidgetManager(renderer, UI_SETTINGS)

    manager.show("Break?")

    assert renderer.dismissed == 1, "must clear any existing widget first"
    assert renderer.shown == ["Break?"]


def test_manager_routes_through_the_ui_host_when_present():
    renderer = RecordingRenderer()
    host = ImmediateHost()
    manager = WidgetManager(renderer, UI_SETTINGS, ui_host=host)

    manager.show("Focus music?")

    assert host.posts == 1, "render must be marshalled onto the UI thread"
    assert renderer.shown == ["Focus music?"]


def test_notification_service_depends_only_on_the_presenter_contract():
    class SpyPresenter(WidgetPresenter):
        def __init__(self) -> None:
            self.messages: list[str] = []

        def show(self, message, mood=WidgetMood.NEUTRAL, on_feedback=None, duration_sec=5.0) -> None:
            self.messages.append(message)

    presenter = SpyPresenter()
    service = NotificationService(presenter, InMemoryHistoryStore())

    action = Action(
        type=ActionType.SHOW_WIDGET,
        payload={"suggestion_type": "TAKE_BREAK", "mood": WidgetMood.POSITIVE.name},
    )
    result = service.execute(action)

    assert presenter.messages, "the approved suggestion should have been shown"
    assert result.service_name == "notification"


def test_notification_feedback_is_recorded_to_history():
    class ImmediatePresenter(WidgetPresenter):
        """Fires the feedback callback as if the user clicked, immediately."""

        def show(self, message, mood=WidgetMood.NEUTRAL, on_feedback=None, duration_sec=5.0) -> None:
            if on_feedback is not None:
                on_feedback(FeedbackType.HELPFUL)

    history = InMemoryHistoryStore()
    service = NotificationService(ImmediatePresenter(), history)

    service.execute(
        Action(type=ActionType.SHOW_WIDGET, payload={"suggestion_type": "TAKE_BREAK"})
    )

    feedback = history.get_feedback()
    assert len(feedback) == 1
    assert feedback[0].feedback == FeedbackType.HELPFUL
