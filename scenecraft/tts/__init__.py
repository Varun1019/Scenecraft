"""Pluggable TTS interfaces for Scenecraft."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from scenecraft.config import get_config


class BaseTTS(ABC):
    """Abstract interface for all Scenecraft narration providers."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if this TTS engine is available and ready."""
        pass

    @abstractmethod
    def generate(
        self,
        text: str,
        output_path: Path,
        voice: Optional[str] = None,
        speed: float = 1.0,
    ) -> float:
        """Synthesize speech from text and write to output_path. Return duration in seconds."""
        pass


def get_tts_engine(engine_name: Optional[str] = None) -> BaseTTS:
    """Return configured TTS engine, falling back to edge-tts if primary is unavailable."""
    from scenecraft.tts.omnivoice import OmniVoiceTTS
    from scenecraft.tts.edge_tts import EdgeTTS

    cfg = get_config()
    target = (engine_name or cfg.tts_engine or "omnivoice").lower()

    if target in ("omnivoice", "voicestudio"):
        omni = OmniVoiceTTS()
        if omni.is_available():
            return omni
        # Fallback to edge-tts
        edge = EdgeTTS()
        if edge.is_available():
            return edge
        return omni

    if target == "edge_tts" or target == "edge":
        return EdgeTTS()

    if target == "piper":
        try:
            from scenecraft.tts.piper import PiperTTS
            piper = PiperTTS()
            if piper.is_available():
                return piper
        except ImportError:
            pass
        return EdgeTTS()

    return EdgeTTS()
