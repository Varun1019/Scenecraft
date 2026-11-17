"""Configuration management for Scenecraft."""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import platformdirs
    DEFAULT_CACHE_DIR = Path(platformdirs.user_cache_dir("scenecraft"))
    DEFAULT_DATA_DIR = Path(platformdirs.user_data_dir("scenecraft"))
except ImportError:
    DEFAULT_CACHE_DIR = Path.home() / ".cache" / "scenecraft"
    DEFAULT_DATA_DIR = Path.home() / ".local" / "share" / "scenecraft"

try:
    import yaml
except ImportError:
    yaml = None


@dataclass
class ScenecraftConfig:
    # TTS & Voice
    tts_engine: str = "omnivoice"  # "omnivoice", "edge_tts", "piper"
    tts_base_url: str = "http://127.0.0.1:3900"
    voice_id: str = "6f7af622"
    voice_speed: float = 0.90
    voice_style: str = "natural"

    # Video Encoding
    video_width: int = 1080
    video_height: int = 1920
    fps: int = 30
    encoder: str = "auto"  # "auto", "h264_nvenc", "libx264"
    crf: int = 19
    audio_duck_lufs: float = -14.0

    # Flow Extension & Bridge
    extension_port: int = 8795
    extension_host: str = "127.0.0.1"
    flow_auto_port: int = 8791

    # Storage & Cache
    cache_dir: Path = field(default_factory=lambda: DEFAULT_CACHE_DIR)
    models_dir: Path = field(default_factory=lambda: DEFAULT_CACHE_DIR / "models")
    output_dir: Path = field(default_factory=lambda: Path.cwd() / "output")
    temp_dir: Path = field(default_factory=lambda: Path(tempfile.gettempdir()))

    # Watermark Cleaner
    cleaner_model_name: str = "lama_fp32.onnx"
    cleaner_threads: int = 4

    @classmethod
    def load(cls, config_path: Optional[Path | str] = None) -> ScenecraftConfig:
        """Load configuration from config.yaml, environment, and defaults."""
        cfg_dict: Dict[str, Any] = {}

        # 1. Locate config.yaml
        possible_paths = [
            Path(config_path) if config_path else None,
            Path.cwd() / "config.yaml",
            Path.cwd() / "config.yml",
            DEFAULT_DATA_DIR / "config.yaml",
        ]

        found_path: Optional[Path] = None
        for p in possible_paths:
            if p and p.is_file():
                found_path = p
                break

        if found_path and yaml:
            try:
                with open(found_path, "r", encoding="utf-8") as f:
                    loaded = yaml.safe_load(f)
                    if isinstance(loaded, dict):
                        cfg_dict = loaded
            except Exception as e:
                print(f"[!] Warning: Failed to parse config file {found_path}: {e}")

        # 2. Environment overrides
        env_voice = os.environ.get("SCENECRAFT_VOICE_ID") or os.environ.get("VOICESTUDIO_VOICE_ID")
        if env_voice:
            cfg_dict["voice_id"] = env_voice

        env_tts = os.environ.get("SCENECRAFT_TTS_ENGINE")
        if env_tts:
            cfg_dict["tts_engine"] = env_tts

        env_vs_url = os.environ.get("VOICESTUDIO_BASE_URL") or os.environ.get("SCENECRAFT_TTS_BASE_URL")
        if env_vs_url:
            cfg_dict["tts_base_url"] = env_vs_url

        env_encoder = os.environ.get("SCENECRAFT_ENCODER")
        if env_encoder:
            cfg_dict["encoder"] = env_encoder

        # Convert paths if present in dict
        if "cache_dir" in cfg_dict:
            cfg_dict["cache_dir"] = Path(cfg_dict["cache_dir"])
        if "models_dir" in cfg_dict:
            cfg_dict["models_dir"] = Path(cfg_dict["models_dir"])
        if "output_dir" in cfg_dict:
            cfg_dict["output_dir"] = Path(cfg_dict["output_dir"])

        # Filter valid fields
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in cfg_dict.items() if k in valid_keys}
        return cls(**filtered)


_GLOBAL_CONFIG: Optional[ScenecraftConfig] = None


def get_config() -> ScenecraftConfig:
    global _GLOBAL_CONFIG
    if _GLOBAL_CONFIG is None:
        _GLOBAL_CONFIG = ScenecraftConfig.load()
    return _GLOBAL_CONFIG


def set_config(config: ScenecraftConfig) -> None:
    global _GLOBAL_CONFIG
    _GLOBAL_CONFIG = config
