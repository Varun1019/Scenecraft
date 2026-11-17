from __future__ import annotations

"""Intelligent Scene Direction Engine for StoryForge.

Determines cinematic shot composition, camera framing, subject positioning,
camera movement, lighting atmosphere, transitions, and sound design for each scene.

Guarantees narrative-driven camera variation and eliminates repetitive zoom-ins.
"""

import re
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple


# ==============================================================================
# CINEMATIC SHOT DEFINITIONS
# ==============================================================================

CINEMATIC_SHOTS = {
    "ESTABLISHING_WIDE": {
        "name": "Establishing Wide Shot",
        "description": "Expansive wide establishing shot showing The Wanderer within the broader atmospheric environment to anchor spatial scale and geography.",
        "typical_movement": "slow_push_in",
        "subject_position": "center_focal",
    },
    "MEDIUM_CHARACTER": {
        "name": "Medium Character Shot",
        "description": "Waist-level cinematic medium shot focusing on The Wanderer actively interacting with props, tools, or the environment.",
        "typical_movement": "pan_left",
        "subject_position": "rule_of_thirds_left",
    },
    "CLOSE_UP_INTENSE": {
        "name": "Intense Close-Up",
        "description": "Tight close-up framing on The Wanderer's ivory head, dark black pill eyes, and expressive posture under dramatic rim light.",
        "typical_movement": "fast_push_in",
        "subject_position": "center_focal",
    },
    "EXTREME_CLOSE_UP": {
        "name": "Extreme Close-Up (Macro Detail)",
        "description": "Macro-level focal detail on a critical narrative prop (radio dials, padlock latch, trembling hand, or vibrating surface).",
        "typical_movement": "static_hold",
        "subject_position": "center_focal",
    },
    "OVER_THE_SHOULDER": {
        "name": "Over-The-Shoulder Framing",
        "description": "Over-the-shoulder framing looking past The Wanderer's striped scarf toward an approaching threat, open doorway, or ominous horizon.",
        "typical_movement": "pan_right",
        "subject_position": "foreground_silhouette",
    },
    "POINT_OF_VIEW": {
        "name": "Point-Of-View (POV)",
        "description": "Subjective first-person point-of-view perspective looking directly through The Wanderer's eyes at the immediate mystery or obstacle.",
        "typical_movement": "slow_push_in",
        "subject_position": "center_focal",
    },
    "LOW_ANGLE_HEROIC": {
        "name": "Low-Angle Dramatic Shot",
        "description": "Low-angle perspective looking sharply upward from the deck floor, emphasizing height, towering structures, and looming tension.",
        "typical_movement": "pan_up",
        "subject_position": "center_focal",
    },
    "HIGH_ANGLE_VULNERABLE": {
        "name": "High-Angle Vulnerable Shot",
        "description": "High-angle perspective looking down from above, capturing The Wanderer isolated against the expansive floor deck or rooftop gravel.",
        "typical_movement": "pan_down",
        "subject_position": "background_isolated",
    },
}

SUPPORTED_MOVEMENTS = [
    "slow_push_in",
    "fast_push_in",
    "pull_back",
    "pan_left",
    "pan_right",
    "pan_up",
    "pan_down",
    "subtle_drift",
    "static_hold",
]

SUPPORTED_TRANSITIONS = [
    "hard_cut",
    "crossfade",
    "dip_to_black",
]


@dataclass
class DirectorialBeat:
    """Complete directorial specifications for a single scene."""
    scene_index: int
    title: str
    narration: str
    emotional_purpose: str  # SUSPENSE, DREAD, PANIC, REVEAL, DISCOVERY, MYSTERY, CONTEMPLATION
    shot_type: str
    shot_description: str
    camera_movement: str
    subject_position: str  # center_focal, rule_of_thirds_left, rule_of_thirds_right, foreground_silhouette, background_isolated
    background_motion: str
    lighting_and_atmosphere: str
    transition_to_next: str
    ambience_cue: Optional[str] = None
    sfx_cue: Optional[str] = None
    sfx_offset_sec: float = 0.0
    visual_prompt_notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SceneDirector:
    """Directorial intelligence engine that orchestrates shot composition, motion, and continuity."""

    def __init__(self, style_preset: str = "earthy_explainer"):
        self.style_preset = style_preset

    def direct_scene(
        self,
        scene_idx: int,
        total_scenes: int,
        title: str,
        narration: str,
        visual_description: str,
        emotion: Optional[str] = None,
        sfx_cue: Optional[str] = None,
        previous_beat: Optional[DirectorialBeat] = None,
        aspect_ratio: str = "9:16",
    ) -> DirectorialBeat:
        """Derive an intelligent, narrative-driven directorial beat with guaranteed motion variation."""
        narr_lower = narration.lower()
        vis_lower = visual_description.lower()
        combined_text = f"{narr_lower} {vis_lower}"

        # 1. Determine Emotional Purpose
        emo = self._classify_emotion(combined_text, emotion, scene_idx, total_scenes)

        # 2. Select Shot Type (with repetition guard against previous_beat)
        shot_type = self._select_shot_type(
            scene_idx=scene_idx,
            total_scenes=total_scenes,
            emotion=emo,
            text=combined_text,
            previous_shot=previous_beat.shot_type if previous_beat else None,
        )
        shot_meta = CINEMATIC_SHOTS.get(shot_type, CINEMATIC_SHOTS["MEDIUM_CHARACTER"])

        # 3. Determine Subject Position
        subject_pos = self._determine_subject_position(shot_type, combined_text, aspect_ratio)

        # 4. Select Camera Movement (enforcing motion variation from previous scene)
        cam_move = self._select_camera_movement(
            shot_type=shot_type,
            emotion=emo,
            text=combined_text,
            previous_move=previous_beat.camera_movement if previous_beat else None,
        )

        # 5. Background Movement & Environmental Action
        bg_motion = self._derive_background_motion(combined_text, emo)

        # 6. Lighting & Atmosphere
        lighting = self._derive_lighting_atmosphere(emo, combined_text)

        # 7. Transition to Next Scene
        transition = self._select_transition(scene_idx, total_scenes, emo)

        # 8. Sound Design (Ambience + Synced SFX)
        ambience, resolved_sfx, sfx_offset = self._orchestrate_sound_design(
            emo, combined_text, sfx_cue, scene_idx
        )

        # 9. Directorial Prompt Notes for Image Generation
        dir_notes = (
            f"Framing: {shot_meta['name']}. {shot_meta['description']} "
            f"Subject Placement: {subject_pos.replace('_', ' ').title()}. "
            f"Lighting: {lighting} "
            f"Background Environment: {bg_motion}."
        )

        return DirectorialBeat(
            scene_index=scene_idx,
            title=title,
            narration=narration,
            emotional_purpose=emo,
            shot_type=shot_type,
            shot_description=shot_meta["description"],
            camera_movement=cam_move,
            subject_position=subject_pos,
            background_motion=bg_motion,
            lighting_and_atmosphere=lighting,
            transition_to_next=transition,
            ambience_cue=ambience,
            sfx_cue=resolved_sfx,
            sfx_offset_sec=sfx_offset,
            visual_prompt_notes=dir_notes,
        )

    def plan_sequence(
        self,
        scenes: List[Dict[str, Any]],
        aspect_ratio: str = "9:16",
    ) -> List[DirectorialBeat]:
        """Compile a full cinematic sequence with guaranteed visual progression and continuity."""
        beats: List[DirectorialBeat] = []
        total = len(scenes)

        for idx, sc in enumerate(scenes, start=1):
            prev = beats[-1] if beats else None
            beat = self.direct_scene(
                scene_idx=idx,
                total_scenes=total,
                title=sc.get("title", f"Scene {idx}"),
                narration=sc.get("narration", ""),
                visual_description=sc.get("visual_description", ""),
                emotion=sc.get("emotion"),
                sfx_cue=sc.get("sfx_cue"),
                previous_beat=prev,
                aspect_ratio=aspect_ratio,
            )
            beats.append(beat)

        return beats

    # --------------------------------------------------------------------------
    # INTERNAL HEURISTICS
    # --------------------------------------------------------------------------

    def _classify_emotion(
        self,
        text: str,
        explicit_emotion: Optional[str],
        scene_idx: int,
        total_scenes: int,
    ) -> str:
        if explicit_emotion:
            return explicit_emotion.upper()

        if any(k in text for k in ["panic", "breach", "run", "fast", "swallow", "wall of", "hurried"]):
            return "PANIC"
        if any(k in text for k in ["static", "warn", "extinguish", "rule", "alarm", "siren"]):
            return "DREAD"
        if any(k in text for k in ["groan", "rivet", "climbing", "vibrate", "knock", "tap"]):
            return "SHOCK"
        if any(k in text for k in ["unlocked", "padlock", "reveal", "truth", "inside"]):
            return "REVEAL"
        if any(k in text for k in ["silent", "refuge", "dusk", "skyline", "alone"]):
            return "SUSPENSE"

        if scene_idx == 1:
            return "SUSPENSE"
        elif scene_idx == total_scenes:
            return "REVEAL"
        return "DREAD"

    def _select_shot_type(
        self,
        scene_idx: int,
        total_scenes: int,
        emotion: str,
        text: str,
        previous_shot: Optional[str],
    ) -> str:
        # Contextual keywords with strict word boundaries
        if re.search(r"\b(look through|peephole|stare out|peer through)\b", text):
            candidate = "POINT_OF_VIEW"
        elif re.search(r"\b(dust|cloud|storm|towering|colossal|monolithic)\b", text):
            candidate = "LOW_ANGLE_HEROIC" if emotion in ["PANIC", "SHOCK"] else "ESTABLISHING_WIDE"
        elif re.search(r"\b(hatch|beneath|ladder|deck floor|downward)\b", text):
            candidate = "HIGH_ANGLE_VULNERABLE"
        elif re.search(r"\b(padlock|dials|latch|knob|deadbolt)\b", text) and scene_idx >= 3:
            candidate = "EXTREME_CLOSE_UP"
        elif re.search(r"\b(approaching|behind|turning toward)\b", text):
            candidate = "OVER_THE_SHOULDER"
        elif re.search(r"\b(radio|holding|kneel|inspecting|hands)\b", text):
            candidate = "MEDIUM_CHARACTER"
        elif scene_idx == 1:
            candidate = "ESTABLISHING_WIDE"
        elif scene_idx == total_scenes:
            candidate = "CLOSE_UP_INTENSE"
        elif emotion in ["SHOCK", "REVEAL"]:
            candidate = "CLOSE_UP_INTENSE"
        else:
            candidate = "MEDIUM_CHARACTER"

        # Repetition Guard: never repeat identical shot consecutively
        if previous_shot and candidate == previous_shot:
            alternatives = [
                s for s in ["MEDIUM_CHARACTER", "CLOSE_UP_INTENSE", "OVER_THE_SHOULDER", "HIGH_ANGLE_VULNERABLE", "LOW_ANGLE_HEROIC", "ESTABLISHING_WIDE"]
                if s != previous_shot
            ]
            candidate = alternatives[(scene_idx) % len(alternatives)]

        return candidate

    def _determine_subject_position(self, shot_type: str, text: str, aspect_ratio: str) -> str:
        if shot_type in ["CLOSE_UP_INTENSE", "EXTREME_CLOSE_UP"]:
            return "center_focal"
        elif shot_type == "OVER_THE_SHOULDER":
            return "foreground_silhouette"
        elif shot_type == "HIGH_ANGLE_VULNERABLE":
            return "background_isolated"
        elif shot_type == "MEDIUM_CHARACTER":
            return "rule_of_thirds_left" if aspect_ratio == "16:9" else "center_focal"
        elif shot_type == "ESTABLISHING_WIDE":
            return "center_focal" if aspect_ratio == "9:16" else "rule_of_thirds_right"
        return "center_focal"

    def _select_camera_movement(
        self,
        shot_type: str,
        emotion: str,
        text: str,
        previous_move: Optional[str],
    ) -> str:
        if emotion == "PANIC" or shot_type == "CLOSE_UP_INTENSE":
            candidate = "fast_push_in"
        elif shot_type == "EXTREME_CLOSE_UP":
            candidate = "static_hold"
        elif shot_type == "HIGH_ANGLE_VULNERABLE":
            candidate = "pan_down"
        elif shot_type == "LOW_ANGLE_HEROIC":
            candidate = "pan_up"
        elif shot_type == "MEDIUM_CHARACTER":
            candidate = "pan_left"
        elif shot_type == "OVER_THE_SHOULDER":
            candidate = "pan_right"
        elif shot_type == "ESTABLISHING_WIDE":
            candidate = "slow_push_in"
        else:
            candidate = "subtle_drift"

        # Motion Variation Guard: avoid consecutive identical movements (especially consecutive push-ins)
        if previous_move and candidate == previous_move:
            if candidate in ["slow_push_in", "fast_push_in"]:
                candidate = "pan_left" if "radio" in text else "subtle_drift"
            elif candidate.startswith("pan_"):
                candidate = "static_hold" if emotion in ["SHOCK", "REVEAL"] else "slow_push_in"
            else:
                candidate = "pull_back"

        return candidate

    def _derive_background_motion(self, text: str, emotion: str) -> str:
        if "dust" in text or "cloud" in text or "storm" in text:
            return "Dense chemical dust front rolling horizontally across the horizon with atmospheric smog drift."
        elif "radio" in text or "static" in text:
            return "Faint red LED indicator lights glowing in the dimly lit concrete mechanical background."
        elif "hatch" in text or "rivet" in text:
            return "Subtle mechanical vibration lines radiating along the bolted iron door plate and weathered concrete deck."
        elif "padlock" in text or "lock" in text:
            return "Cold twilight air stirring loose gravel around the unlatched hatch opening."
        else:
            return "Still silhouette skyline under dusky twilight with distant cold city blackout."

    def _derive_lighting_atmosphere(self, emotion: str, text: str) -> str:
        if emotion == "PANIC":
            return "Harsh high-contrast amber and ochre atmospheric haze with dark cast shadows."
        elif emotion == "SHOCK" or "padlock" in text:
            return "Dramatic low-key rim lighting, stark cold moonlight cutting across weathered iron textures."
        elif emotion == "DREAD":
            return "Muted dusty olive and concrete grey palette, dim directional lamp glow, deep charcoal shadows."
        else:
            return "Atmospheric dusky amber twilight, soft cinematic cel shading, clean graphic-novel contrast."

    def _select_transition(self, scene_idx: int, total_scenes: int, emotion: str) -> str:
        # Penultimate into climax or fast shock -> hard cut for impact
        if scene_idx == total_scenes - 1 or emotion in ["SHOCK", "PANIC"]:
            return "hard_cut"
        elif scene_idx == 1:
            return "crossfade"
        elif emotion == "REVEAL":
            return "dip_to_black"
        return "hard_cut"

    def _orchestrate_sound_design(
        self,
        emotion: str,
        text: str,
        user_sfx: Optional[str],
        scene_idx: int,
    ) -> Tuple[str, Optional[str], float]:
        # Ambience mapping
        if "storm" in text or "dust" in text or "wind" in text:
            ambience = "amb_rain_heavy"  # storm / weather bed
        elif emotion in ["PANIC", "SHOCK"]:
            ambience = "amb_tension_drone"
        else:
            ambience = "apocalypse_ambient_drone.wav"

        # Primary SFX selection
        if user_sfx:
            resolved_sfx = user_sfx
        elif "radio" in text or "static" in text:
            resolved_sfx = "sfx_radio_static"
        elif "hatch" in text or "rivet" in text or "groan" in text:
            resolved_sfx = "sfx_pipe_tap"
        elif "padlock" in text or "unlocked" in text:
            resolved_sfx = "sfx_tape_click"
        elif "storm" in text or "swallow" in text:
            resolved_sfx = "sfx_tension_drone"
        elif scene_idx == 1:
            resolved_sfx = "sfx_whoosh_cinematic"
        else:
            resolved_sfx = None

        offset = 0.25 if scene_idx > 1 else 0.1
        return ambience, resolved_sfx, offset
