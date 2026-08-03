# DeskOS - Engineering Review

Status of this document: living. Findings are checked off as milestones
land. Last updated at Milestone 0.

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

### 1. Habit learning measures the tick rate, not behaviour - **critical**

`main.py` calls `record_context_transition()` every tick regardless of
whether the state changed. Measured: 3,600 rows per hour spent in a single
unchanging state, ~86,400 rows/day, and `average_session_duration()`
returning `1.00s` for a one-hour session because consecutive rows are one
tick apart.

The entire Knowledge layer currently produces meaningless output while
appearing to work. Fix: record only on genuine state change.

### 2. A single dropped frame destroys a confirmation streak - **critical**

`EventEngine` deletes a label's streak the moment it is absent for one
frame. Measured: 29 consecutive `laptop` detections, one dropped frame,
streak reset to zero. YOLO flickers constantly on real webcam input, so
events may fire rarely or never - DeskOS goes silent because it is broken,
not because it judged silence correct.

Fix: decay the streak on a miss, or use an N-of-last-M rolling ratio.

### 3. Confirmation delay is 30s, not the documented 6s

`default_config.yaml` annotates `min_frames_to_confirm: 30` as "~6s at
5fps", but the main loop sleeps on `detection_interval_sec: 1.0` and reads
one frame per tick. Camera `fps` never affects loop rate. Two competing
time models exist; only one is real.

### 4. Cooldown is spent before the user sees anything

`DecisionEngine.decide()` writes `record_suggestion_shown()` and then
returns the Action. If the service later fails or returns `SKIPPED`, the
10-minute cooldown is burned on a suggestion never displayed. Decision is a
policy layer and should not perform writes; recording belongs in
`ServiceRegistry` on `SUCCESS`.

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

### 7. Test coverage is thin exactly where bugs were found

No tests for `EventEngine` debounce, `ContextEngine` rules,
`DecisionEngine` cooldown, or `HabitStore` aggregation - the four areas
where issues 1-4 live. The correlation is not a coincidence.

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
| 1 | Fix issues 1-4, each with a regression test |
| 2 | Unify the UI thread and entry point (issues 5-6) |
| 3 | Observable pipeline: see why DeskOS chose silence |
| 4+ | Voice, real timer service, integrations |
