"""UI layer contract."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable, Optional

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
        on_feedback: Optional[Callable[[FeedbackType], None]] = None,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def dismiss(self) -> None:
        raise NotImplementedError
