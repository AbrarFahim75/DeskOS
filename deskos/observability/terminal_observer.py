"""A PipelineObserver that prints each tick to the terminal.

Format is one compact, greppable line per tick, e.g.

    12:04:31  ctx=CODING(0.85)  det=laptop,keyboard  -> SILENT: RESUME_TIMER in_cooldown
    12:04:47  ctx=BREAK(0.90)   det=coffee_cup       -> SHOW: TAKE_BREAK (first occurrence)

By default it stays quiet on ticks where nothing happened (no detections,
no context, no suggestions), so a long idle stretch does not scroll a wall
of empty lines. Pass `verbose=True` to print every tick, including idle
ones, when you are specifically debugging why nothing is being detected.
"""
from __future__ import annotations

import sys
import time
from typing import TextIO

from deskos.observability import PipelineObserver, PipelineTrace


class TerminalObserver(PipelineObserver):
    def __init__(self, stream: TextIO | None = None, verbose: bool = False) -> None:
        self._stream = stream if stream is not None else sys.stderr
        self._verbose = verbose

    def on_tick(self, trace: PipelineTrace) -> None:
        if not self._verbose and self._is_idle(trace):
            return
        self._stream.write(self._format(trace) + "\n")
        self._stream.flush()

    @staticmethod
    def _is_idle(trace: PipelineTrace) -> bool:
        context_is_meaningful = trace.context is not None and trace.context.confidence > 0.0
        return not trace.detections and not trace.suggestions and not context_is_meaningful

    def _format(self, trace: PipelineTrace) -> str:
        stamp = time.strftime("%H:%M:%S")
        parts = [stamp, self._format_context(trace), self._format_detections(trace)]
        parts.append("->")
        parts.append(self._format_outcome(trace))
        return "  ".join(p for p in parts if p)

    @staticmethod
    def _format_context(trace: PipelineTrace) -> str:
        ctx = trace.context
        if ctx is None:
            return "ctx=?"
        return f"ctx={ctx.state.name}({ctx.confidence:.2f})"

    @staticmethod
    def _format_detections(trace: PipelineTrace) -> str:
        if not trace.detections:
            return "det=-"
        labels = ",".join(d.label for d in trace.detections)
        return f"det={labels}"

    @staticmethod
    def _format_outcome(trace: PipelineTrace) -> str:
        if not trace.outcomes:
            return "SILENT: nothing proposed"

        approved = [o for o in trace.outcomes if o.approved]
        if approved:
            shown = ", ".join(f"{o.suggestion_type.name} ({o.reason})" for o in approved)
            return f"SHOW: {shown}"

        # All rejected: name each suppression so a wrong silence is visible.
        reasons = ", ".join(
            f"{o.suggestion_type.name} {o.reason.lower()}" for o in trace.outcomes
        )
        return f"SILENT: {reasons}"
