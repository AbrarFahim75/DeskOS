"""UI layer contract."""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable

from deskos.core import FeedbackType, WidgetMood


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
