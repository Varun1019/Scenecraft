"""Scenecraft Global and Workspace Configuration Settings.

Manages persistent preferences such as automatic thumbnail generation,
default creative universe (Wanderer vs Experimental), aspect ratios,
and narration profiles.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from scenecraft.config import get_config

SETTINGS_DIR = Path(os.environ.get("SCENECRAFT_HOME", Path.home() / ".scenecraft"))
SETTINGS_FILE = SETTINGS_DIR / "settings.json"

DEFAULT_SETTINGS: Dict[str, Any] = {
    "auto_thumbnail": True,
    "default_aspect_ratio": "9:16",
    "default_universe": "wanderer",
    "narrator_profile_id": get_config().voice_id,
    "narrator_speed": 0.90,
    "narrator_style": "natural",
    "flow_agent_beats_min": 25,
    "flow_agent_beats_max": 45,
    "auto_approve_credits": False,
    "style_preset": "dark_cinematic",
}


def get_settings_file_path(workspace_dir: Optional[Path] = None) -> Path:
    """Resolve active settings file path (workspace override takes precedence over home)."""
    if workspace_dir:
        ws_file = Path(workspace_dir).resolve() / ".scenecraft.json"
        if ws_file.is_file():
            return ws_file
    return SETTINGS_FILE


def load_settings(workspace_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Load settings merging defaults with persisted configuration."""
    settings = dict(DEFAULT_SETTINGS)
    target_file = get_settings_file_path(workspace_dir)

    if target_file.is_file():
        try:
            with open(target_file, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    settings.update(loaded)
        except Exception:
            pass
    return settings


def save_settings(new_settings: Dict[str, Any], workspace_dir: Optional[Path] = None) -> Path:
    """Save updated settings to disk."""
    target_file = get_settings_file_path(workspace_dir)
    target_file.parent.mkdir(parents=True, exist_ok=True)

    current = load_settings(workspace_dir)
    current.update(new_settings)

    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(current, f, indent=2)
    return target_file


def get_setting(key: str, default: Any = None, workspace_dir: Optional[Path] = None) -> Any:
    """Retrieve a single setting value."""
    settings = load_settings(workspace_dir)
    return settings.get(key, default if default is not None else DEFAULT_SETTINGS.get(key))


def set_setting(key: str, value: Any, workspace_dir: Optional[Path] = None) -> None:
    """Set a single setting value."""
    save_settings({key: value}, workspace_dir=workspace_dir)


def is_auto_thumbnail_enabled(workspace_dir: Optional[Path] = None) -> bool:
    """Check whether automatic Flow AI thumbnail generation is active in Scenecraft settings."""
    return bool(get_setting("auto_thumbnail", True, workspace_dir=workspace_dir))


def set_auto_thumbnail_enabled(enabled: bool = True, workspace_dir: Optional[Path] = None) -> None:
    """Enable or disable automatic Flow AI thumbnail generation."""
    set_setting("auto_thumbnail", bool(enabled), workspace_dir=workspace_dir)
