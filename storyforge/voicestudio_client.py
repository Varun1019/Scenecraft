"""VoiceStudio API client for StoryForge narration and speech generation.

Connects to local VoiceStudio backend running on port 3900 (OpenAI-compatible and native endpoints).
Supports:
- Local TTS with GPU acceleration (OmniVoice, KittenTTS, etc.)
- Voice cloning and custom designed profiles
- Direct WAV/MP3 export
"""

from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, Any, List, Optional


DEFAULT_VOICESTUDIO_URL = os.environ.get("VOICESTUDIO_BASE_URL", "http://127.0.0.1:3900")
PERMANENT_NARRATOR_CONFIG = Path(__file__).resolve().parent.parent / "references/voice/permanent_narrator/narrator_config.json"
CANDIDATE_NARRATOR_CONFIG = Path(__file__).resolve().parent.parent / "references/voice/candidates/rooftop_survivor/candidate_profile_config.json"


def get_permanent_narrator_config() -> Dict[str, Any]:
    """Load locked permanent narrator configuration."""
    if PERMANENT_NARRATOR_CONFIG.exists():
        try:
            with open(PERMANENT_NARRATOR_CONFIG, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "narrator_name": "StoryForge Permanent Cinematic Narrator (The Documentarian)",
        "voice_id": "b77c1cca",
        "engine": "omnivoice",
        "default_speed": 0.88,
        "seed": 42101,
        "tone": "Low American Baritone — calm, mature, authoritative, investigative",
        "approved_date": "2026-11-09",
        "locked": True,
    }


def get_candidate_narrator_config() -> Dict[str, Any]:
    """Load candidate narrator configuration if present."""
    if CANDIDATE_NARRATOR_CONFIG.exists():
        try:
            with open(CANDIDATE_NARRATOR_CONFIG, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def get_scene_delivery_params(
    emotion: Optional[str] = None,
    tension_level: Optional[int] = None,
    base_speed: Optional[float] = None,
    delivery_style: Optional[str] = None,
) -> Dict[str, Any]:
    """Calculate speed multiplier and expressive instructions based on scene emotion and tension.
    
    Rules:
    - Slightly faster during escalation (PANIC, ACTION, tension >= 8)
    - Slower during reveals (SHOCK, REVEAL, CLIMAX, tension >= 9)
    - Natural conversational delivery elsewhere
    """
    cfg = get_permanent_narrator_config()
    base_spd = float(base_speed if base_speed is not None else cfg.get("default_speed", 0.88))

    emo = (emotion or "").upper()
    if isinstance(tension_level, str):
        tension_map = {"low": 3, "medium": 5, "high": 7, "extreme": 9}
        lvl = tension_map.get(tension_level.lower(), 5)
    elif tension_level is not None:
        try:
            lvl = int(tension_level)
        except (ValueError, TypeError):
            lvl = 5
    else:
        lvl = 5

    style_instruction_prefix = ""
    if delivery_style:
        style_instruction_prefix = f"[{delivery_style.title()} Delivery] "

    if emo in ["SHOCK", "REVEAL", "DISCOVERY", "CLIMAX"]:
        return {
            "speed": round(max(0.75, base_spd - 0.04), 2),
            "instructions": f"{style_instruction_prefix}Deliberate, slow, heavy pauses, gravitas, chilling revelation",
        }
    elif emo in ["PANIC", "ACTION", "CHASE"] or lvl >= 8:
        return {
            "speed": round(min(1.05, base_spd + 0.07), 2),
            "instructions": f"{style_instruction_prefix}Urgent, hurried pace, rapid delivery, building intense suspense",
        }
    elif emo in ["DREAD", "SUSPENSE"]:
        return {
            "speed": base_spd,
            "instructions": f"{style_instruction_prefix}Quiet intensity, investigative, measured suspense",
        }
    else:
        return {
            "speed": base_spd,
            "instructions": f"{style_instruction_prefix}Calm, authoritative documentary narration, natural conversational pacing",
        }


def get_audio_duration(file_path: Path) -> float:
    """Return duration of audio file in seconds using ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(file_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(res.stdout.strip())


class VoiceStudioClient:
    """Client for local VoiceStudio speech synthesis service."""

    def __init__(self, base_url: str = DEFAULT_VOICESTUDIO_URL):
        self.base_url = base_url.rstrip("/")

    def is_available(self, timeout: float = 2.0) -> bool:
        """Check if VoiceStudio backend is responsive."""
        try:
            req = urllib.request.Request(f"{self.base_url}/health", method="GET")
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.status == 200
        except Exception:
            return False

    def get_health(self, timeout: float = 3.0) -> Dict[str, Any]:
        """Fetch system health, GPU device, and version info."""
        req = urllib.request.Request(f"{self.base_url}/health", method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def list_profiles(self, timeout: float = 3.0) -> List[Dict[str, Any]]:
        """Fetch custom and demo voice profiles."""
        req = urllib.request.Request(f"{self.base_url}/profiles", method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def list_voices(self, timeout: float = 3.0) -> List[Dict[str, Any]]:
        """Fetch list of all supported voices from OpenAI-compatible endpoint."""
        req = urllib.request.Request(f"{self.base_url}/v1/audio/voices", method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data.get("voices", [])

    def list_tts_engines(self, timeout: float = 3.0) -> Dict[str, Any]:
        """Fetch available TTS backends."""
        req = urllib.request.Request(f"{self.base_url}/engines/tts", method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def generate_speech(
        self,
        text: str,
        output_path: Path | str,
        voice: str = "default",
        model: str = "tts-1",
        response_format: str = "wav",
        speed: float = 1.0,
        instructions: Optional[str] = None,
        seed: Optional[int] = None,
        timeout: float = 120.0,
    ) -> float:
        """Synthesize text to speech using VoiceStudio OpenAI-compatible endpoint.

        Args:
            text: Text to synthesize.
            output_path: Path where output audio file should be written.
            voice: Voice profile ID, preset voice name, or alias.
            model: Engine name ('omnivoice', 'kittentts', etc.).
            response_format: Format ('wav', 'mp3', 'opus', 'flac').
            speed: Speed multiplier (0.25 to 4.0).
            instructions: Optional style instruction.
            seed: Optional deterministic seed.
            timeout: Generation timeout in seconds.

        Returns:
            Duration of generated audio in seconds.
        """
        if voice in ["default", "permanent"]:
            cfg = get_permanent_narrator_config()
            voice = cfg.get("voice_id", "b77c1cca")
            if seed is None:
                seed = cfg.get("seed", 42101)
            if speed == 1.0:
                speed = float(cfg.get("default_speed", 0.88))
        elif voice in ["candidate", "rooftop_survivor", "rooftop"]:
            cfg = get_candidate_narrator_config()
            voice = cfg.get("profile_id", "6f7af622")
            if speed == 1.0:
                speed = float(cfg.get("default_speed", 0.88))

        payload: Dict[str, Any] = {
            "model": model,
            "input": text,
            "voice": voice,
            "response_format": response_format,
            "speed": speed,
        }
        if instructions:
            payload["instructions"] = instructions
        if seed is not None:
            payload["seed"] = seed

        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/v1/audio/speech",
            data=req_data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                with open(out_path, "wb") as f:
                    f.write(response.read())
        except urllib.error.HTTPError as err:
            err_body = err.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"VoiceStudio generation failed (HTTP {err.code}): {err_body}") from err

        return get_audio_duration(out_path)


if __name__ == "__main__":
    client = VoiceStudioClient()
    if not client.is_available():
        print(f"VoiceStudio server is not running on {client.base_url}.")
        sys.exit(1)

    health = client.get_health()
    print(f"VoiceStudio connected: Device={health.get('device')}, Version={health.get('version')}")

    profiles = client.list_profiles()
    print(f"Profiles ({len(profiles)}): {[p.get('name') + ' (' + p.get('id') + ')' for p in profiles]}")

    test_out = Path("/tmp/voicestudio_test_run.wav")
    duration = client.generate_speech(
        text="Voice Studio test generation complete.",
        output_path=test_out,
        voice="demo0001",
    )
    print(f"Test synthesis succeeded: {test_out} ({duration:.2f}s)")
