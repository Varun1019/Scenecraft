"""ElevenLabs paid API speech provider for Scenecraft."""

from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path
from typing import List, Optional

from scenecraft.config import get_config
from scenecraft.narration import get_audio_duration
from scenecraft.tts import BaseTTS


DEFAULT_ELEVENLABS_VOICES = [
    "21m00Tcm4TlvDq8ikWAM",  # Rachel
    "AZnzlk1XvdvUeBnXmlld",  # Domi
    "EXAVITQu4vr4xnSDxMaL",  # Bella
    "ErXwobaYiN019PkySvjV",  # Antoni
    "MF3mGyEYCl7XYWbV9V6O",  # Elli
    "TxGEqnHWrfWFTfGW9XjX",  # Josh
    "VR6AewLTigWG4xSOukaG",  # Arnold
    "pNInz6obpgDQGcFmaJgB",  # Adam
    "yoZ06aMxZJJ28mfd3POQ",  # Sam
]


class ElevenLabsTTS(BaseTTS):
    """ElevenLabs Cloud TTS synthesis (requires ELEVENLABS_API_KEY)."""

    def __init__(self, api_key: Optional[str] = None):
        cfg = get_config()
        self.api_key = api_key or os.environ.get("ELEVENLABS_API_KEY")
        self.default_voice = cfg.elevenlabs_voice or "21m00Tcm4TlvDq8ikWAM"

    def is_available(self) -> bool:
        """Return True if an API key is configured in environment or .env."""
        key = self.api_key or os.environ.get("ELEVENLABS_API_KEY")
        return bool(key and key.strip())

    def list_voices(self) -> List[str]:
        return DEFAULT_ELEVENLABS_VOICES

    def generate(
        self,
        text: str,
        output_path: Path,
        voice: Optional[str] = None,
        speed: float = 1.0,
    ) -> float:
        """Call ElevenLabs API to synthesize speech."""
        api_key = self.api_key or os.environ.get("ELEVENLABS_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ElevenLabs API key missing. Set ELEVENLABS_API_KEY in your environment or .env file."
            )

        output_path = Path(output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        chosen_voice = voice or self.default_voice

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{chosen_voice}"
        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
            },
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "xi-api-key": api_key.strip(),
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
            raise RuntimeError(f"ElevenLabs synthesis failed: {e}") from e

        return get_audio_duration(output_path)
