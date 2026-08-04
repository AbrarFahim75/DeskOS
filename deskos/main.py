"""Backwards-compatible entry point.

The camera pipeline and the assistant bubble now run together in one
process (`deskos.app`). This module remains so that `python -m deskos.main`
keeps working; it simply delegates.
"""
from __future__ import annotations

from deskos.app import main

if __name__ == "__main__":
    main()
