"""Edge-TTS fallback speech engine (zero-setup, high-clarity neural speech)."""

from __future__ import annotations

import asyncio
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

from scenecraft.tts import BaseTTS
from scenecraft.narration import get_audio_duration


class EdgeTTS(BaseTTS):
    """Microsoft Edge Neural Speech synthesizer via edge-tts CLI or library."""

    DEFAULT_VOICE = "en-US-AndrewMultilingualNeural"

    def is_available(self) -> bool:
        """Check if edge-tts is available as package or CLI."""
        try:
            import edge_tts  # noqa: F401
            return True
        except ImportError:
            return shutil.which("edge-tts") is not None

    def generate(
        self,
        text: str,
        output_path: Path,
        voice: Optional[str] = None,
        speed: float = 1.0,
    ) -> float:
        output_path = Path(output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        chosen_voice = voice or self.DEFAULT_VOICE

        # Calculate rate string
        pct = int(round((speed - 1.0) * 100))
        rate_str = f"{pct:+d}%"

        # 1. Try python package directly
        try:
            import edge_tts

            async def _synthesize():
                communicate = edge_tts.Communicate(text, chosen_voice, rate=rate_str)
                await communicate.save(str(output_path))

            asyncio.run(_synthesize())
            if output_path.is_file() and output_path.stat().st_size > 1000:
                return get_audio_duration(output_path)
        except Exception:
            pass

        # 2. Try CLI command
        edge_bin = shutil.which("edge-tts") or "edge-tts"
        cmd = [
            edge_bin,
            "--voice", chosen_voice,
            "--rate", rate_str,
            "--text", text,
            "--write-media", str(output_path),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and output_path.is_file() and output_path.stat().st_size > 1000:
            return get_audio_duration(output_path)

        raise RuntimeError(f"Edge-TTS failed to generate audio: {res.stderr or res.stdout}")
