"""Services layer contract."""
from __future__ import annotations

from abc import ABC, abstractmethod

from deskos.core import Action, ActionType, ExecutionResult


class Service(ABC):
    """A single integration (timer, notifications, music, future Home
    Assistant, ...). Declares which ActionTypes it handles and executes
    them; ignores anything else.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Stable identifier used in ExecutionResult, e.g. 'timer', 'spotify'."""
        raise NotImplementedError

    @property
    @abstractmethod
    def handles(self) -> set[ActionType]:
        raise NotImplementedError

    @abstractmethod
    def execute(self, action: Action) -> ExecutionResult:
        raise NotImplementedError
