# DeskOS Architecture

Pipeline: Camera -> Perception -> Event Engine -> Context Engine -> Knowledge
-> Reasoning -> Decision Engine -> Services -> UI.

Each layer is a package under `deskos/` with an `interfaces.py` (ABC
contracts) and one or more implementations. Layers depend only on `core`
(shared dataclasses) and `config` (typed settings) plus the layer directly
upstream of them - never downstream, never sideways.

`core` imports nothing from DeskOS. That is what keeps the graph acyclic
and lets any layer be swapped without touching its neighbours.

## Entry points

One unified process runs everything:

| Command | What it runs | Dependencies |
|---|---|---|
| `python -m deskos.app` | Assistant bubble, plus the context pipeline if the vision extra is installed | base; `[vision]` adds camera + YOLO |

`deskos.main` and `deskos.assistant_app` remain as thin shims that call
`deskos.app.main`, so older instructions keep working. Vision is detected
at runtime: without `ultralytics`/`opencv` or a camera, DeskOS runs as a
bubble and simply does not observe context.

The single Tk root lives in `deskos.ui.ui_host.UIHost` on the main thread.
The perception loop runs on a worker thread and never touches the UI
directly; it acts through Services, which marshal onto the UI thread.

## Running

```bash
pip install -e .            # base
pip install -e ".[vision]"  # add camera + YOLO
pip install -e ".[dev]"     # add pytest + ruff
```

## MVP scope

Context states: CODING, STUDYING, BREAK, AWAY. Everything else (THINKING,
READING, additional Services, learned habit mining, LLM-backed Reasoning)
is scaffolded as an interface + TODO, not implemented, per product
principle: prefer silence over bad suggestions, and prefer a small
robust MVP over a sprawling one.

## Extending

- New detector: implement `perception.interfaces.Detector`, add to the
  `PerceptionPipeline` detector list in `main.py`.
- New context state: add to `core.types.ContextState`, add a rule to
  `context.context_engine._LABEL_STATE_RULES`.
- New suggestion/action: add enum members to `core.types`, extend the
  mapping tables in `reasoning` and `decision`.
- New integration: implement `services.interfaces.Service`, register it
  in `main.py`'s `ServiceRegistry`.

## Known architectural debt

See [REVIEW.md](REVIEW.md) for the full assessment. The Tk threading and
Services-to-UI coupling issues were resolved in Milestone 2. One minor item
remains: `OBJECT_APPEARED` is re-emitted as a liveness heartbeat, which the
name does not convey.

## Observability

`deskos.observability` defines a one-directional diagnostic seam. A
`PipelineObserver` receives a `PipelineTrace` per tick and may print, log,
or count it, but can never influence a decision - that would make
diagnostics part of the product's behaviour.

The Decision Engine exposes `evaluate()`, returning each suggestion's
Action (or None) alongside a `SuggestionOutcome` explaining approval or
naming the `SuppressionReason`. `decide()` is defined as `evaluate()` with
rejections dropped, so the diagnostic and production paths cannot diverge.

```bash
python -m deskos.app --debug           # one line per tick, idle ticks hidden
python -m deskos.app --debug-verbose   # include idle ticks
python examples/demo_pipeline.py       # same view, no webcam needed
```
