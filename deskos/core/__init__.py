"""Core package: shared data contracts used across every DeskOS layer.

Nothing in `core` depends on any other DeskOS package. This is what keeps
Camera -> Perception -> Events -> Context -> Knowledge -> Reasoning ->
Decision -> Services -> UI acyclic.
"""
from deskos.core.types import (
    Action,
    ActionType,
    ContextSnapshot,
    ContextState,
    Detection,
    DetectionType,
    Event,
    EventType,
    ExecutionResult,
    ExecutionStatus,
    FeedbackType,
    Frame,
    Suggestion,
    SuggestionFeedback,
    SuggestionType,
    UserValue,
    WidgetMood,
)

__all__ = [
    "Frame",
    "Detection",
    "DetectionType",
    "Event",
    "EventType",
    "ContextState",
    "ContextSnapshot",
    "Suggestion",
    "SuggestionType",
    "UserValue",
    "WidgetMood",
    "FeedbackType",
    "SuggestionFeedback",
    "Action",
    "ActionType",
    "ExecutionStatus",
    "ExecutionResult",
]
