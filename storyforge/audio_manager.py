"""Audio manager with strict license verification for YouTube safe use."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, Optional


class LicenseError(Exception):
    """Raised when an audio asset is unverified or lacks YouTube commercial rights."""


class AudioManager:
    """Manages audio assets and verifies licenses prior to inclusion in the video pipeline."""

    def __init__(self, licenses_path: Optional[Path] = None):
        if licenses_path is None:
            # Default to bundled licenses.json
            base_dir = Path(__file__).resolve().parent.parent
            licenses_path = base_dir / "assets" / "licenses.json"
        
        self.licenses_path = Path(licenses_path)
        self.licenses = self._load_licenses()
        self._imported_sfx_index: Optional[Dict[str, Path]] = None

    def clear_sfx_cache(self) -> None:
        """Clear cached in-memory index of imported SFX assets."""
        self._imported_sfx_index = None

    def _build_imported_sfx_index(self) -> Dict[str, Path]:
        """Build in-memory index of imported SFX files keyed by stem."""
        base_dir = self.licenses_path.parent.parent
        imported_sfx_dir = (
            base_dir
            / "assets"
            / "imported"
            / "stickman_animation"
            / "skills"
            / "vox-doc-sound"
            / "sfx"
        )
        index: Dict[str, Path] = {}
        if not imported_sfx_dir.is_dir():
            return index

        # Sort paths for deterministic resolution when duplicate stems exist
        for path in sorted(imported_sfx_dir.rglob("*")):
            if path.is_file():
                stem = path.stem
                if stem not in index:
                    index[stem] = path.resolve()
        return index

    def _get_imported_sfx_index(self) -> Dict[str, Path]:
        """Lazy-load and return cached in-memory index of imported SFX assets."""
        if self._imported_sfx_index is None:
            self._imported_sfx_index = self._build_imported_sfx_index()
        return self._imported_sfx_index

    def _load_licenses(self) -> Dict[str, Any]:
        if not self.licenses_path.is_file():
            raise FileNotFoundError(f"Licenses file missing at: {self.licenses_path}")
        with open(self.licenses_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("verified_assets", {})

    def verify_asset(self, filename: str) -> Dict[str, Any]:
        """Verify an audio asset against the license manifest.
        
        Rejects unverified or unsafe assets immediately.
        """
        if filename not in self.licenses:
            raise LicenseError(
                f"REJECTED: Audio asset '{filename}' is NOT in verified licenses manifest."
            )

        asset_info = self.licenses[filename]
        if asset_info.get("status") != "VERIFIED":
            raise LicenseError(
                f"REJECTED: Audio asset '{filename}' status is '{asset_info.get('status')}', not VERIFIED."
            )

        if not asset_info.get("youtube_monetization_safe", False):
            raise LicenseError(
                f"REJECTED: Audio asset '{filename}' is not cleared for YouTube monetization."
            )

        if not asset_info.get("commercial_use_permitted", False):
            raise LicenseError(
                f"REJECTED: Audio asset '{filename}' does not permit commercial use."
            )

        return asset_info

    def get_asset_path(self, filename: str) -> Path:
        """Verify asset and return its absolute filesystem path."""
        asset_info = self.verify_asset(filename)
        rel_path = asset_info["path"]
        base_dir = self.licenses_path.parent.parent
        abs_path = (base_dir / rel_path).resolve()
        if not abs_path.is_file():
            raise FileNotFoundError(f"Verified asset file missing on disk: {abs_path}")
        return abs_path

    def get_default_bgm(self) -> Path:
        """Return the default verified ambient suspense background track."""
        try:
            return self.get_asset_path("apocalypse_ambient_drone.mp3")
        except (LicenseError, FileNotFoundError):
            return self.get_asset_path("apocalypse_ambient_drone.wav")

    def get_sfx(self, sfx_name: str) -> Path:
        """Resolve SFX name (with or without extension) and return verified path."""
        # Common semantic alias mapping to verified CC0 / Public Domain assets
        SFX_ALIASES = {
            "sfx_wind_ambience": "b2_desert_wind",
            "sfx_wind": "b2_desert_wind",
            "sfx_phone_buzz": "sfx_phone_vibrate",
            "sfx_static_burst": "sfx_radio_static",
            "sfx_suspense_drone": "sfx_tension_drone",
            "sfx_alarm_drone": "sfx_alarm",
            "sfx_heartbeat": "sfx_sub_rumble",
            "sfx_metallic_thud": "sfx_knock_heavy",
            "sfx_car_impact": "sfx_door_slam",
            "sfx_page_turn": "sfx_tape_click",
            "sfx_security_beep": "b4_bell_tone_h",
            "sfx_traffic_silence": "sfx_tension_drone",
        }
        stem = Path(sfx_name).stem
        if stem in SFX_ALIASES:
            sfx_name = SFX_ALIASES[stem]

        # 1. Check existing verified manifest
        candidates = [sfx_name, f"{sfx_name}.wav", f"{sfx_name}.mp3"]
        for cand in candidates:
            if cand in self.licenses:
                return self.get_asset_path(cand)

        # 2. Check imported commercial-cleared sound library via cached in-memory index
        imported_index = self._get_imported_sfx_index()
        for cand in [sfx_name, f"{sfx_name}.mp3", f"{sfx_name}.wav"]:
            clean_stem = Path(cand).stem
            if clean_stem in imported_index:
                resolved_path = imported_index[clean_stem]
                if resolved_path.is_file():
                    return resolved_path

        # Fallback to standard check
        if not sfx_name.endswith(".wav"):
            filename = f"{sfx_name}.wav"
        else:
            filename = sfx_name
        return self.get_asset_path(filename)
