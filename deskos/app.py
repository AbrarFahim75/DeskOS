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
from deskos.observability import PipelineObserver, PipelineTrace
from deskos.reasoning.rule_based_reasoner import RuleBasedReasoner
from deskos.services.notification_service import NotificationService
from deskos.services.service_registry import ServiceRegistry
from deskos.services.timer_service import TimerService
from deskos.ui.ui_host import UIHost
from deskos.ui.widget_manager import WidgetManager
from deskos.ui.widgets.ambient_bubble import AmbientBubble

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("deskos")


class PerceptionLoop:
    """Runs Camera -> ... -> Services on a background thread.

    Nothing here touches Tk. Effects on the UI happen only through the
    Services it dispatches to, which post onto the UI thread themselves.
    """

    def __init__(
        self,
        settings: Settings,
        services: ServiceRegistry,
        observer: PipelineObserver | None = None,
    ) -> None:
        self._settings = settings
        self._services = services
        self._observer = observer
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
        reasoner = RuleBasedReasoner(settings.context_engine.long_session_sec)
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

                    if self._observer is None:
                        actions = decision.decide(suggestions)
                    else:
                        evaluated = decision.evaluate(suggestions)
                        actions = [a for a, _ in evaluated if a is not None]
                        self._observer.on_tick(
                            PipelineTrace(
                                detections=tuple(detections),
                                events=tuple(events),
                                context=context,
                                suggestions=tuple(suggestions),
                                outcomes=tuple(o for _, o in evaluated),
                            )
                        )

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


def build_app(
    settings: Settings | None = None,
    observer: PipelineObserver | None = None,
) -> tuple[UIHost, PerceptionLoop | None]:
    """Assemble the whole application. Returns the UI host and, if vision is
    available, the perception loop (not yet started).

    An optional `observer` receives a PipelineTrace each tick for
    diagnostics. When None (the default), the pipeline runs identically and
    emits nothing.
    """
    settings = settings or load_settings()

    ui_host = UIHost()
    history = SQLiteHistoryStore(settings.storage.habits_db_path)

    # One widget, two states: a quiet dot that becomes a suggestion card.
    # This is what makes "only one widget visible at a time" structural
    # rather than a rule someone has to remember.
    bubble = AmbientBubble(
        position_file=settings.storage.data_dir / "bubble_position.json",
        on_quit=ui_host.stop,
    )
    widget_manager = WidgetManager(bubble, settings.ui, ui_host=ui_host)

    ui_host.on_ready(bubble.attach)

    services = ServiceRegistry(
        [TimerService(), NotificationService(widget_manager, history)],
        history,
    )

    loop: PerceptionLoop | None = None
    if _vision_available():
        loop = PerceptionLoop(settings, services, observer=observer)
    else:
        logger.info(
            "Vision extra not installed; running as assistant only. "
            "Install with: pip install -e \".[vision]\""
        )

    return ui_host, loop


def main(argv: list[str] | None = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(
        prog="deskos",
        description="A calm, context-aware desktop companion.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print the pipeline's decisions each tick, including why it "
        "chose to stay silent. Diagnostic only; does not change behaviour.",
    )
    parser.add_argument(
        "--debug-verbose",
        action="store_true",
        help="Like --debug but also prints idle ticks (nothing detected).",
    )
    args = parser.parse_args(argv)

    observer = None
    if args.debug or args.debug_verbose:
        from deskos.observability.terminal_observer import TerminalObserver

        observer = TerminalObserver(verbose=args.debug_verbose)
        logger.info("Debug pipeline view enabled.")

    ui_host, loop = build_app(observer=observer)

    if not ui_host.available:
        # No display at all (e.g. headless). Nothing to show; exit cleanly.
        logger.info("No display available; DeskOS has nothing to render.")
        return

    if loop is not None:
        loop.start()

    logger.info("DeskOS running. Right-click the bubble to quit, or press Ctrl+C.")
    try:
        ui_host.run()  # blocks on the Tk event loop until the window closes
    except KeyboardInterrupt:
        logger.info("Shutting down.")
    finally:
        if loop is not None:
            loop.stop()


if __name__ == "__main__":
    main()
