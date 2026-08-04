"""Backwards-compatible entry point.

DeskOS used to have two separate apps. They are now one (`deskos.app`),
which runs the assistant bubble and, if the vision extra is installed, the
context pipeline in a single process. This module remains only so that
`python -m deskos.assistant_app` keeps working; it simply delegates.
"""
from __future__ import annotations

from deskos.app import main

if __name__ == "__main__":
    main()
