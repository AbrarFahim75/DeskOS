"""Dispatches approved Actions to the Service(s) that handle them, and
records every ExecutionResult into History - success or failure - so
future reasoning can learn from real-world execution outcomes, not just
approved intent.

This is also where a suggestion is recorded as *shown*, which starts its
cooldown. Doing it here rather than in the Decision Engine means the
cooldown reflects what the user actually saw: a service that fails or
skips does not silence that suggestion for the next ten minutes.
"""
from __future__ import annotations

import logging
import time

from deskos.core import Action, ExecutionResult, ExecutionStatus, SuggestionType
from deskos.knowledge.interfaces import HistoryStore
from deskos.services.interfaces import Service

logger = logging.getLogger(__name__)


class ServiceRegistry:
    def __init__(self, services: list[Service], history: HistoryStore) -> None:
        self._services = services
        self._history = history

    @property
    def history(self) -> HistoryStore:
        """The shared history store, so callers assembling a loop reuse the
        same instance rather than opening a second connection to the DB.
        """
        return self._history

    def dispatch(self, actions: list[Action]) -> None:
        for action in actions:
            handled = False
            for service in self._services:
                if action.type in service.handles:
                    handled = True
                    result = self._execute_with_timing(service, action)
                    self._history.record_execution_result(result)
                    if result.status == ExecutionStatus.SUCCESS:
                        self._record_shown(action)
                    if result.status == ExecutionStatus.FAILED:
                        logger.warning(
                            "%s failed executing %s: %s", service.name, action.type, result.error_message
                        )
            if not handled:
                logger.warning("No service registered for action: %s", action.type)

    def _execute_with_timing(self, service: Service, action: Action) -> ExecutionResult:
        start = time.time()
        try:
            result = service.execute(action)
        except Exception as exc:  # a misbehaving Service must never crash the loop
            return ExecutionResult(
                action=action,
                service_name=service.name,
                status=ExecutionStatus.FAILED,
                duration_sec=time.time() - start,
                error_message=str(exc),
            )
        return result

    def _record_shown(self, action: Action) -> None:
        """Start the cooldown for the suggestion behind a delivered Action.

        Actions not originating from a Suggestion (or carrying an unknown
        type) are simply ignored rather than treated as an error.
        """
        name = action.payload.get("suggestion_type")
        if name in SuggestionType.__members__:
            self._history.record_suggestion_shown(SuggestionType[name], time.time())
