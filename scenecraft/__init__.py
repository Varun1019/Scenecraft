"""Scenecraft - Local CLI automation tool for stickman story shorts."""

import sys

# Ensure UTF-8 output even in environments with legacy codepages (e.g. Windows cp1252)
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

__version__ = "1.0.0"

from scenecraft.voicestudio_client import VoiceStudioClient

__all__ = ["VoiceStudioClient", "__version__"]

