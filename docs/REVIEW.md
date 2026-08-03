# DeskOS - Engineering Review

Status of this document: living. Findings are checked off as milestones
land. Last updated at Milestone 1.

---

## Summary

The layered architecture is sound and should be preserved. The problems
found in review were **correctness bugs inside layers**, one unresolved
**threading decision**, and **repository hygiene** - not the structure
itself.

## What is working well

- `core/types.py` has no DeskOS dependencies, uses frozen dataclasses, and
  draws distinctions that protect the product philosophy - notably
  `FeedbackType` separating `DISMISSED` from `NOT_HELPFUL`, so silence is
  never recorded as rejection.
- Dependency direction is genuinely acyclic. Every layer exposes ABCs in
  `interfaces.py` with implementations kept separate.
- `InMemoryHistoryStore` alongside the SQLite one is real dependency
  inversion, not decoration.
- Heavy dependencies (`ultralytics`, `cv2`, `tkinter`) are imported lazily,
  so a missing optional package degrades instead of crashing.
- `ServiceRegistry` catches service exceptions, so one bad integration can
  never kill the main loop.
- Comments explain *why* rather than *what*.

---

## Open issues

### 5. Two competing Tk threading models - **architectural**

`ChatBubble` creates a `Tk` root and blocks the calling thread.
`FloatingWidget` creates a *second* `Tk` root on a daemon background
thread. Two roots in one process is unsafe, and Tk off the main thread is
unsupported. Currently hidden because the two live in separate entry
points - but the product needs bubble and suggestions together.

Fix: one `Tk` root on the main thread, perception moved to a worker thread
posting into the existing command queue. Resolve before building more UI.

### 6. `NotificationService` depends on a concrete class

It imports `WidgetManager` directly rather than the `WidgetRenderer`
abstraction, a downstream dependency that violates the rule stated in
`ARCHITECTURE.md`.

### 8. `OBJECT_APPEARED` is re-emitted as a heartbeat

Once confirmed, a label re-emits `OBJECT_APPEARED` every
`event_debounce_sec`. The name is wrong for what it does: it is a
liveness signal, not a new appearance. The Context Engine currently
depends on it to keep labels from expiring, so renaming it means changing
both layers together. Low priority, but it will confuse the next reader.

---

## Resolved in Milestone 1 (correctness)

- [x] **Habit learning measured the tick rate.** `main.py` wrote a history
      row every tick. `ContextSnapshot` now carries `is_transition`, set
      only when the state genuinely changes, and only those are recorded.
      Measured before: 3,600 rows/hour and `average_session_duration`
      returning 1.00s for a one-hour session. After: 2 rows and 3600s.
- [x] **A dropped frame destroyed a confirmation streak.** The Event
      Engine now tolerates absences shorter than `absence_grace_sec`, so a
      detector flicker no longer resets progress.
- [x] **Confirmation took 30s while the config claimed 6.** Confirmation is
      now measured in wall-clock seconds (`confirm_after_sec`) rather than
      frame counts, so it no longer depends on the loop tick rate. Camera
      `fps` is documented as a capture hint only.
- [x] **Cooldown was spent before delivery.** `record_suggestion_shown`
      moved from `DecisionEngine` to `ServiceRegistry`, fired only on
      `SUCCESS`. Decision is now pure policy and performs no writes.
- [x] **Stale databases are rebuilt automatically.** `PRAGMA user_version`
      gates the schema; a pre-v2 database is dropped and recreated, since
      per-tick rows cannot be converted into real sessions.
- [x] Test suite grew from 5 tests to 28, covering the Event, Context,
      Decision, Knowledge and Services layers where all four bugs lived.

---

## Resolved in Milestone 0 (repository hygiene)

- [x] Removed `support.js`, `Canvas.dc.html`, `.thumbnail` - artifacts from
      an unrelated design tool, tracked in git.
- [x] Untracked `yolov8n.pt` (6.3 MB); `ultralytics` downloads it on demand.
- [x] Removed vestigial `data/`, which contradicted the configured
      `~/.deskos` runtime path.
- [x] Added `.gitattributes`. The repository was entirely CRLF with no
      normalization, which made `launch.sh` fail on macOS/Linux with
      `bad interpreter: bash^M` and caused 4,643-line whitespace diffs.
- [x] Added `pyproject.toml`: version, pinned floors, console scripts, and
      optional `vision` / `dev` dependency groups.
- [x] Split heavy dependencies out of the default install. Previously the
      launcher installed `ultralytics` (and therefore PyTorch, several GB)
      just to show a chat bubble, despite the README promising ~1 minute.
- [x] Moved `deskos/tests/` to `tests/` so tests no longer ship inside the
      installed package.
- [x] Moved `demo_*.py` to `examples/`.
- [x] Added `ruff` config and fixed all 31 reported lint issues.
- [x] Added GitHub Actions CI running lint + tests on Python 3.10-3.14.
- [x] Added `CONTRIBUTING.md`; updated `README.md` and `ARCHITECTURE.md` to
      match actual behaviour.

---

## Roadmap

| Milestone | Goal |
|---|---|
| 0 | Repository hygiene - **done** |
| 1 | Fix issues 1-4, each with a regression test - **done** |
| 2 | Unify the UI thread and entry point (issues 5-6) |
| 3 | Observable pipeline: see why DeskOS chose silence |
| 4+ | Voice, real timer service, integrations |
