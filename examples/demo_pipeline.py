"""Real pipeline demo - lets you type a context state and watch it flow
through the ACTUAL Reasoning -> Decision -> Services layers (not just the
UI). Unlike demo_widget.py, this exercises real cooldowns, confidence
gating, and the user-value check - including DeskOS choosing to stay
silent, which is the point of the product.

Each entry prints one pipeline line showing the inferred context and what
the Decision Engine did with it, including the reason for any silence.

Run: python examples/demo_pipeline.py
Then type: coding / studying / break / away / quit
"""
from __future__ import annotations

import sys
from pathlib import Path

# Allow running this file directly (`python examples/demo_x.py`) without
# having installed DeskOS first: put the repository root on the import path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from deskos.config.settings import load_settings
from deskos.core import ContextSnapshot, ContextState
from deskos.decision.decision_engine import DecisionEngine
from deskos.knowledge.habit_store import InferredHabitStore
from deskos.knowledge.history_store import SQLiteHistoryStore
from deskos.observability import PipelineTrace
from deskos.observability.terminal_observer import TerminalObserver
from deskos.reasoning.rule_based_reasoner import RuleBasedReasoner
from deskos.services.notification_service import NotificationService
from deskos.services.service_registry import ServiceRegistry
from deskos.services.timer_service import TimerService
from deskos.ui.widget_manager import WidgetManager
from deskos.ui.widgets.ambient_bubble import AmbientBubble

_STATE_ALIASES = {
    "coding": ContextState.CODING,
    "studying": ContextState.STUDYING,
    "break": ContextState.BREAK,
    "away": ContextState.AWAY,
}


def main() -> None:
    settings = load_settings()
    history_store = SQLiteHistoryStore(settings.storage.habits_db_path)
    habit_store = InferredHabitStore(history_store)
    reasoner = RuleBasedReasoner()
    decision_engine = DecisionEngine(settings.decision_engine, history_store)
    widget_manager = WidgetManager(
        AmbientBubble(settings.storage.data_dir / "bubble_position.json"), settings.ui
    )
    services = ServiceRegistry(
        [TimerService(), NotificationService(widget_manager, history_store)], history_store
    )
    # Always verbose here: seeing *why* DeskOS stayed silent is the whole
    # point of this demo, so unlike the real app it never hides a tick.
    observer = TerminalObserver(stream=sys.stdout, verbose=True)

    print("Type a state (coding / studying / break / away) or 'quit'.")
    print("Repeating the same state within the cooldown window will correctly produce silence.\n")

    while True:
        raw = input("> ").strip().lower()
        if raw in ("quit", "exit"):
            break
        state = _STATE_ALIASES.get(raw)
        if state is None:
            print("Unknown state. Try: coding, studying, break, away, quit")
            continue

        context = ContextSnapshot(state=state, confidence=0.9, is_transition=True)
        history_store.record_context_transition(context)
        suggestions = reasoner.reason(context, habit_store)

        evaluated = decision_engine.evaluate(suggestions)
        actions = [a for a, _ in evaluated if a is not None]
        observer.on_tick(
            PipelineTrace(
                context=context,
                suggestions=tuple(suggestions),
                outcomes=tuple(o for _, o in evaluated),
            )
        )
        services.dispatch(actions)

    history_store.close()


if __name__ == "__main__":
    main()
