"""Kokoro-82M neural TTS engine via Kokoro-ONNX (fast, offline, Apache 2.0)."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import List, Optional, Tuple

from scenecraft.config import get_config
from scenecraft.narration import get_audio_duration
from scenecraft.tts import BaseTTS


KOKORO_STANDARD_VOICES = [
    # American Female
    "af_heart", "af_alloy", "af_aoede", "af_bella", "af_jessica",
    "af_kore", "af_nicole", "af_nova", "af_river", "af_sarah", "af_sky",
    # American Male
    "am_adam", "am_echo", "am_eric", "am_fenrir", "am_liam",
    "am_michael", "am_onyx", "am_puck", "am_santa",
    # British Female
    "bf_alice", "bf_emma", "bf_isabella", "bf_lily",
    # British Male
    "bm_daniel", "bm_fable", "bm_george", "bm_lewis",
]


class KokoroTTS(BaseTTS):
    """Local offline neural speech synthesizer powered by Kokoro-82M ONNX."""

    def __init__(
        self,
        model_path: Optional[Path | str] = None,
        voices_path: Optional[Path | str] = None,
    ):
        cfg = get_config()
        self.models_dir = cfg.models_dir / "kokoro"
        self.default_model_name = cfg.kokoro_model or "kokoro-v1.0.int8.onnx"
        self.default_voice = cfg.kokoro_voice or "af_heart"

        self._custom_model_path = Path(model_path) if model_path else None
        self._custom_voices_path = Path(voices_path) if voices_path else None

    def get_paths(self) -> Tuple[Optional[Path], Optional[Path]]:
        """Return paths to model weights and voices bin file if found."""
        if self._custom_model_path and self._custom_model_path.is_file():
            model = self._custom_model_path
        else:
            candidates = [
                self.models_dir / self.default_model_name,
                self.models_dir / "kokoro-v1.0.int8.onnx",
                self.models_dir / "kokoro-v1.0.onnx",
                self.models_dir / "kokoro-v0.19.onnx",
            ]
            model = next((p for p in candidates if p.is_file()), None)

        if self._custom_voices_path and self._custom_voices_path.is_file():
            voices = self._custom_voices_path
        else:
            candidates = [
                self.models_dir / "voices-v1.0.bin",
                self.models_dir / "voices.bin",
                self.models_dir / "voices.json",
            ]
            voices = next((p for p in candidates if p.is_file()), None)

        return model, voices

    def is_package_installed(self) -> bool:
        """Check if kokoro-onnx package is installed."""
        try:
            import kokoro_onnx  # noqa: F401
            return True
        except ImportError:
            return False

    def is_available(self) -> bool:
        """Return True if package is installed and model weights exist on disk."""
        if not self.is_package_installed():
            return False
        model, voices = self.get_paths()
        return model is not None and voices is not None

    def list_voices(self) -> List[str]:
        """Return list of known Kokoro voice identifiers."""
        _, voices_path = self.get_paths()
        if voices_path and self.is_package_installed():
            try:
                import kokoro_onnx
                # kokoro-onnx exposes get_voices() or similar if instantiated
                return KOKORO_STANDARD_VOICES
            except Exception:
                pass
        return KOKORO_STANDARD_VOICES

    def generate(
        self,
        text: str,
        output_path: Path,
        voice: Optional[str] = None,
        speed: float = 1.0,
    ) -> float:
        """Synthesize speech using Kokoro-ONNX and write to output_path."""
        if not self.is_package_installed():
            raise RuntimeError(
                "Kokoro TTS package not installed. Run: pip install \"scenecraft[kokoro]\""
            )

        model_path, voices_path = self.get_paths()
        if not model_path or not voices_path:
            raise RuntimeError(
                f"Kokoro model files not found in {self.models_dir}. "
                "Download them via: scenecraft setup --tts kokoro"
            )

        output_path = Path(output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        chosen_voice = voice or self.default_voice

        import soundfile as sf
        from kokoro_onnx import Kokoro

        kokoro = Kokoro(str(model_path), str(voices_path))
        # kokoro.create returns (samples, sample_rate)
        # Determine language prefix from voice (e.g. af/am -> en-us, bf/bm -> en-gb)
        lang = "en-gb" if chosen_voice.startswith("b") else "en-us"
        samples, sample_rate = kokoro.create(
            text=text,
            voice=chosen_voice,
            speed=speed,
            lang=lang,
        )

        sf.write(str(output_path), samples, sample_rate)
        if not output_path.is_file() or output_path.stat().st_size == 0:
            raise RuntimeError(f"Kokoro TTS produced an empty file: {output_path}")

        return get_audio_duration(output_path)
