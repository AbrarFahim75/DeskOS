"""Events package: converts continuous Detections into debounced Events."""
from deskos.events.interfaces import EventSource
from deskos.events.event_engine import EventEngine

__all__ = ["EventSource", "EventEngine"]
