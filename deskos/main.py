"""DeskOS entry point.

Wires every layer together and runs the main perception loop. Contains NO
business logic itself - only construction and orchestration, per the
architecture rule that main.py just wires modules together.
"""
from __future__ import annotations

import logging
import time

from deskos.camera.webcam_source import WebcamSource
from deskos.config.settings import load_settings
from deskos.context.context_engine import RuleBasedContextEngine
from deskos.decision.decision_engine import DecisionEngine
from deskos.events.event_engine import EventEngine
from deskos.knowledge.habit_store import InferredHabitStore
from deskos.knowledge.history_store import SQLiteHistoryStore
from deskos.perception.object_detector import ObjectDetector
from deskos.perception.pipeline import PerceptionPipeline
from deskos.reasoning.rule_based_reasoner import RuleBasedReasoner
from deskos.services.notification_service import NotificationService
from deskos.services.service_registry import ServiceRegistry
from deskos.services.timer_service import TimerService
from deskos.ui.widget_manager import WidgetManager
from deskos.ui.widgets.floating_widget import FloatingWidget

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("deskos")


def build_app():
    """Constructs every layer and returns a callable `tick()` for one loop
    iteration, plus the camera to manage its lifecycle.
    """
    settings = load_settings()

    camera = WebcamSource(settings.camera)
    perception = PerceptionPipeline(
        detectors=[ObjectDetector(settings.perception.model_path, settings.perception.confidence_threshold)]
    )
    event_engine = EventEngine(settings.event_engine)
    context_engine = RuleBasedContextEngine(settings.context_engine)
    history_store = SQLiteHistoryStore(settings.storage.habits_db_path)
    habit_store = InferredHabitStore(history_store)
    reasoner = RuleBasedReasoner()
    decision_engine = DecisionEngine(settings.decision_engine, history_store)

    widget_manager = WidgetManager(FloatingWidget(settings.storage.data_dir / "widget_position.json"), settings.ui)
    services = ServiceRegistry(
        [TimerService(), NotificationService(widget_manager, history_store)],
        history_store,
    )

    def tick() -> None:
        frame = camera.read_frame()
        if frame is None:
            return
        detections = perception.process(frame)
        events = event_engine.process(detections)
        context = context_engine.update(events)
        if context.is_transition:
            # Only genuine state changes are history. Logging every tick would
            # make a "session" one tick long and habit learning meaningless.
            history_store.record_context_transition(context)
        suggestions = reasoner.reason(context, habit_store)
        actions = decision_engine.decide(suggestions)
        services.dispatch(actions)

    return camera, tick, settings


def main() -> None:
    camera, tick, settings = build_app()
    with camera:
        logger.info("DeskOS running. Ctrl+C to stop.")
        try:
            while True:
                tick()
                time.sleep(settings.perception.detection_interval_sec)
        except KeyboardInterrupt:
            logger.info("Shutting down.")


if __name__ == "__main__":
    main()
