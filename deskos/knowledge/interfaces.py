"""Knowledge layer contracts, split into History (raw record) and Habits
(derived knowledge). Knowledge stores and computes facts; it never decides
or reacts - Reasoning/Decision read from it, they don't hand it authority.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from deskos.core import ContextSnapshot, ExecutionResult, SuggestionFeedback, SuggestionType


class HistoryStore(ABC):
    """The raw, append-only factual record. No judgment, no aggregation -
    just "what happened, and when". This is the ground truth everything
    else (including Habits) is computed from.
    """

    @abstractmethod
    def record_context_transition(self, snapshot: ContextSnapshot) -> None:
        """Log that context changed to `snapshot.state` at `snapshot.timestamp`."""
        raise NotImplementedError

    @abstractmethod
    def record_suggestion_shown(self, suggestion_type: SuggestionType, timestamp: float) -> None:
        raise NotImplementedError

    @abstractmethod
    def record_feedback(self, feedback: SuggestionFeedback) -> None:
        """Log explicit, voluntary user feedback on a shown Suggestion.

        Absence of feedback must never be synthesized and passed here -
        only genuine user actions (👍/👎/✖/⏰) are recorded.
        """
        raise NotImplementedError

    @abstractmethod
    def seconds_since_last_suggestion(self, suggestion_type: SuggestionType) -> float | None:
        """Used by Decision for cooldown checks. None if never shown."""
        raise NotImplementedError

    @abstractmethod
    def record_execution_result(self, result: ExecutionResult) -> None:
        """Log the real-world outcome of a Service executing an Action -
        success or failure alike. Feeds debugging, reliability metrics,
        and future adaptive reasoning (e.g. stop suggesting an integration
        that keeps failing).
        """
        raise NotImplementedError

    @abstractmethod
    def get_context_transitions(self) -> list[ContextSnapshot]:
        """Raw transition log, for HabitStore aggregation. Read-only."""
        raise NotImplementedError

    @abstractmethod
    def get_feedback(self) -> list[SuggestionFeedback]:
        """Raw feedback log, for HabitStore aggregation. Read-only."""
        raise NotImplementedError


class HabitStore(ABC):
    """Derived knowledge, computed (periodically or on-demand) from
    HistoryStore. Answers "what does the user usually do", never "what
    just happened" (that's History) and never "what should we do about
    it" (that's Reasoning/Decision).
    """

    @abstractmethod
    def average_session_duration(self, state_name: str) -> float | None:
        """Average duration of a context state, in seconds, across
        recorded sessions. TODO: implement aggregation once enough
        transition history exists to make this meaningful.
        """
        raise NotImplementedError

    @abstractmethod
    def typical_time_for_state(self, state_name: str) -> str | None:
        """E.g. 'usually studies after 19:00'. TODO: derive from
        recorded transition timestamps; stubbed until History has data.
        """
        raise NotImplementedError

    @abstractmethod
    def acceptance_rate(self, suggestion_type_name: str) -> float | None:
        """Derived from explicit HELPFUL/NOT_HELPFUL feedback only -
        never from DISMISSED or missing responses. Lets Reasoning/Decision
        personalize without overfitting to a single interaction.
        """
        raise NotImplementedError
