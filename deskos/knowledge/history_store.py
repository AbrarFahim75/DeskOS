"""SQLite-backed HistoryStore: the raw factual log.

Three append-only tables: context transitions, suggestions shown, and user
responses. No aggregation happens here - that is HabitStore's job, reading
from these tables.
"""
from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path

from deskos.core import (
    ContextSnapshot,
    ContextState,
    ExecutionResult,
    FeedbackType,
    SuggestionFeedback,
    SuggestionType,
)
from deskos.knowledge.interfaces import HistoryStore


class SQLiteHistoryStore(HistoryStore):
    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        # The tick loop (main thread) and the UI thread (widget feedback)
        # both write to this connection concurrently - sqlite3 connections
        # aren't safe for concurrent use without external serialization.
        self._lock = threading.Lock()
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS context_transitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                state TEXT NOT NULL,
                confidence REAL NOT NULL,
                timestamp REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS suggestions_shown (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                suggestion_type TEXT NOT NULL,
                timestamp REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS suggestion_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                suggestion_type TEXT NOT NULL,
                feedback TEXT NOT NULL,
                timestamp REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS execution_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_type TEXT NOT NULL,
                service_name TEXT NOT NULL,
                status TEXT NOT NULL,
                duration_sec REAL NOT NULL,
                error_message TEXT,
                timestamp REAL NOT NULL
            );
            """
        )
        self._conn.commit()

    def record_context_transition(self, snapshot: ContextSnapshot) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO context_transitions (state, confidence, timestamp) VALUES (?, ?, ?)",
                (snapshot.state.name, snapshot.confidence, snapshot.timestamp),
            )
            self._conn.commit()

    def record_suggestion_shown(self, suggestion_type: SuggestionType, timestamp: float) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO suggestions_shown (suggestion_type, timestamp) VALUES (?, ?)",
                (suggestion_type.name, timestamp),
            )
            self._conn.commit()

    def record_feedback(self, feedback: SuggestionFeedback) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO suggestion_feedback (suggestion_type, feedback, timestamp) VALUES (?, ?, ?)",
                (feedback.suggestion_type.name, feedback.feedback.name, feedback.timestamp),
            )
            self._conn.commit()

    def seconds_since_last_suggestion(self, suggestion_type: SuggestionType) -> float | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT MAX(timestamp) FROM suggestions_shown WHERE suggestion_type = ?",
                (suggestion_type.name,),
            ).fetchone()
        if row is None or row[0] is None:
            return None
        return time.time() - row[0]

    def record_execution_result(self, result: ExecutionResult) -> None:
        with self._lock:
            self._conn.execute(
                """INSERT INTO execution_results
                   (action_type, service_name, status, duration_sec, error_message, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    result.action.type.name,
                    result.service_name,
                    result.status.name,
                    result.duration_sec,
                    result.error_message,
                    result.timestamp,
                ),
            )
            self._conn.commit()

    def get_context_transitions(self) -> list[ContextSnapshot]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT state, confidence, timestamp FROM context_transitions ORDER BY timestamp"
            ).fetchall()
        return [
            ContextSnapshot(state=ContextState[state], confidence=confidence, timestamp=timestamp)
            for state, confidence, timestamp in rows
        ]

    def get_feedback(self) -> list[SuggestionFeedback]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT suggestion_type, feedback, timestamp FROM suggestion_feedback ORDER BY timestamp"
            ).fetchall()
        return [
            SuggestionFeedback(
                suggestion_type=SuggestionType[suggestion_type],
                feedback=FeedbackType[feedback],
                timestamp=timestamp,
            )
            for suggestion_type, feedback, timestamp in rows
        ]

    def close(self) -> None:
        with self._lock:
            self._conn.close()


class InMemoryHistoryStore(HistoryStore):
    """Non-persistent HistoryStore for tests and offline development."""

    def __init__(self) -> None:
        self._transitions: list[ContextSnapshot] = []
        self._suggestions_shown: list[tuple[SuggestionType, float]] = []
        self._feedback: list[SuggestionFeedback] = []
        self._execution_results: list[ExecutionResult] = []

    def record_context_transition(self, snapshot: ContextSnapshot) -> None:
        self._transitions.append(snapshot)

    def record_suggestion_shown(self, suggestion_type: SuggestionType, timestamp: float) -> None:
        self._suggestions_shown.append((suggestion_type, timestamp))

    def record_feedback(self, feedback: SuggestionFeedback) -> None:
        self._feedback.append(feedback)

    def record_execution_result(self, result: ExecutionResult) -> None:
        self._execution_results.append(result)

    def get_context_transitions(self) -> list[ContextSnapshot]:
        return list(self._transitions)

    def get_feedback(self) -> list[SuggestionFeedback]:
        return list(self._feedback)

    def seconds_since_last_suggestion(self, suggestion_type: SuggestionType) -> float | None:
        matches = [ts for st, ts in self._suggestions_shown if st == suggestion_type]
        if not matches:
            return None
        return time.time() - max(matches)
