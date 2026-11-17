"""Piper offline neural TTS provider (optional local fallback)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Optional

from scenecraft.tts import BaseTTS
from scenecraft.narration import get_audio_duration


class PiperTTS(BaseTTS):
    """Piper neural text-to-speech system for fast, local offline synthesis."""

    def is_available(self) -> bool:
        return shutil.which("piper") is not None

    def generate(
        self,
        text: str,
        output_path: Path,
        voice: Optional[str] = None,
        speed: float = 1.0,
    ) -> float:
        output_path = Path(output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        piper_bin = shutil.which("piper") or "piper"

        cmd = [piper_bin, "--output_file", str(output_path)]
        if voice:
            cmd.extend(["--model", voice])

        res = subprocess.run(cmd, input=text.encode("utf-8"), capture_output=True)
        if res.returncode == 0 and output_path.is_file():
            return get_audio_duration(output_path)
        raise RuntimeError(f"Piper TTS synthesis failed: {res.stderr.decode('utf-8', errors='ignore')}")
