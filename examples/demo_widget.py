"""Manual widget demo - summons the floating widget directly, bypassing
camera/detection, so you can see and test it without waiting on real
context inference. Not part of the production pipeline; a dev/demo tool.

Run: python examples/demo_widget.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Allow running this file directly (`python examples/demo_x.py`) without
# having installed DeskOS first: put the repository root on the import path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import time

from deskos.config.settings import load_settings
from deskos.core import WidgetMood
from deskos.ui.widget_manager import WidgetManager
from deskos.ui.widgets.ambient_bubble import AmbientBubble


def main() -> None:
    settings = load_settings()
    widget_manager = WidgetManager(
        AmbientBubble(settings.storage.data_dir / "bubble_position.json"), settings.ui
    )

    demo_messages = [
        ("\u2615 Break?", WidgetMood.POSITIVE),
        ("\U0001F3B5 Focus music?", WidgetMood.POSITIVE),
        ("\u26A0 Away a while", WidgetMood.IMPORTANT),
    ]
    for message, mood in demo_messages:
        print(f"Showing: {message} ({mood.name})")
        widget_manager.show(message, mood=mood, duration_sec=6.0)
        time.sleep(8)  # let it fully show, hold, and fade before the next one

    print("Demo done. Ctrl+C to exit if a background window lingers.")
    time.sleep(2)


if __name__ == "__main__":
    main()
