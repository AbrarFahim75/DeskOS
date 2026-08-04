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

    def __init__(self, running: bool = False) -> None:
        # Starts stopped: DeskOS has no timer running until something starts
        # one. Assuming otherwise made the first PAUSE_TIMER a no-op that
        # still reported success.
        self._running = running

    @property
    def name(self) -> str:
        return "timer"

    @property
    def handles(self) -> set[ActionType]:
        return {ActionType.PAUSE_TIMER, ActionType.RESUME_TIMER}

    def execute(self, action: Action) -> ExecutionResult:
        start = time.time()
        wants_running = action.type == ActionType.RESUME_TIMER

        # Already in the requested state: report SKIPPED rather than SUCCESS.
        # A SUCCESS would start this suggestion's cooldown for work that
        # never happened, silencing a genuinely useful prompt later. On
        # startup DeskOS used to "pause" a timer that was never running.
        if wants_running == self._running:
            return ExecutionResult(
                action=action,
                service_name=self.name,
                status=ExecutionStatus.SKIPPED,
                duration_sec=time.time() - start,
            )

        self._running = wants_running
        logger.info("Timer %s", "resumed" if wants_running else "paused")
        return ExecutionResult(
            action=action,
            service_name=self.name,
            status=ExecutionStatus.SUCCESS,
            duration_sec=time.time() - start,
        )
