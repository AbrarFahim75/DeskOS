"""Events package: converts continuous Detections into debounced Events."""
from deskos.events.event_engine import EventEngine
from deskos.events.interfaces import EventSource

__all__ = ["EventSource", "EventEngine"]
