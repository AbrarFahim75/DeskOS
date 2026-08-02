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
   terminal window will show `DeskOS running.` — that's it working.
5. Grant camera permission if your OS asks.

DeskOS is now watching your context and will show a small message in the
corner of your screen only when it's genuinely confident there's
something worth flagging.

To stop DeskOS: close the terminal window, or press `Ctrl+C` inside it.

## Daily Usage

- Just leave `launch.bat` / `launch.sh` running in the background while
  you work (minimize the terminal window — you don't need to watch it).
- You'll occasionally see a small, quiet widget appear in the corner —
  that's DeskOS. Drag it anywhere; it remembers where you put it next time.
- It will not sound, pop up dialogs, or steal focus. If nothing appears,
  that's by design — DeskOS prefers silence over a bad suggestion.
- To fully exit, close the terminal window running DeskOS.

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
python -m deskos.main
```

macOS/Linux:
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m deskos.main
```

Run tests: `pytest deskos/tests`

## Architecture

See `docs/ARCHITECTURE.md` for the full layer-by-layer design (Camera →
Perception → Events → Context → Knowledge → Reasoning → Decision →
Services → UI) and how to extend each layer.

## Roadmap / Currently Placeholder

Now implemented: real YOLO detection, full History→Habit aggregation,
habit-aware Reasoning (learns from 👍/👎 feedback), feedback buttons on
the widget (👍/👎/✖/⏰, with Remind Later re-showing later), and a
fade in/out animated widget with mood accents and remembered position.

Still placeholder:

- More Services: Spotify, YouTube, browser awareness, calendar.
- A proper OS-native overlay instead of the current Tkinter widget.
- Additional Context states beyond the MVP four (Thinking, Reading).
- Packaging as a true installable app (e.g. PyInstaller `.exe`) instead
  of running from source via the launcher scripts.

## License

Open source — see `LICENSE`.
