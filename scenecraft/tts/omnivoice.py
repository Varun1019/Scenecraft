"""OmniVoice (VoiceStudio) local HTTP TTS client implementation."""

from __future__ import annotations

import urllib.request
import json
from pathlib import Path
from typing import Optional

from scenecraft.config import get_config
from scenecraft.tts import BaseTTS
from scenecraft.voicestudio_client import VoiceStudioClient


class OmniVoiceTTS(BaseTTS):
    """VoiceStudio / OmniVoice local daemon client running on configured port (default 3900)."""

    def __init__(self, base_url: Optional[str] = None):
        cfg = get_config()
        self.base_url = (base_url or cfg.tts_base_url).rstrip("/")
        self.client = VoiceStudioClient(base_url=self.base_url)

    def is_available(self) -> bool:
        """Check if local VoiceStudio / OmniVoice daemon is responding."""
        try:
            req = urllib.request.Request(f"{self.base_url}/health", headers={"User-Agent": "Scenecraft"})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                return resp.status in (200, 204)
        except Exception:
            return False

    def generate(
        self,
        text: str,
        output_path: Path,
        voice: Optional[str] = None,
        speed: float = 1.0,
    ) -> float:
        cfg = get_config()
        voice_id = voice or cfg.voice_id
        return self.client.generate_speech(
            text=text,
            output_path=output_path,
            voice=voice_id,
            speed=speed,
        )
