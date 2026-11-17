"""Prompt builder for Flow / Nano Banana matching cinematic graphic-novel illustration style."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from storyforge.visual_intelligence import (
    CharacterSpec,
    CinematicPromptEngine,
    DEFAULT_STICKMAN_IDENTITY,
    DARK_COMIC_STYLE_HEADER,
    STRICT_NEGATIVE_CONSTRAINTS,
    get_character_reference_for_shot,
)

CHARACTER_ANCHOR = DEFAULT_STICKMAN_IDENTITY
CINEMATIC_STYLE_PREFIX = DARK_COMIC_STYLE_HEADER
COMPOSITION_CONSTRAINTS = STRICT_NEGATIVE_CONSTRAINTS


@dataclass
class ScenePrompt:
    scene_index: int
    title: str
    narration: str
    visual_description: str
    aspect_ratio: str = "16:9"
    sfx_cue: str | None = None
    camera_movement: str = "zoom_in"  # zoom_in, zoom_out, pan_left, pan_right
    emotion: str = "SUSPENSE"
    shot_type: Optional[str] = None
    character: Optional[CharacterSpec] = None
    compiled_prompt: Optional[str] = None
    reference_angle_path: Optional[Path] = None
    style_preset: str = "dark_cinematic"

    def full_prompt(self) -> str:
        """Compose the full prompt combining character anchor, scene specifics, and strict single-shot rules."""
        if self.compiled_prompt:
            return self.compiled_prompt

        engine = CinematicPromptEngine()
        char = self.character or CharacterSpec()
        prompt, _ = engine.build_scene_prompt(
            scene_idx=self.scene_index,
            total_scenes=6,
            title=self.title,
            narration=self.narration,
            visual_action=self.visual_description,
            character=char,
            emotion=self.emotion,
            aspect_ratio=self.aspect_ratio,
            previous_shot=None,
            style_preset=self.style_preset,
        )
        return prompt


def build_prompts_from_scenes(
    scenes_data: List[Dict[str, Any]],
    aspect_ratio: str = "16:9",
    character_data: Optional[Dict[str, Any]] = None,
    style_preset: str = "dark_cinematic",
) -> List[ScenePrompt]:
    """Convert parsed scene dicts into ScenePrompt objects with single-shot constraints and visual intelligence."""
    char_spec = CharacterSpec.from_dict(character_data) if character_data else CharacterSpec()
    engine = CinematicPromptEngine()
    total_scenes = len(scenes_data)
    prompts = []
    prev_shot = None

    for idx, s in enumerate(scenes_data, start=1):
        emo = s.get("emotion") or "SUSPENSE"
        action = s.get("visual_description", "")
        title = s.get("title", f"Scene {idx}")
        narr = s.get("narration", "")
        dir_shot = s.get("shot_type")

        compiled_prompt, shot_type = engine.build_scene_prompt(
            scene_idx=idx,
            total_scenes=total_scenes,
            title=title,
            narration=narr,
            visual_action=action,
            character=char_spec,
            emotion=emo,
            aspect_ratio=aspect_ratio,
            previous_shot=prev_shot,
            style_preset=style_preset,
            shot_type=dir_shot,
        )
        prev_shot = shot_type
        ref_angle = get_character_reference_for_shot(shot_type)

        prompts.append(
            ScenePrompt(
                scene_index=idx,
                title=title,
                narration=narr,
                visual_description=action,
                aspect_ratio=aspect_ratio,
                sfx_cue=s.get("sfx_cue"),
                camera_movement=s.get("camera_movement", "zoom_in"),
                emotion=emo,
                shot_type=shot_type,
                character=char_spec,
                compiled_prompt=compiled_prompt,
                reference_angle_path=ref_angle,
                style_preset=style_preset,
            )
        )
    return prompts
