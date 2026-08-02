"""DeskOS Assistant -- the lightweight, camera-free entry point.

Runs just the persistent chat bubble widget so a beginner can start DeskOS
with one click, without needing the webcam/YOLO context-detection pipeline
(that full experience is still available via `python -m deskos.main`).

Run: python -m deskos.assistant_app
"""
from __future__ import annotations

import logging

from deskos.config.settings import load_settings
from deskos.ui.widgets.chat_bubble import ChatBubble

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("deskos.assistant")

_PLACEHOLDER_REPLY = "I can't do much yet, but I'm listening. Voice commands are coming soon!"


def _handle_message(text: str) -> str:
    logger.info("User message: %s", text)
    return _PLACEHOLDER_REPLY


def main() -> None:
    settings = load_settings()
    position_file = settings.storage.data_dir / "chat_bubble_position.json"
    bubble = ChatBubble(position_file=position_file, on_message=_handle_message)

    logger.info("DeskOS Assistant running. Close the terminal or press Ctrl+C to stop.")
    try:
        bubble.run()
    except KeyboardInterrupt:
        logger.info("Shutting down.")


if __name__ == "__main__":
    main()
