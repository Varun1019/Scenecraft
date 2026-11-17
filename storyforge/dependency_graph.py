"""Lightweight Content Hash Caching & Dependency Graph Engine for StoryForge.

Uses cryptographic content fingerprints (SHA-256) instead of naive file existence.
Tracks dependencies between scenes, narration, subtitles, images, clips, and composition:
- Modifying scene 3 visual description only regenerates scene 3 image & clip.
- Modifying subtitles does not regenerate images or narration.
- Modifying BGM does not regenerate narration or visual clips.
- Modifying narration automatically cascades to dependent scene timing and subtitles.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, Optional, List


def compute_sha256(data: str | bytes) -> str:
    """Compute 16-character SHA-256 fingerprint."""
    h = hashlib.sha256()
    if isinstance(data, str):
        h.update(data.encode("utf-8"))
    else:
        h.update(data)
    return h.hexdigest()[:16]


def compute_file_sha256(path: Path) -> str:
    """Compute content fingerprint of a file on disk."""
    p = Path(path)
    if not p.is_file():
        return ""
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()[:16]


@dataclass
class SceneDependencyRecord:
    scene_idx: int
    narration_hash: str = ""
    visual_prompt_hash: str = ""
    image_hash: str = ""
    clip_hash: str = ""
    duration: float = 0.0
    image_path: str = ""
    clip_path: str = ""


class DependencyGraph:
    """Tracks project asset content fingerprints and determines surgical invalidations."""

    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir)
        self.state_file = self.project_dir / ".storyforge_deps.json"
        self.state: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.state_file.is_file():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "version": "2.0.0",
            "global": {},
            "scenes": {},
        }

    def save(self):
        """Persist graph state to project directory."""
        self.project_dir.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2)

    def compute_scene_narration_hash(self, scene: Dict[str, Any], voice: str, rate: str) -> str:
        content = f"{scene.get('narration', '')}|{scene.get('emotion', '')}|{voice}|{rate}"
        return compute_sha256(content)

    def is_narration_current(self, scene_idx: int, current_hash: str, audio_file: Path) -> bool:
        if not audio_file.is_file():
            return False
        rec = self.state.get("scenes", {}).get(str(scene_idx), {})
        return rec.get("narration_hash") == current_hash

    def compute_scene_visual_hash(
        self,
        prompt: str,
        aspect_ratio: str,
        reference_image: Optional[Path] = None,
    ) -> str:
        ref_hash = compute_file_sha256(reference_image) if reference_image else ""
        content = f"{prompt.strip()}|{aspect_ratio}|{ref_hash}"
        return compute_sha256(content)

    def is_image_current(self, scene_idx: int, current_hash: str, image_file: Path) -> bool:
        if not image_file.is_file():
            return False
        rec = self.state.get("scenes", {}).get(str(scene_idx), {})
        return rec.get("visual_prompt_hash") == current_hash

    def compute_scene_clip_hash(
        self,
        image_path: Path,
        duration: float,
        camera_movement: str,
        fps: int,
        width: int,
        height: int,
    ) -> str:
        img_hash = compute_file_sha256(image_path)
        content = f"{img_hash}|{duration:.2f}|{camera_movement}|{fps}|{width}x{height}"
        return compute_sha256(content)

    def is_clip_current(self, scene_idx: int, current_hash: str, clip_file: Path) -> bool:
        if not clip_file.is_file():
            return False
        rec = self.state.get("scenes", {}).get(str(scene_idx), {})
        return rec.get("clip_hash") == current_hash

    def update_scene_record(
        self,
        scene_idx: int,
        narration_hash: Optional[str] = None,
        visual_prompt_hash: Optional[str] = None,
        clip_hash: Optional[str] = None,
        duration: Optional[float] = None,
        image_path: Optional[str] = None,
        clip_path: Optional[str] = None,
    ):
        s_key = str(scene_idx)
        if s_key not in self.state["scenes"]:
            self.state["scenes"][s_key] = {}
        rec = self.state["scenes"][s_key]

        if narration_hash is not None:
            rec["narration_hash"] = narration_hash
        if visual_prompt_hash is not None:
            rec["visual_prompt_hash"] = visual_prompt_hash
        if clip_hash is not None:
            rec["clip_hash"] = clip_hash
        if duration is not None:
            rec["duration"] = duration
        if image_path is not None:
            rec["image_path"] = image_path
        if clip_path is not None:
            rec["clip_path"] = clip_path

        self.save()
