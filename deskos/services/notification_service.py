"""Routes SHOW_WIDGET actions to the UI's WidgetManager and records
whatever explicit feedback the user gives back into History.

Kept as a Service (not a direct UI call from Decision) so Decision never
imports UI — it only returns Actions, per architecture rule.
"""
from __future__ import annotations

import threading
import time

from deskos.core import (
    Action,
    ActionType,
    ExecutionResult,
    ExecutionStatus,
    FeedbackType,
    SuggestionFeedback,
    SuggestionType,
    WidgetMood,
)
from deskos.knowledge.interfaces import HistoryStore
from deskos.services.interfaces import Service
from deskos.ui.widget_manager import WidgetManager

_SUGGESTION_COPY: dict[str, str] = {
    "TAKE_BREAK": "\u2615 Break?",
    "PLAY_FOCUS_MUSIC": "\U0001F3B5 Focus music?",
}

_REMIND_LATER_DELAY_SEC = 600.0  # 10 minutes — a deferral, not a new suggestion cycle


class NotificationService(Service):
    """Translates an approved Action into a short widget message, wires
    up feedback capture, and re-queues on REMIND_LATER. No suggestion
    logic lives here — only what's needed to show and record a response.
    """

    def __init__(self, widget_manager: WidgetManager, history: HistoryStore) -> None:
        self._widget_manager = widget_manager
        self._history = history

    @property
    def name(self) -> str:
        return "notification"

    @property
    def handles(self) -> set[ActionType]:
        return {ActionType.SHOW_WIDGET}

    def execute(self, action: Action) -> ExecutionResult:
        start = time.time()
        suggestion_type_name = action.payload.get("suggestion_type", "")
        message = _SUGGESTION_COPY.get(suggestion_type_name, "")
        mood_name = action.payload.get("mood", WidgetMood.NEUTRAL.name)
        mood = WidgetMood[mood_name] if mood_name in WidgetMood.__members__ else WidgetMood.NEUTRAL

        status = ExecutionStatus.SKIPPED
        if message:
            self._widget_manager.show(
                message, mood=mood,
                on_feedback=lambda feedback: self._handle_feedback(action, suggestion_type_name, feedback, mood),
            )
            status = ExecutionStatus.SUCCESS
        return ExecutionResult(
            action=action, service_name=self.name, status=status, duration_sec=time.time() - start,
        )

    def _handle_feedback(self, action: Action, suggestion_type_name: str, feedback: FeedbackType, mood: WidgetMood) -> None:
        # Explicit feedback only — no-response is never recorded here.
        if suggestion_type_name in SuggestionType.__members__:
            self._history.record_feedback(
                SuggestionFeedback(
                    suggestion_type=SuggestionType[suggestion_type_name],
                    feedback=feedback,
                    timestamp=time.time(),
                )
            )
        if feedback == FeedbackType.REMIND_LATER:
            message = _SUGGESTION_COPY.get(suggestion_type_name, "")
            timer = threading.Timer(
                _REMIND_LATER_DELAY_SEC,
                lambda: self._widget_manager.show(
                    message, mood=mood,
                    on_feedback=lambda fb: self._handle_feedback(action, suggestion_type_name, fb, mood),
                ),
            )
            timer.daemon = True
            timer.start()
