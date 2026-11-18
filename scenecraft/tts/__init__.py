"""Pluggable TTS interfaces and engine selection for Scenecraft."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from scenecraft.config import get_config

logger = logging.getLogger("scenecraft")


class BaseTTS(ABC):
    """Abstract interface for all Scenecraft narration providers."""

    engine_name: str = "base"

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

    def list_voices(self) -> List[str]:
        """Return available voices for this engine."""
        return []


class AutoFallbackTTS(BaseTTS):
    """Engine wrapper implementing auto priority selection with fallback on failure."""

    engine_name: str = "auto"

    def __init__(self):
        self.priority_engines: List[Tuple[str, BaseTTS, str]] = []
        self._initialize_chain()

    def _initialize_chain(self):
        from scenecraft.tts.omnivoice import OmniVoiceTTS
        from scenecraft.tts.kokoro import KokoroTTS
        from scenecraft.tts.edge_tts import EdgeTTS

        self.priority_engines = [
            ("omnivoice", OmniVoiceTTS(), "OmniVoice daemon active on port 3900"),
            ("kokoro", KokoroTTS(), "Kokoro-82M ONNX local neural model ready"),
            ("edge-tts", EdgeTTS(), "Edge-TTS zero-setup cloud fallback (requires internet)"),
        ]

    def resolve_best_engine(self) -> Tuple[str, BaseTTS, str]:
        """Pick the first ready engine in priority order: omnivoice -> kokoro -> edge-tts."""
        for name, engine, reason in self.priority_engines:
            if engine.is_available():
                return name, engine, reason
        # Fallback to edge-tts if none reported ready
        from scenecraft.tts.edge_tts import EdgeTTS
        return "edge-tts", EdgeTTS(), "Edge-TTS default fallback"

    def is_available(self) -> bool:
        _, engine, _ = self.resolve_best_engine()
        return engine.is_available()

    def generate(
        self,
        text: str,
        output_path: Path,
        voice: Optional[str] = None,
        speed: float = 1.0,
    ) -> float:
        """Synthesize with best available engine, falling back to next engine on failure."""
        name, active_engine, reason = self.resolve_best_engine()
        print(f"[*] Auto TTS: Selected '{name}' ({reason})")

        try:
            return active_engine.generate(text, output_path, voice=voice, speed=speed)
        except Exception as primary_err:
            print(f"[!] Warning: Primary engine '{name}' failed ({primary_err}). Attempting fallback...")
            # Try remaining engines
            for fallback_name, fallback_engine, fallback_reason in self.priority_engines:
                if fallback_name == name:
                    continue
                if fallback_engine.is_available():
                    try:
                        print(f"[*] Auto TTS Fallback: Attempting '{fallback_name}' ({fallback_reason})...")
                        dur = fallback_engine.generate(text, output_path, voice=voice, speed=speed)
                        print(f"[✔] Auto TTS Fallback succeeded with '{fallback_name}'.")
                        return dur
                    except Exception as err:
                        print(f"[!] Fallback '{fallback_name}' also failed: {err}")
            raise primary_err


def get_tts_engine(engine_name: Optional[str] = None) -> BaseTTS:
    """Return configured TTS engine instance."""
    cfg = get_config()
    target = (engine_name or cfg.tts_engine or "auto").lower().strip()

    if target in ("auto", "automatic"):
        return AutoFallbackTTS()

    if target in ("omnivoice", "voicestudio"):
        from scenecraft.tts.omnivoice import OmniVoiceTTS
        return OmniVoiceTTS()

    if target in ("kokoro", "kokoro-onnx"):
        from scenecraft.tts.kokoro import KokoroTTS
        return KokoroTTS()

    if target in ("edge-tts", "edge_tts", "edge"):
        from scenecraft.tts.edge_tts import EdgeTTS
        return EdgeTTS()

    if target == "piper":
        from scenecraft.tts.piper import PiperTTS
        return PiperTTS()

    if target in ("elevenlabs", "eleven_labs"):
        from scenecraft.tts.elevenlabs import ElevenLabsTTS
        return ElevenLabsTTS()

    if target == "openai":
        from scenecraft.tts.openai import OpenAITTS
        return OpenAITTS()

    raise ValueError(f"Unknown TTS engine: {target}")


from scenecraft.tts.edge_tts import EdgeTTS
from scenecraft.tts.elevenlabs import ElevenLabsTTS
from scenecraft.tts.kokoro import KokoroTTS
from scenecraft.tts.omnivoice import OmniVoiceTTS
from scenecraft.tts.openai import OpenAITTS
from scenecraft.tts.piper import PiperTTS

__all__ = [
    "BaseTTS",
    "AutoFallbackTTS",
    "OmniVoiceTTS",
    "KokoroTTS",
    "EdgeTTS",
    "PiperTTS",
    "ElevenLabsTTS",
    "OpenAITTS",
    "get_tts_engine",
]
