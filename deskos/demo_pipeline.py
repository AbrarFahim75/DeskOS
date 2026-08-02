"""Real pipeline demo — lets you type a context state and watch it flow
through the ACTUAL Reasoning -> Decision -> Services layers (not just the
UI). Unlike demo_widget.py, this exercises real cooldowns, confidence
gating, and the user-value check — including DeskOS choosing to stay
silent, which is the point of the product.

Run: python -m deskos.demo_pipeline
Then type: coding / studying / break / away / quit
"""
from __future__ import annotations

from deskos.config.settings import load_settings
from deskos.context.context_engine import RuleBasedContextEngine
from deskos.core import ContextSnapshot, ContextState
from deskos.decision.decision_engine import DecisionEngine
from deskos.knowledge.habit_store import InferredHabitStore
from deskos.knowledge.history_store import SQLiteHistoryStore
from deskos.reasoning.rule_based_reasoner import RuleBasedReasoner
from deskos.services.notification_service import NotificationService
from deskos.services.service_registry import ServiceRegistry
from deskos.services.timer_service import TimerService
from deskos.ui.widget_manager import WidgetManager
from deskos.ui.widgets.floating_widget import FloatingWidget

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
        FloatingWidget(settings.storage.data_dir / "widget_position.json"), settings.ui
    )
    services = ServiceRegistry(
        [TimerService(), NotificationService(widget_manager, history_store)], history_store
    )

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

        context = ContextSnapshot(state=state, confidence=0.9)
        history_store.record_context_transition(context)
        suggestions = reasoner.reason(context, habit_store)
        actions = decision_engine.decide(suggestions)

        if not actions:
            print("  -> DeskOS stayed silent (no action approved).")
        else:
            services.dispatch(actions)
            for action in actions:
                print(f"  -> Action: {action.type.name} (approval: {action.approval_reason})")

    history_store.close()


if __name__ == "__main__":
    main()
