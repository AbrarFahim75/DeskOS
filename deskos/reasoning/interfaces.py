"""Reasoning layer contract."""
from __future__ import annotations

from abc import ABC, abstractmethod

from deskos.core import ContextSnapshot, Suggestion
from deskos.knowledge.interfaces import HabitStore


class Reasoner(ABC):
    """Produces candidate Suggestions from the current context (and,
    optionally, derived Habits). Does NOT decide whether to act — that is
    the Decision Engine's job. A Reasoner may propose nothing.
    """

    @abstractmethod
    def reason(self, context: ContextSnapshot, habits: HabitStore) -> list[Suggestion]:
        raise NotImplementedError
