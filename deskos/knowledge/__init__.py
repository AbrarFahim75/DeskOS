"""Knowledge package: durable memory of the system.

Split by design: `History` is the raw factual record (context transitions,
suggestions shown, user responses, session durations). `Habits` is derived
knowledge computed from History over time (typical study time, average
coding session length). Reasoning/Decision consume both, but never need to
compute habits from raw history themselves.
"""
from deskos.knowledge.interfaces import HistoryStore, HabitStore
from deskos.knowledge.history_store import SQLiteHistoryStore, InMemoryHistoryStore
from deskos.knowledge.habit_store import InferredHabitStore

__all__ = [
    "HistoryStore",
    "HabitStore",
    "SQLiteHistoryStore",
    "InMemoryHistoryStore",
    "InferredHabitStore",
]
