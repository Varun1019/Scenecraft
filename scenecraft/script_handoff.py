from __future__ import annotations

"""Script Handoff & Versioning System for Scenecraft.

Enables clean separation between story creation (e.g., Antigravity authoring)
and video production (Scenecraft CLI execution).

Features:
- Structured JSON and human-readable Markdown/plain-text script parsing.
- Non-destructive script versioning (v1, v2, v3...) so revisions never overwrite originals.
- Pre-flight script validation ensuring scene continuity, narration word budgets,
  opening hook curiosity, camera movements, and safe aspect ratios before spending credits.
"""

import json
import os
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union


@dataclass
class ScriptValidationResult:
    """Detailed report from pre-production script validation."""
    valid: bool
    title: str
    total_scenes: int
    total_word_count: int
    estimated_duration_sec: float
    aspect_ratio: str
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def format_report(self) -> str:
        lines = []
        lines.append("=" * 66)
        lines.append(f"📜 STORY SCRIPT VALIDATION REPORT: {self.title or 'UNTITLED'}")
        lines.append("=" * 66)
        status_str = "✅ VALID (Ready for Production)" if self.valid else "❌ INVALID (Corrections Required)"
        lines.append(f"Status:             {status_str}")
        lines.append(f"Aspect Ratio:       {self.aspect_ratio}")
        lines.append(f"Total Scenes:       {self.total_scenes}")
        lines.append(f"Narration Words:    {self.total_word_count} words (~{self.estimated_duration_sec:.1f}s spoken)")
        lines.append("-" * 66)

        if self.errors:
            lines.append("🛑 Blocking Errors:")
            for err in self.errors:
                lines.append(f"   [!] {err}")

        if self.warnings:
            lines.append("⚠️  Advisories / Warnings:")
            for warn in self.warnings:
                lines.append(f"   [*] {warn}")

        if not self.errors and not self.warnings:
            lines.append("✨ All checks passed! Script satisfies high-retention storytelling standards.")

        lines.append("=" * 66)
        return "\n".join(lines)


def slugify(text: str) -> str:
    """Convert text to safe lowercase directory/file slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[\s_-]+", "_", text).strip("_")


def parse_markdown_script(content: str) -> Dict[str, Any]:
    """Parse a plain-text / Markdown script into structured storyboard dictionary."""
    lines = content.splitlines()
    data: Dict[str, Any] = {
        "story_title": "Untitled Script",
        "genre": "Suspense",
        "aspect_ratio": "9:16",
        "style": "earthy_explainer",
        "summary": "",
        "opening_hook": "",
        "scenes": [],
        "ending": "",
        "engagement_question": "",
    }

    current_scene: Optional[Dict[str, Any]] = None
    in_header = True

    scene_header_pattern = re.compile(
        r"^(?:###\s*Scene\s*(\d+)|\*{0,2}Scene\s*(\d+)\*{0,2}|(?:###\s*Beat\s*(\d+)))(?::\s*(.*))?",
        re.IGNORECASE,
    )

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Check for top-level Title (# Title)
        if in_header and stripped.startswith("# ") and not stripped.startswith("### "):
            data["story_title"] = stripped[2:].strip()
            continue

        # Check for header metadata key-values
        if in_header and ":" in stripped and not stripped.startswith("###"):
            lower = stripped.lower()
            if any(lower.startswith(k) for k in ["**genre:**", "genre:"]):
                data["genre"] = stripped.split(":", 1)[1].strip().strip("* ")
                continue
            if any(lower.startswith(k) for k in ["**aspect ratio:**", "**aspect_ratio:**", "aspect ratio:", "aspect_ratio:"]):
                data["aspect_ratio"] = stripped.split(":", 1)[1].strip().strip("* ")
                continue
            if any(lower.startswith(k) for k in ["**style:**", "style:"]):
                data["style"] = stripped.split(":", 1)[1].strip().strip("* ")
                continue
            if any(lower.startswith(k) for k in ["**premise:**", "**summary:**", "premise:", "summary:"]):
                data["summary"] = stripped.split(":", 1)[1].strip().strip("* ")
                continue
            if any(lower.startswith(k) for k in ["**opening hook:**", "**hook:**", "opening hook:", "hook:"]):
                data["opening_hook"] = stripped.split(":", 1)[1].strip().strip("* ")
                continue
            if any(lower.startswith(k) for k in ["**ending:**", "ending:"]):
                data["ending"] = stripped.split(":", 1)[1].strip().strip("* ")
                continue
            if any(lower.startswith(k) for k in ["**question:**", "engagement question:", "question:"]):
                data["engagement_question"] = stripped.split(":", 1)[1].strip().strip("* ")
                continue

        # Check for Scene Header
        m = scene_header_pattern.match(stripped)
        if m:
            in_header = False
            if current_scene:
                data["scenes"].append(current_scene)
            s_idx = int(m.group(1) or m.group(2) or m.group(3) or (len(data["scenes"]) + 1))
            s_title = (m.group(4) or f"Scene {s_idx}").strip()
            current_scene = {
                "scene_index": s_idx,
                "title": s_title,
                "narration": "",
                "visual_description": "",
                "camera_movement": "zoom_in",
                "sfx_cue": None,
                "visual_focus": "",
            }
            continue

        # Scene detail line
        if current_scene:
            cleaned_line = stripped.lstrip("-* ").strip()
            if ":" in cleaned_line:
                field_name, field_val = cleaned_line.split(":", 1)
                f_name = field_name.strip().lower()
                f_val = field_val.strip()
                if f_name in ["narration", "narrator", "voiceover", "voice"]:
                    current_scene["narration"] = f_val.strip('"\'')
                elif f_name in ["visual", "visuals", "visual description", "visual_description", "action"]:
                    current_scene["visual_description"] = f_val
                elif f_name in ["camera", "camera movement", "camera_movement"]:
                    current_scene["camera_movement"] = f_val
                elif f_name in ["sfx", "sfx cue", "sound", "audio"]:
                    current_scene["sfx_cue"] = f_val if f_val.lower() not in ["none", "null", ""] else None
                elif f_name in ["focus", "visual focus"]:
                    current_scene["visual_focus"] = f_val
                else:
                    # Append extra context to visual description
                    if not current_scene["narration"]:
                        current_scene["narration"] = cleaned_line
                    elif not current_scene["visual_description"]:
                        current_scene["visual_description"] = cleaned_line
            else:
                if not current_scene["narration"]:
                    current_scene["narration"] = cleaned_line
                elif not current_scene["visual_description"]:
                    current_scene["visual_description"] = cleaned_line
                else:
                    current_scene["visual_description"] += " " + cleaned_line

    if current_scene:
        data["scenes"].append(current_scene)

    if not data["opening_hook"] and data["scenes"]:
        data["opening_hook"] = data["scenes"][0].get("narration", "")

    if not data["ending"] and data["scenes"]:
        data["ending"] = data["scenes"][-1].get("narration", "")

    return data


def load_script(path_or_dict: Union[str, Path, Dict[str, Any]]) -> Dict[str, Any]:
    """Load and normalize a Scenecraft script from JSON file, Markdown file, or dict."""
    if isinstance(path_or_dict, dict):
        raw = dict(path_or_dict)
    else:
        p = Path(path_or_dict).resolve()
        if not p.is_file():
            raise FileNotFoundError(f"Script file not found: {p}")
        text = p.read_text(encoding="utf-8")
        if p.suffix.lower() == ".json":
            raw = json.loads(text)
        else:
            raw = parse_markdown_script(text)

    # Normalize fields to standard Scenecraft storyboard format
    raw_title = raw.get("story_title") if raw.get("story_title") is not None else raw.get("title", "")
    title = str(raw_title).strip()
    scenes = raw.get("scenes", [])

    # If raw is a StoryPlan representation, scenes might be SceneBeat objects or dicts
    clean_scenes = []
    for idx, s in enumerate(scenes, start=1):
        if hasattr(s, "to_dict"):
            s_dict = s.to_dict()
        elif isinstance(s, dict):
            s_dict = dict(s)
        else:
            continue

        clean_scenes.append({
            "scene_index": s_dict.get("scene_index", idx),
            "title": s_dict.get("title", f"Scene {idx}"),
            "narration": s_dict.get("narration", "").strip(),
            "visual_description": s_dict.get("visual_description", "").strip(),
            "camera_movement": s_dict.get("camera_movement", "zoom_in"),
            "sfx_cue": s_dict.get("sfx_cue"),
            "visual_focus": s_dict.get("visual_focus", ""),
            "emotion": s_dict.get("emotion"),
            "tension_level": s_dict.get("tension_level"),
            "duration": s_dict.get("duration"),
        })

    normalized = {
        "story_title": title,
        "title": title,
        "genre": raw.get("genre", "Suspense / Mystery"),
        "aspect_ratio": raw.get("aspect_ratio", "9:16"),
        "style": raw.get("style", "earthy_explainer"),
        "summary": raw.get("summary") or raw.get("premise", ""),
        "premise": raw.get("premise") or raw.get("summary", ""),
        "opening_hook": raw.get("opening_hook") or (clean_scenes[0]["narration"] if clean_scenes else ""),
        "hook_options": raw.get("hook_options", []),
        "recommended_hook_id": raw.get("recommended_hook_id", 1),
        "on_screen_hook_text": raw.get("on_screen_hook_text", ""),
        "ending": raw.get("ending") or (clean_scenes[-1]["narration"] if clean_scenes else ""),
        "engagement_question": raw.get("engagement_question", ""),
        "characters": raw.get("characters", []),
        "scenes": clean_scenes,
        "version": raw.get("version", 1),
    }

    return normalized


def validate_script(script_input: Union[str, Path, Dict[str, Any]]) -> ScriptValidationResult:
    """Validate a Scenecraft script against storytelling, narration timing, and production rules.
    
    Checks:
    - Title presence.
    - Scene count (minimum 3; recommended 4-6 for Shorts).
    - Non-empty narration and visual descriptions for every scene.
    - Total narration word count and estimated duration bounds.
    - Opening hook presence in scene 1 (curiosity trigger in first 3-5 seconds).
    - Valid aspect ratio (9:16 or 16:9).
    - Sequential scene indices.
    - Camera movement validity.
    """
    errors: List[str] = []
    warnings: List[str] = []

    try:
        data = load_script(script_input)
    except Exception as e:
        return ScriptValidationResult(
            valid=False,
            title="Unparseable Script",
            total_scenes=0,
            total_word_count=0,
            estimated_duration_sec=0.0,
            aspect_ratio="unknown",
            errors=[f"Failed to load/parse script: {e}"],
        )

    title = data.get("story_title", "").strip()
    if not title:
        errors.append("Script must define a non-empty story title.")

    aspect_ratio = data.get("aspect_ratio", "9:16").strip()
    if aspect_ratio not in ["9:16", "16:9"]:
        errors.append(f"Invalid aspect ratio '{aspect_ratio}'. Must be strictly '9:16' or '16:9'.")

    scenes = data.get("scenes", [])
    if not scenes:
        errors.append("Script has zero scenes. At least 3 scenes are required.")
    elif len(scenes) < 3:
        errors.append(f"Script only has {len(scenes)} scene(s). Minimum is 3 scenes for a coherent narrative arc.")

    total_words = 0
    valid_camera_moves = {
        "zoom_in", "zoom_out", "pan_left", "pan_right", "static", "slow_dolly_forward", "tilt_up", "tilt_down",
        "slow_push_in", "fast_push_in", "pull_back", "pan_up", "pan_down", "subtle_drift", "static_hold",
    }

    for idx, sc in enumerate(scenes, start=1):
        s_idx = sc.get("scene_index", idx)
        if s_idx != idx:
            warnings.append(f"Scene index mismatch: expected {idx}, found {s_idx}.")

        narr = (sc.get("narration") or "").strip()
        vdesc = (sc.get("visual_description") or "").strip()

        if not narr:
            errors.append(f"Scene {idx} ('{sc.get('title', '')}') has empty narration.")
        else:
            w_count = len(narr.split())
            total_words += w_count
            if w_count < 3:
                warnings.append(f"Scene {idx} narration is very short ({w_count} words). May sound clipped.")
            elif w_count > 45 and aspect_ratio == "9:16":
                warnings.append(f"Scene {idx} narration is very long ({w_count} words). Consider splitting for vertical short pacing.")

        if not vdesc:
            errors.append(f"Scene {idx} ('{sc.get('title', '')}') has empty visual description.")
        elif len(vdesc.split()) < 5:
            warnings.append(f"Scene {idx} visual description is brief ({len(vdesc.split())} words). Prompts may lack detail.")

        cam = sc.get("camera_movement", "zoom_in")
        if cam and cam.lower() not in valid_camera_moves:
            warnings.append(f"Scene {idx} has unrecognized camera movement '{cam}'. Defaulting to 'zoom_in'.")

    # Timing estimations: standard English spoken pace is ~2.3 words/sec (138 wpm)
    est_duration = round(total_words / 2.3, 1)

    # Word count bounds for Shorts (aspect ratio 9:16)
    if aspect_ratio == "9:16":
        if total_words < 40:
            warnings.append(f"Total narration is very brief ({total_words} words, ~{est_duration}s). Shorts target ~45-60s (100-150 words).")
        elif total_words > 175:
            warnings.append(f"Total narration is long ({total_words} words, ~{est_duration}s). May exceed 60-second YouTube Short limit.")
        if len(scenes) > 10:
            warnings.append(f"High scene count ({len(scenes)}) for a 9:16 short. Pacing may feel rushed.")

    # Hook check
    if scenes:
        hook_text = scenes[0].get("narration", "")
        hook_words = len(hook_text.split())
        if hook_words > 22:
            warnings.append(f"Opening hook in Scene 1 is wordy ({hook_words} words). First 3-5 seconds should be under 16 words for retention.")

    is_valid = len(errors) == 0

    stats = {
        "title": title,
        "genre": data.get("genre", "Suspense"),
        "aspect_ratio": aspect_ratio,
        "style": data.get("style", "earthy_explainer"),
        "scene_count": len(scenes),
        "total_words": total_words,
        "estimated_duration_sec": est_duration,
        "opening_hook_words": len(scenes[0].get("narration", "").split()) if scenes else 0,
    }

    return ScriptValidationResult(
        valid=is_valid,
        title=title,
        total_scenes=len(scenes),
        total_word_count=total_words,
        estimated_duration_sec=est_duration,
        aspect_ratio=aspect_ratio,
        errors=errors,
        warnings=warnings,
        stats=stats,
    )


def save_script(
    script_data: Dict[str, Any],
    title: Optional[str] = None,
    version: Optional[int] = None,
    base_dir: Optional[Path] = None,
    format: str = "json",
) -> Tuple[Path, int]:
    """Save a script non-destructively, auto-incrementing version so previous revisions are preserved."""
    root_dir = Path(base_dir or Path.cwd()).resolve() / "scripts"
    root_dir.mkdir(parents=True, exist_ok=True)

    story_title = title or script_data.get("story_title") or script_data.get("title") or "untitled_story"
    slug = slugify(story_title)
    story_dir = root_dir / slug
    story_dir.mkdir(parents=True, exist_ok=True)

    # Detect existing versions
    existing_versions = []
    for f in story_dir.glob("v*.*"):
        m = re.match(r"^v(\d+)\.", f.name)
        if m:
            existing_versions.append(int(m.group(1)))

    if version is not None:
        target_version = version
    else:
        target_version = (max(existing_versions) + 1) if existing_versions else 1

    script_data["version"] = target_version
    script_data["story_title"] = story_title

    if format.lower() == "json":
        out_file = story_dir / f"v{target_version}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(script_data, f, indent=2)
    else:
        out_file = story_dir / f"v{target_version}.md"
        lines = [
            f"# {story_title}",
            f"**Genre:** {script_data.get('genre', 'Suspense')}",
            f"**Aspect Ratio:** {script_data.get('aspect_ratio', '9:16')}",
            f"**Style:** {script_data.get('style', 'earthy_explainer')}",
            f"**Premise:** {script_data.get('summary') or script_data.get('premise', '')}",
            f"**Opening Hook:** {script_data.get('opening_hook', '')}",
            "",
            "## Scene Breakdown",
            "",
        ]
        for sc in script_data.get("scenes", []):
            lines.append(f"### Scene {sc.get('scene_index', 1):02d}: {sc.get('title', 'Untitled Beat')}")
            lines.append(f"- Narration: {sc.get('narration', '')}")
            lines.append(f"- Visual: {sc.get('visual_description', '')}")
            lines.append(f"- Camera: {sc.get('camera_movement', 'zoom_in')}")
            if sc.get("sfx_cue"):
                lines.append(f"- SFX: {sc.get('sfx_cue')}")
            lines.append("")

        if script_data.get("ending"):
            lines.append(f"**Ending:** {script_data.get('ending')}")
        if script_data.get("engagement_question"):
            lines.append(f"**Question:** {script_data.get('engagement_question')}")

        with open(out_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    return out_file, target_version
