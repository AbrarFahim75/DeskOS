# DeskOS

An open-source AI desktop companion that understands *what you're doing*
(coding, studying, on a break, away) instead of just recognizing objects -
and quietly helps only when it's confident it's useful. It never
interrupts, never repeats itself, and prefers silence over a bad guess.

This is an early, evolving MVP. It runs entirely on your machine - no
cloud, no account, nothing leaves your computer.

---

## Quick Start

**You need:** Windows, macOS, or Linux with Python 3.10+
([python.org/downloads](https://python.org/downloads) - on Windows, tick
**"Add Python to PATH"** during install).

1. Download and extract this project anywhere (e.g. your Desktop).
2. Open the extracted `DeskOS` folder.
3. **Windows:** double-click `launch.bat`
   **macOS/Linux:** open a terminal in this folder and run `./launch.sh`
   (first time only: `chmod +x launch.sh`)
4. The first run sets everything up in a few seconds. A small,
   transparent bubble appears in the corner of your screen.

Click the bubble to expand it into a chat panel; type a message and press
Enter. Click **-** to collapse it back. Drag it anywhere - it remembers
where you put it.

**To stop DeskOS:** close the terminal window, or press `Ctrl+C` in it.

> **Linux note:** if you get `ModuleNotFoundError: No module named 'tkinter'`,
> install it with `sudo apt install python3-tk` (Debian/Ubuntu) or
> `sudo dnf install python3-tkinter` (Fedora). Tkinter ships with Python on
> Windows and macOS but is a separate package on most Linux distributions.

---

## Full context-aware mode (camera + YOLO)

The default launcher starts the lightweight assistant bubble only. The
camera-based context pipeline is **opt-in**, because it depends on
`ultralytics`, which installs PyTorch - several gigabytes.

```bash
# from the DeskOS folder, with the environment activated
pip install -e ".[vision]"
python -m deskos.main
```

This watches your webcam, infers whether you're coding / studying / on a
break / away, and shows an occasional small suggestion widget. Your camera
feed is processed locally and never stored or transmitted.

---

## Why a desktop app (not a web app)

DeskOS needs constant, low-latency webcam access and the ability to draw a
tiny always-on-top widget over whatever else you're doing. Both are native
desktop capabilities a browser can't do well without extra installs. A
plain Python desktop app is also the shortest path to "download and run"
for a non-technical user: one launcher, no Node.js, no separate
frontend/backend to keep in sync.

---

## Project structure

```
DeskOS/
├── deskos/            # the application package
│   ├── core/          # shared data contracts (depends on nothing)
│   ├── config/        # typed settings loaded from YAML
│   ├── camera/        # frame capture
│   ├── perception/    # object detection
│   ├── events/        # debouncing raw detections into real events
│   ├── context/       # inferring what the user is doing
│   ├── knowledge/     # history + learned habits
│   ├── reasoning/     # proposing suggestions
│   ├── decision/      # deciding whether to act at all
│   ├── services/      # timers, notifications, future integrations
│   └── ui/            # floating widget + chat bubble
├── tests/             # test suite
├── examples/          # developer demo scripts
├── docs/              # architecture and design review
├── launch.bat         # one-click launcher (Windows)
└── launch.sh          # one-click launcher (macOS/Linux)
```

Runtime data (history database, remembered widget position) is stored in
`~/.deskos` on your machine, never in this folder.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for how the layers fit
together, and [docs/REVIEW.md](docs/REVIEW.md) for the current engineering
assessment and known issues.

---

## Development

```bash
pip install -e ".[dev]"   # install with test + lint tools
pytest                    # run the test suite
ruff check .              # lint
ruff check . --fix        # auto-fix lint issues
```

Contributions welcome - see [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Status

DeskOS is pre-1.0 and under active development. The architecture is
stable; several layers are deliberately simple placeholders pending real
implementations. Known issues are tracked in
[docs/REVIEW.md](docs/REVIEW.md).

## License

MIT - see [LICENSE](LICENSE).
