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

DeskOS currently has two, which will be unified in a future milestone:

| Command | What it runs | Dependencies |
|---|---|---|
| `python -m deskos.assistant_app` | Chat bubble only (the default launcher) | base install |
| `python -m deskos.main` | Full camera + YOLO context pipeline | `pip install -e ".[vision]"` |

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

See [REVIEW.md](REVIEW.md) for the full assessment. The two items that
constrain near-term work:

1. **Two competing Tk threading models.** `ChatBubble` owns a `Tk` root on
   the main thread; `FloatingWidget` owns a second one on a background
   thread. They cannot run in the same process, which is why the two entry
   points above are still separate.
2. **`NotificationService` depends on the concrete `WidgetManager`** rather
   than the `WidgetRenderer` abstraction, violating the downstream rule
   stated above.
