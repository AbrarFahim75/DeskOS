"""Pipeline observability contracts.

DeskOS's defining behaviour is *not acting*, which makes it hard to tell a
correct silence ("nothing was worth saying") from a broken one ("context
detection is stuck"). This package lets a diagnostic observer watch each
tick without changing what the pipeline does: with no observer attached,
nothing here runs and behaviour is identical.

The contract is deliberately one-directional. An observer receives facts
and may print, log, or count them. It cannot influence a decision - that
would make diagnostics part of the product's behaviour, which is exactly
what we are trying to avoid.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto

from deskos.core import (
    ContextSnapshot,
    Detection,
    Event,
    Suggestion,
    SuggestionType,
)


class SuppressionReason(Enum):
    """Why the Decision Engine declined to act on a suggestion.

    The mirror image of an Action's approval_reason: when DeskOS stays
    silent, this says which rule produced the silence.
    """

    LOW_CONFIDENCE = auto()      # below min_confidence_to_act
    IN_COOLDOWN = auto()         # shown too recently; never repeat, never interrupt
    LOW_USER_VALUE = auto()      # doing nothing costs the user nothing real
    NO_ACTION_MAPPING = auto()   # no ActionType wired for this SuggestionType yet


@dataclass(frozen=True)
class SuggestionOutcome:
    """What the Decision Engine did with one suggestion, and why."""

    suggestion_type: SuggestionType
    approved: bool
    reason: str  # approval_reason if approved, else the SuppressionReason name


@dataclass(frozen=True)
class PipelineTrace:
    """A single tick's journey through the pipeline, for diagnostics only.

    Every field is a plain snapshot of what a layer produced. Nothing here
    is read back by the pipeline; it exists purely to be shown.
    """

    detections: tuple[Detection, ...] = field(default_factory=tuple)
    events: tuple[Event, ...] = field(default_factory=tuple)
    context: ContextSnapshot | None = None
    suggestions: tuple[Suggestion, ...] = field(default_factory=tuple)
    outcomes: tuple[SuggestionOutcome, ...] = field(default_factory=tuple)

    @property
    def stayed_silent(self) -> bool:
        return not any(o.approved for o in self.outcomes)


class PipelineObserver(ABC):
    """Receives one PipelineTrace per tick. Implementations only report."""

    @abstractmethod
    def on_tick(self, trace: PipelineTrace) -> None:
        raise NotImplementedError
