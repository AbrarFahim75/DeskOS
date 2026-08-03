"""DeskOS application assembly: one process, one UI thread, one loop.

This is the single entry point that replaces the old split between
`assistant_app` (bubble only) and `main` (camera only). It wires every
layer together and runs them in one process:

- The UI (chat bubble + suggestion widget) owns the main thread via UIHost.
- The perception loop, if vision is available, runs on a worker thread and
  posts nothing to the UI directly - it acts only through Services, which
  marshal onto the UI thread via the WidgetManager/UIHost pair.

Vision is optional at runtime. If `ultralytics`/`opencv` or a camera are
missing, DeskOS still runs as a calm assistant bubble; it just does not
observe context. This keeps first-run install light (see the `vision`
extra in pyproject.toml) without a second entry point.
"""
from __future__ import annotations

import logging
import threading

from deskos.config.settings import Settings, load_settings
from deskos.context.context_engine import RuleBasedContextEngine
from deskos.decision.decision_engine import DecisionEngine
from deskos.events.event_engine import EventEngine
from deskos.knowledge.habit_store import InferredHabitStore
from deskos.knowledge.history_store import SQLiteHistoryStore
from deskos.reasoning.rule_based_reasoner import RuleBasedReasoner
from deskos.services.notification_service import NotificationService
from deskos.services.service_registry import ServiceRegistry
from deskos.services.timer_service import TimerService
from deskos.ui.ui_host import UIHost
from deskos.ui.widget_manager import WidgetManager
from deskos.ui.widgets.chat_bubble import ChatBubble
from deskos.ui.widgets.floating_widget import FloatingWidget

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("deskos")

_PLACEHOLDER_REPLY = "I can't do much yet, but I'm listening. Voice commands are coming soon!"


def _handle_message(text: str) -> str:
    logger.info("User message: %s", text)
    return _PLACEHOLDER_REPLY


class PerceptionLoop:
    """Runs Camera -> ... -> Services on a background thread.

    Nothing here touches Tk. Effects on the UI happen only through the
    Services it dispatches to, which post onto the UI thread themselves.
    """

    def __init__(self, settings: Settings, services: ServiceRegistry) -> None:
        self._settings = settings
        self._services = services
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name="perception", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        # Imported lazily so a machine without the vision extra never pays
        # for these heavy modules just to run the bubble.
        from deskos.camera.webcam_source import WebcamSource
        from deskos.perception.object_detector import ObjectDetector
        from deskos.perception.pipeline import PerceptionPipeline

        settings = self._settings
        camera = WebcamSource(settings.camera)
        perception = PerceptionPipeline(
            detectors=[
                ObjectDetector(
                    settings.perception.model_path,
                    settings.perception.confidence_threshold,
                )
            ]
        )
        event_engine = EventEngine(settings.event_engine)
        context_engine = RuleBasedContextEngine(settings.context_engine)
        history = self._services.history
        habit_store = InferredHabitStore(history)
        reasoner = RuleBasedReasoner()
        decision = DecisionEngine(settings.decision_engine, history)

        try:
            camera.start()
        except Exception:
            logger.warning("Camera unavailable; perception loop will not run", exc_info=True)
            return

        logger.info("Perception loop started")
        try:
            while not self._stop.is_set():
                frame = camera.read_frame()
                if frame is not None:
                    detections = perception.process(frame)
                    events = event_engine.process(detections)
                    context = context_engine.update(events)
                    if context.is_transition:
                        history.record_context_transition(context)
                    suggestions = reasoner.reason(context, habit_store)
                    actions = decision.decide(suggestions)
                    self._services.dispatch(actions)
                self._stop.wait(settings.perception.detection_interval_sec)
        finally:
            camera.stop()
            logger.info("Perception loop stopped")


def _vision_available() -> bool:
    """True only if the optional vision stack can be imported."""
    try:
        import cv2  # noqa: F401
        import ultralytics  # noqa: F401
    except ImportError:
        return False
    return True


def build_app(settings: Settings | None = None) -> tuple[UIHost, PerceptionLoop | None]:
    """Assemble the whole application. Returns the UI host and, if vision is
    available, the perception loop (not yet started).
    """
    settings = settings or load_settings()

    ui_host = UIHost()
    history = SQLiteHistoryStore(settings.storage.habits_db_path)

    floating = FloatingWidget(settings.storage.data_dir / "widget_position.json")
    widget_manager = WidgetManager(floating, settings.ui, ui_host=ui_host)
    bubble = ChatBubble(
        position_file=settings.storage.data_dir / "chat_bubble_position.json",
        on_message=_handle_message,
    )

    # Widgets are built once the root exists, on the UI thread.
    def build_ui(root) -> None:
        floating.attach(root)
        bubble.attach(root)

    ui_host.on_ready(build_ui)

    services = ServiceRegistry(
        [TimerService(), NotificationService(widget_manager, history)],
        history,
    )

    loop: PerceptionLoop | None = None
    if _vision_available():
        loop = PerceptionLoop(settings, services)
    else:
        logger.info(
            "Vision extra not installed; running as assistant only. "
            "Install with: pip install -e \".[vision]\""
        )

    return ui_host, loop


def main() -> None:
    ui_host, loop = build_app()

    if not ui_host.available:
        # No display at all (e.g. headless). Nothing to show; exit cleanly.
        logger.info("No display available; DeskOS has nothing to render.")
        return

    if loop is not None:
        loop.start()

    logger.info("DeskOS running. Close the bubble or press Ctrl+C to stop.")
    try:
        ui_host.run()  # blocks on the Tk event loop until the window closes
    except KeyboardInterrupt:
        logger.info("Shutting down.")
    finally:
        if loop is not None:
            loop.stop()


if __name__ == "__main__":
    main()
