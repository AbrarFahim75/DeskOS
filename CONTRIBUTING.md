# Contributing to DeskOS

Thanks for your interest. DeskOS is a small, opinionated project — the
guidelines below exist to keep it that way.

## Setup

```bash
git clone https://github.com/datazenith-labs/DeskOS.git
cd DeskOS
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Verify:

```bash
pytest
ruff check .
```

Both must pass before you open a pull request. CI runs exactly these two
commands on Python 3.10, 3.11, and 3.12.

## Product principles

These are not negotiable, and a change that violates one will be declined
even if the code is good:

1. **Prefer silence.** Do not add a notification unless staying quiet would
   cost the user something real.
2. **Never repeat a suggestion.** Cooldowns and repetition suppression live
   in the Decision Engine and belong nowhere else.
3. **Learn only from explicit feedback.** Absence of a response is not a
   negative signal and must never be recorded as one.
4. **One widget at a time.** Never stack UI.

## Engineering guidelines

- Every layer keeps a single responsibility. If a change makes a layer
  reach across the pipeline, it probably belongs somewhere else.
- Depend on the `interfaces.py` abstraction, not the concrete class.
- `deskos/core` must never import from another DeskOS package.
- Use type hints on public functions and document public APIs.
- Comments should explain *why*, not *what*. The existing codebase does
  this well — match it.
- Keep functions small and names meaningful. Readability beats cleverness.

## Adding a dependency

Base dependencies are deliberately minimal so the default launch stays
fast. If a package is only needed for camera work, add it to the `vision`
extra in `pyproject.toml`, not to `dependencies`. Import heavy libraries
lazily inside functions so a missing optional dependency degrades
gracefully instead of crashing.

## Tests

New behaviour needs a test. Pay particular attention to the Event, Context,
and Decision layers — that is where regressions are least visible and most
damaging.

Tests that require a display must skip themselves cleanly when none is
available (see `tests/test_chat_bubble.py` for the pattern), so CI stays
green on headless runners.

## Commits and branches

- One branch per milestone or fix, merged into `main` via pull request.
- Write commit messages in the imperative mood: "Fix event streak reset",
  not "Fixed" or "Fixes".
- Keep unrelated changes in separate commits.
