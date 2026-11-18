"""OpenAI paid API speech provider for Scenecraft."""

from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path
from typing import List, Optional

from scenecraft.config import get_config
from scenecraft.narration import get_audio_duration
from scenecraft.tts import BaseTTS


DEFAULT_OPENAI_VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]


class OpenAITTS(BaseTTS):
    """OpenAI Cloud TTS synthesis (requires OPENAI_API_KEY)."""

    def __init__(self, api_key: Optional[str] = None):
        cfg = get_config()
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.default_voice = cfg.openai_voice or "alloy"

    def is_available(self) -> bool:
        """Return True if an API key is configured in environment or .env."""
        key = self.api_key or os.environ.get("OPENAI_API_KEY")
        return bool(key and key.strip())

    def list_voices(self) -> List[str]:
        return DEFAULT_OPENAI_VOICES

    def generate(
        self,
        text: str,
        output_path: Path,
        voice: Optional[str] = None,
        speed: float = 1.0,
    ) -> float:
        """Call OpenAI TTS API to synthesize speech."""
        api_key = self.api_key or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OpenAI API key missing. Set OPENAI_API_KEY in your environment or .env file."
            )

        output_path = Path(output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        chosen_voice = voice or self.default_voice

        url = "https://api.openai.com/v1/audio/speech"
        payload = {
            "model": "tts-1",
            "input": text,
            "voice": chosen_voice,
            "speed": max(0.25, min(4.0, speed)),
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key.strip()}",
                "User-Agent": "Scenecraft",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
                with open(output_path, "wb") as f:
                    f.write(data)
        except Exception as e:
            raise RuntimeError(f"OpenAI TTS synthesis failed: {e}") from e

        return get_audio_duration(output_path)
