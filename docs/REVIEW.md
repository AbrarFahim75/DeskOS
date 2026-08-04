# DeskOS - Engineering Review

Status of this document: living. Findings are checked off as milestones
land. Last updated at Milestone 5.

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

### 8. `OBJECT_APPEARED` is re-emitted as a heartbeat

Once confirmed, a label re-emits `OBJECT_APPEARED` every
`event_debounce_sec`. The name is wrong for what it does: it is a
liveness signal, not a new appearance. The Context Engine currently
depends on it to keep labels from expiring, so renaming it means changing
both layers together. Low priority, but it will confuse the next reader.

---

## Resolved in Milestone 5 (one honest widget)

- [x] **Removed the chat panel.** It replied with a canned placeholder
      string, dressing a non-feature as a feature, and framed DeskOS as a
      chatbot - the one thing the README says it is not. It can return when
      there is something real behind it.
- [x] **Merged two widgets into one.** A persistent bubble plus a separate
      suggestion toast meant two surfaces could be on screen at once,
      breaking "one widget at a time". The bubble is now the renderer: a
      quiet dot at rest that expands into a suggestion card and collapses
      back, so the principle holds structurally rather than by convention.
      A test caught a stacking bug during development, where a second
      suggestion built a card on top of the first instead of replacing it.
- [x] **Right-click to quit.** Previously the only way to stop DeskOS was
      Ctrl+C in a terminal, followed by Windows asking "Terminate batch
      job (Y/N)?". A companion you cannot politely dismiss is not calm.
- [x] **TimerService no longer reports success for work it did not do.**
      It assumed a timer was always running, so the first PAUSE_TIMER
      "paused" nothing, returned SUCCESS, and burned a ten-minute cooldown.
      It now starts stopped and returns SKIPPED when already in the
      requested state.

Known limitation, recorded deliberately: Tk cannot do per-pixel alpha, so
the resting dot uses colour-key transparency and its edge is slightly
aliased. Genuine frosted glass needs a different toolkit.

---

## Resolved in Milestone 4 (context that matches reality)

Found by running DeskOS against a real webcam, not by any test.

- [x] **DeskOS was permanently stuck in AWAY.** Three faults compounded:
      `person` matched no rule, so `_infer()` returned UNKNOWN at 0.0
      confidence; that fell below `min_confidence`, so `update()` discarded
      it and re-reported the previous belief; and the previous belief was
      an AWAY(0.90) asserted on the very first tick before any event had
      been confirmed. The result was a trap: DeskOS believed the user was
      absent while detecting them in frame, and fired PAUSE_TIMER every ten
      minutes.
- [x] **The rules assumed the wrong camera.** They required
      `laptop + keyboard` for CODING, but a laptop webcam cannot see the
      laptop it is mounted on. Measured on a real desk: `person` 0.89,
      `laptop` 0.12, below a background couch at 0.21. CODING was
      unreachable on the most common hardware in existence.
- [x] **Presence is now the foundation.** New `PRESENT` state means "at the
      desk, activity unknown", which is what a face-facing camera can
      honestly claim. Objects *refine* presence into CODING/STUDYING/BREAK
      when a camera can actually see them, so an external camera pointed at
      the desk still gets the specific states.
- [x] **Startup is UNKNOWN, not AWAY.** A `warmup_sec` window lets DeskOS
      observe before claiming anything. Absence of evidence is no longer
      converted into evidence of absence at 0.90 confidence.
- [x] **AWAY requires sustained absence.** Leaning out of frame is not
      leaving; `away_timeout_sec` must elapse.
- [x] **A weak reading can never re-report a strong stale belief.**
      Sub-threshold confidence now degrades to UNKNOWN.
- [x] **Bare presence is gated on duration.** "You are at your desk" is not
      news; "you have been at your desk for 45 minutes" is. Suggestions
      require `long_session_sec` of unbroken presence.
- [x] **Debug view collapses repeated ticks.** The observer printed 62
      near-identical lines a minute, burying the events that mattered.
- [x] **Warm-up was measured from construction, not first observation.**
      Found on the second real run: the Context Engine is built before the
      camera opens and before YOLO lazily loads, which took about six
      seconds. Warm-up had nearly expired by the time the first frame
      arrived, so DeskOS declared AWAY and fired PAUSE_TIMER while looking
      straight at a person. The clock now starts on the first `update()`.
- [x] **Grace and warm-up retuned against measured behaviour.** A seated
      person drops out of YOLO's detections for 3-4 seconds at a time on a
      real laptop webcam, exceeding the 3s `absence_grace_sec` and resetting
      the streak, so confirmation took 16s instead of 6. Grace raised to 6s,
      and `warmup_sec` to 20s so it comfortably exceeds `confirm_after_sec`.
- [x] Added `examples/diagnose_vision.py`, which reports each vision stage
      separately (camera, frame content, raw YOLO output at 1% confidence,
      label mapping, threshold) so this class of problem is diagnosable in
      one run instead of by inference.

---

## Resolved in Milestone 3 (observability)

- [x] **Silence was unattributable.** DeskOS's defining behaviour is not
      acting, but a correct silence and a broken one looked identical. The
      Decision Engine now records a `SuppressionReason` for every rejected
      suggestion (`LOW_CONFIDENCE`, `IN_COOLDOWN`, `LOW_USER_VALUE`,
      `NO_ACTION_MAPPING`), the mirror image of the existing
      `approval_reason`.
- [x] **Added a `PipelineObserver` seam.** `decide()` keeps its exact
      contract; a new `evaluate()` returns approvals *and* rejections with
      reasons, and `decide()` is defined in terms of it so the two can
      never disagree. With no observer attached the pipeline behaves
      identically, so diagnostics are never in the hot path.
- [x] **Terminal debug view.** `deskos.app --debug` prints one compact,
      greppable line per tick showing detections, inferred context with
      confidence, and what the Decision Engine did, including why it stayed
      quiet. Idle ticks are hidden unless `--debug-verbose` is passed.
      `examples/demo_pipeline.py` uses the same view, so the reasoning can
      be watched without a webcam or the vision extra.

---

## Resolved in Milestone 2 (unified UI)

- [x] **Two competing Tk roots.** `ChatBubble` and `FloatingWidget` each
      created their own `Tk()` root on different threads, so they could not
      run together. A new `UIHost` owns the single root and event loop on
      the main thread; both widgets now `attach()` to it instead of
      creating one. Verified end-to-end: bubble and suggestion widget in
      one process, one root, one UI thread.
- [x] **Background thread touching Tk.** The perception loop runs on a
      worker thread and never calls a widget directly. It acts only through
      Services, and `WidgetManager` marshals every render onto the UI
      thread via `UIHost.post`.
- [x] **`NotificationService` depended on a concrete class.** It now depends
      on a new `WidgetPresenter` contract; `WidgetManager` implements it.
      Services no longer import any concrete UI class.
- [x] **Two entry points.** `deskos.app` runs the bubble and, when the
      vision extra is installed, the context pipeline in one process.
      `deskos.main` and `deskos.assistant_app` remain as thin shims. Vision
      is detected at runtime, so the app still runs as a bubble when
      `ultralytics`/`opencv` or a camera are absent.

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
| 2 | Unify the UI thread and entry point (issues 5-6) - **done** |
| 3 | Observable pipeline: see why DeskOS chose silence - **done** |
| 4 | Context that matches real hardware - **done** |
| 5+ | Voice, real timer service, integrations |
