"""HabitStore implementation: derives patterns from a HistoryStore.

Real (not stubbed) aggregation over whatever History has recorded so far.
Deliberately simple in-Python computation rather than SQL aggregation -
easy to reason about and independent of which HistoryStore backend is used.
"""
from __future__ import annotations

from datetime import datetime

from deskos.core import FeedbackType
from deskos.knowledge.interfaces import HabitStore, HistoryStore

_MIN_SAMPLES_FOR_ACCEPTANCE_RATE = 5


class InferredHabitStore(HabitStore):
    def __init__(self, history: HistoryStore) -> None:
        self._history = history

    def average_session_duration(self, state_name: str) -> float | None:
        transitions = self._history.get_context_transitions()
        durations = [
            transitions[i + 1].timestamp - transitions[i].timestamp
            for i in range(len(transitions) - 1)
            if transitions[i].state.name == state_name
        ]
        if not durations:
            return None
        return sum(durations) / len(durations)

    def typical_time_for_state(self, state_name: str) -> str | None:
        entry_times = [
            t.timestamp for t in self._history.get_context_transitions() if t.state.name == state_name
        ]
        if not entry_times:
            return None
        avg_seconds_into_day = sum(
            datetime.fromtimestamp(ts).hour * 3600 + datetime.fromtimestamp(ts).minute * 60
            for ts in entry_times
        ) / len(entry_times)
        hour, minute = divmod(int(avg_seconds_into_day // 60), 60)
        return f"usually around {hour:02d}:{minute:02d}"

    def acceptance_rate(self, suggestion_type_name: str) -> float | None:
        judgments = [
            f.feedback
            for f in self._history.get_feedback()
            if f.suggestion_type.name == suggestion_type_name
            and f.feedback in (FeedbackType.HELPFUL, FeedbackType.NOT_HELPFUL)
        ]
        if len(judgments) < _MIN_SAMPLES_FOR_ACCEPTANCE_RATE:
            return None  # avoid overfitting to a handful of interactions
        helpful = sum(1 for f in judgments if f == FeedbackType.HELPFUL)
        return helpful / len(judgments)
