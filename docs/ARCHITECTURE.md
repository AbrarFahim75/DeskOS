# DeskOS Architecture

Pipeline: Camera -> Perception -> Event Engine -> Context Engine -> Knowledge
-> Reasoning -> Decision Engine -> Services -> UI.

Each layer is a package under `deskos/` with an `interfaces.py` (ABC
contracts) and one or more implementations. Layers depend only on `core`
(shared dataclasses) and `config` (typed settings) plus the layer directly
upstream of them — never downstream, never sideways.

## Running

```
pip install -r requirements.txt
python -m deskos.main
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
