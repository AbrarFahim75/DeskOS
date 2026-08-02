# DeskOS

An open-source AI desktop companion that understands *what you're doing*
(coding, studying, on a break, away) instead of just recognizing objects —
and quietly helps only when it's confident it's useful. It never
interrupts, never repeats itself, and prefers silence over a bad guess.

This is an early, evolving MVP. It currently ships as a Python desktop
app you run locally — no cloud, no account, nothing leaves your machine.

## Why a desktop app (not a web app)

DeskOS needs constant, low-latency access to your webcam and to draw a
tiny always-on-top widget over whatever else you're doing — both are
native desktop capabilities a browser can't do well or at all without
extra installs (camera permissions, a packaged server, a browser tab you
have to keep open). A plain Python desktop app is also the fastest path
to "download and run" for a non-technical user: one launcher script, no
Node.js, no separate frontend/backend to keep in sync. As DeskOS grows,
the floating widget can be upgraded to a more polished toolkit (see
Roadmap) without changing this fundamental shape.

---

## Quick Start (beginner-friendly)

**You need:** a Windows, macOS, or Linux computer with a webcam, and
Python 3.10+ installed ([python.org/downloads](https://python.org/downloads) —
on Windows, tick "Add Python to PATH" during install).

1. Download and extract this ZIP anywhere (e.g. your Desktop).
2. Open the extracted `DeskOS` folder.
3. **Windows:** double-click `launch.bat`.
   **macOS/Linux:** open a terminal in this folder and run `./launch.sh`
   (first time only: `chmod +x launch.sh` to make it runnable).
4. The first run installs everything automatically (~1 minute). A
   terminal window will show `DeskOS Assistant running.` — and a small,
   transparent, round bubble will appear in the corner of your screen.

Click the bubble to expand it into a small chat panel, type a message and
press Enter. Click the "–" in the panel to collapse it back to just the
bubble. Drag the bubble (or the panel's header) anywhere; it remembers
where you put it next time.

To stop DeskOS: close the terminal window, or press `Ctrl+C` inside it.

## Daily Usage

- Just leave `launch.bat` / `launch.sh` running in the background while
  you work (minimize the terminal window — you don't need to watch it).
- The bubble stays visible at all times, but stays small and out of the
  way until you click it.
- It will not sound, pop up dialogs, or steal focus. Voice commands are
  coming next; for now, typing in the expanded panel is the way to talk
  to it.
- To fully exit, close the terminal window running DeskOS.

## Full context-aware mode (camera + YOLO)

The one-click launcher now starts the lightweight chat bubble
(`deskos.assistant_app`), which needs no webcam. The original webcam/YOLO
context-detection mode described elsewhere in this README is still
available and unchanged — run `python -m deskos.main` instead (see
Commands below) if you also want DeskOS to watch your activity and show
contextual suggestions. Grant camera permission if your OS asks in that
mode.

## Troubleshooting

- **"python is not recognized" (Windows):** reinstall Python and check
  "Add Python to PATH", then re-run `launch.bat`.
- **Camera doesn't open / black window:** another app (Zoom, Teams) may
  be using the webcam — close it and restart DeskOS. Also check your OS's
  camera privacy settings allow Python/Terminal to use the camera.
- **`pip install` fails on `ultralytics`/`opencv-python`:** make sure
  you're on Python 3.10–3.12 (not 3.13, some ML packages lag behind);
  on Windows, installing the latest
  [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
  resolves most install errors.
- **Nothing ever appears on screen:** expected in the current MVP —
  Suggestions only fire above a high confidence threshold, and DeskOS
  needs a little time watching a state (e.g. ~30 seconds of coding
  signals) before it commits to a Context. This is intentional, not a bug.
- **Delete all learned data / start fresh:** delete the `data/` folder's
  contents (keeps `data/README.md`); DeskOS recreates everything it needs.

## Commands (manual / advanced)

Windows (PowerShell or cmd):
```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m deskos.assistant_app
```

macOS/Linux:
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m deskos.assistant_app
```

Swap `deskos.assistant_app` for `deskos.main` to run the full webcam/YOLO
context-aware mode instead. `python -m deskos.demo_widget` still previews
the older transient suggestion toast on its own.

Run tests: `pytest deskos/tests`

## Architecture

See `docs/ARCHITECTURE.md` for the full layer-by-layer design (Camera →
Perception → Events → Context → Knowledge → Reasoning → Decision →
Services → UI) and how to extend each layer.

## Roadmap / Currently Placeholder

Now implemented: real YOLO detection, full History→Habit aggregation,
habit-aware Reasoning (learns from 👍/👎 feedback), feedback buttons on
the transient suggestion widget (👍/👎/✖/⏰, with Remind Later re-showing
later), a fade in/out animated widget with mood accents and remembered
position, and — new — a persistent transparent chat bubble
(`deskos.assistant_app`) with click-to-expand/collapse and a typed chat
panel.

Still placeholder:

- Voice input (e.g. "play my favorite song") — typed chat only for now.
- More Services: Spotify, YouTube, browser awareness, calendar.
- A proper OS-native overlay instead of the current Tkinter widgets.
- Additional Context states beyond the MVP four (Thinking, Reading).
- Packaging as a true installable app (e.g. PyInstaller `.exe`) instead
  of running from source via the launcher scripts.

## License

Open source — see `LICENSE`.
