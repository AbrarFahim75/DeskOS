"""UI layer contract."""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable

from deskos.core import FeedbackType, WidgetMood


class WidgetPresenter(ABC):
    """What the Services layer is allowed to know about the UI.

    Deliberately smaller than WidgetRenderer: a service can ask for one
    suggestion to be shown, and nothing else. This is the seam that keeps
    Services from importing a concrete UI class - NotificationService
    depends on this, and WidgetManager implements it.
    """

    @abstractmethod
    def show(
        self,
        message: str,
        mood: WidgetMood = WidgetMood.NEUTRAL,
        on_feedback: Callable[[FeedbackType], None] | None = None,
        duration_sec: float = 5.0,
    ) -> None:
        raise NotImplementedError


class WidgetRenderer(ABC):
    """Renders a single small floating widget with a short text message.
    Implementations own their own toolkit (tkinter, Qt, native OS overlay).
    """

    @abstractmethod
    def show(
        self,
        message: str,
        duration_sec: float,
        mood: WidgetMood = WidgetMood.NEUTRAL,
        on_feedback: Callable[[FeedbackType], None] | None = None,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def dismiss(self) -> None:
        raise NotImplementedError
