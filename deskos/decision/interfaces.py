"""Decision layer contract."""
from __future__ import annotations

from abc import ABC, abstractmethod

from deskos.core import Action, Suggestion


class DecisionMaker(ABC):
    """Filters candidate Suggestions down to approved Actions.

    This is the sole home of "should DeskOS react?" - confidence gating,
    cooldowns, and repetition suppression all live here so no other layer
    needs to reimplement the golden rule: prefer silence.
    """

    @abstractmethod
    def decide(self, suggestions: list[Suggestion]) -> list[Action]:
        raise NotImplementedError
