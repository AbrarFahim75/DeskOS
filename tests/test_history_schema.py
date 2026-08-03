"""Schema versioning for the on-disk history database.

Milestone 1 changed what a context_transitions row *means* (one per state
change, not one per tick). Old rows cannot be converted into real sessions,
so opening a pre-v2 database rebuilds it rather than mixing the two.
"""
from __future__ import annotations

import sqlite3

from deskos.core import ContextSnapshot, ContextState
from deskos.knowledge.history_store import SQLiteHistoryStore


def test_new_database_is_created_at_the_current_version(tmp_path):
    db = tmp_path / "habits.db"
    store = SQLiteHistoryStore(db)
    store.close()

    with sqlite3.connect(db) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 2


def test_existing_current_version_database_keeps_its_rows(tmp_path):
    db = tmp_path / "habits.db"

    store = SQLiteHistoryStore(db)
    store.record_context_transition(
        ContextSnapshot(state=ContextState.CODING, confidence=0.9)
    )
    store.close()

    reopened = SQLiteHistoryStore(db)
    try:
        assert len(reopened.get_context_transitions()) == 1
    finally:
        reopened.close()


def test_stale_database_is_rebuilt(tmp_path, caplog):
    """A v1 database full of per-tick rows must not survive the upgrade."""
    db = tmp_path / "habits.db"

    with sqlite3.connect(db) as conn:
        conn.executescript(
            """
            CREATE TABLE context_transitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                state TEXT NOT NULL,
                confidence REAL NOT NULL,
                timestamp REAL NOT NULL
            );
            PRAGMA user_version = 1;
            """
        )
        for i in range(100):
            conn.execute(
                "INSERT INTO context_transitions (state, confidence, timestamp) "
                "VALUES ('CODING', 0.9, ?)",
                (1000.0 + i,),
            )

    store = SQLiteHistoryStore(db)
    try:
        assert store.get_context_transitions() == []
    finally:
        store.close()

    with sqlite3.connect(db) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 2
