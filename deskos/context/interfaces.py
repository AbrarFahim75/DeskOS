"""Context Engine layer contract."""
from __future__ import annotations

from abc import ABC, abstractmethod

from deskos.core import ContextSnapshot, Event


class ContextInferer(ABC):
    """Turns Events into the current ContextSnapshot.

    Deliberately swappable: today a rule engine, tomorrow a classifier or
    an LLM call. Callers only ever depend on this interface.
    """

    @abstractmethod
    def update(self, events: list[Event]) -> ContextSnapshot:
        """Feed newly confirmed Events; returns the (possibly unchanged)
        current ContextSnapshot.
        """
        raise NotImplementedError

    @abstractmethod
    def current(self) -> ContextSnapshot:
        """Return the last computed ContextSnapshot without new input."""
        raise NotImplementedError
