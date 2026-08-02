"""Placeholder timer integration (e.g. Pomodoro/focus timer)."""
from __future__ import annotations

import logging
import time

from deskos.core import Action, ActionType, ExecutionResult, ExecutionStatus
from deskos.services.interfaces import Service

logger = logging.getLogger(__name__)


class TimerService(Service):
    """Pauses/resumes a focus timer. TODO: wire to a real timer
    implementation (in-process or OS-level); currently logs only.
    """

    def __init__(self) -> None:
        self._running = True

    @property
    def name(self) -> str:
        return "timer"

    @property
    def handles(self) -> set[ActionType]:
        return {ActionType.PAUSE_TIMER, ActionType.RESUME_TIMER}

    def execute(self, action: Action) -> ExecutionResult:
        start = time.time()
        if action.type == ActionType.PAUSE_TIMER:
            self._running = False
            logger.info("Timer paused")
        elif action.type == ActionType.RESUME_TIMER:
            self._running = True
            logger.info("Timer resumed")
        return ExecutionResult(
            action=action,
            service_name=self.name,
            status=ExecutionStatus.SUCCESS,
            duration_sec=time.time() - start,
        )
