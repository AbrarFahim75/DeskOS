"""Shared, immutable data contracts passed between DeskOS layers.

These types have no behavior beyond simple derived properties. Keeping them
dependency-free is what lets any layer be swapped (e.g. YOLO -> a different
detector, rule-based Context Engine -> an ML model) without touching its
neighbors.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


# --------------------------------------------------------------------------
# Camera -> Perception
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Frame:
    """A single raw camera frame."""
    image: Any  # np.ndarray, kept as Any so core has no cv2/numpy dependency
    timestamp: float = field(default_factory=time.time)


# --------------------------------------------------------------------------
# Perception -> Event Engine
# --------------------------------------------------------------------------

class DetectionType(Enum):
    """What kind of thing perception observed. Extend as new detectors land."""
    OBJECT = auto()
    POSE = auto()
    HAND = auto()
    FACE = auto()
    OCR_TEXT = auto()


@dataclass(frozen=True)
class Detection:
    """A single observation from the Perception layer for one frame.

    `label` is detector-specific (e.g. "coffee_cup", "keyboard", "empty_chair").
    `confidence` is 0.0-1.0. Perception makes NO judgment about what this means.
    """
    type: DetectionType
    label: str
    confidence: float
    timestamp: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)


# --------------------------------------------------------------------------
# Event Engine -> Context Engine
# --------------------------------------------------------------------------

class EventType(Enum):
    """A meaningful, debounced occurrence — never raw per-frame noise."""
    OBJECT_APPEARED = auto()
    OBJECT_DISAPPEARED = auto()
    USER_PRESENT = auto()
    USER_ABSENT = auto()
    ACTIVITY_STARTED = auto()
    ACTIVITY_STOPPED = auto()


@dataclass(frozen=True)
class Event:
    """A debounced, confirmed occurrence derived from many Detections.

    Example: 300 consecutive "coffee_cup" detections collapse into ONE
    OBJECT_APPEARED event with label="coffee_cup".
    """
    type: EventType
    label: str
    confidence: float
    timestamp: float = field(default_factory=time.time)


# --------------------------------------------------------------------------
# Context Engine -> Knowledge / Reasoning / Decision
# --------------------------------------------------------------------------

class ContextState(Enum):
    """User state. MVP supports the first four; rest are future extensions."""
    CODING = auto()
    STUDYING = auto()
    BREAK = auto()
    AWAY = auto()
    THINKING = auto()   # future
    READING = auto()    # future
    UNKNOWN = auto()


@dataclass(frozen=True)
class ContextSnapshot:
    """The Context Engine's current belief about what the user is doing.

    Rich by design: downstream layers (Knowledge, Reasoning, Decision, UI)
    should rarely need to recompute anything about "what just happened" —
    it should already be here.
    """
    state: ContextState                       # current activity
    confidence: float
    timestamp: float = field(default_factory=time.time)
    duration_in_state: float = 0.0            # seconds spent in `state` so far
    triggering_events: tuple[Event, ...] = field(default_factory=tuple)
    previous_context: "ContextSnapshot | None" = None
    metadata: dict = field(default_factory=dict)


# --------------------------------------------------------------------------
# Reasoning / Decision -> Services / UI
# --------------------------------------------------------------------------

class SuggestionType(Enum):
    """What kind of nudge Reasoning is proposing. Extend as Services grow."""
    TAKE_BREAK = auto()
    RESUME_FOCUS = auto()
    PAUSE_TIMER = auto()
    RESUME_TIMER = auto()
    PLAY_FOCUS_MUSIC = auto()


class UserValue(Enum):
    """Reasoning's own estimate of how valuable a Suggestion is likely to
    be to the user — distinct from `confidence` (how sure we are the
    context read is correct). Decision may weigh both.
    """
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()


class WidgetMood(Enum):
    """Subtle visual register for a shown widget — never changes layout or
    behavior, only tone (color/weight). Kept to three so the vocabulary
    stays calm and easy to reason about.
    """
    NEUTRAL = auto()    # ambient, routine (e.g. resume timer)
    POSITIVE = auto()   # affirming (e.g. break/music suggestions)
    IMPORTANT = auto()  # rare, higher-stakes (e.g. away for a long time)


@dataclass(frozen=True)
class Suggestion:
    """A candidate nudge, not yet approved to run. The Decision Engine
    decides whether this becomes an Action.
    """
    type: SuggestionType
    context: ContextSnapshot
    confidence: float
    estimated_value: UserValue = UserValue.MEDIUM
    mood: WidgetMood = WidgetMood.NEUTRAL
    reason: str = ""
    expires_at: float | None = None


class FeedbackType(Enum):
    """Explicit, voluntary user response to a shown Suggestion.

    Distinct signals, never conflated:
    - DISMISSED: user closed it without judging it (NOT negative signal).
    - NOT_HELPFUL: user explicitly said this suggestion type isn't useful.
    - HELPFUL: explicit positive signal.
    - REMIND_LATER: defer, not a judgment on usefulness.
    - No response at all is NOT represented here — absence of feedback
      must never be recorded as if it were NOT_HELPFUL.
    """
    HELPFUL = auto()
    NOT_HELPFUL = auto()
    DISMISSED = auto()
    REMIND_LATER = auto()


@dataclass(frozen=True)
class SuggestionFeedback:
    """A single explicit feedback event tied to a shown Suggestion."""
    suggestion_type: SuggestionType
    feedback: FeedbackType
    timestamp: float = field(default_factory=time.time)


class ActionType(Enum):
    """A concrete, executable action a Service knows how to perform."""
    SHOW_WIDGET = auto()
    PAUSE_TIMER = auto()
    RESUME_TIMER = auto()
    PLAY_MUSIC = auto()
    STOP_MUSIC = auto()


@dataclass(frozen=True)
class Action:
    """An approved instruction for a Service to execute. Produced only by
    the Decision Engine — Services never invent their own actions.

    `approval_reason` is internal-only (debugging/explainability, e.g.
    "high confidence", "cooldown expired", "high estimated value") — never
    shown to the user.
    """
    type: ActionType
    payload: dict = field(default_factory=dict)
    approval_reason: str = ""
    timestamp: float = field(default_factory=time.time)


class ExecutionStatus(Enum):
    """Outcome of a Service actually executing an Action. Internal-only —
    used for debugging, reliability, analytics, and future adaptive
    reasoning, never shown to the user.
    """
    SUCCESS = auto()
    FAILED = auto()
    SKIPPED = auto()
    RETRY_SUGGESTED = auto()


@dataclass(frozen=True)
class ExecutionResult:
    """What actually happened when a Service executed an Action. Recorded
    into History regardless of outcome so DeskOS can learn from real-world
    reliability, not just approved intent.
    """
    action: Action
    service_name: str
    status: ExecutionStatus
    duration_sec: float
    error_message: str | None = None
    timestamp: float = field(default_factory=time.time)
