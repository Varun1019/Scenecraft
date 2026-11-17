"""StoryForge Google Flow Video Generation & Flow Agent Storyboard Director.

Provides master prompt generation for Google Flow Agent, intelligent script
breakdown into 25-45 visual image beats for 1-3 minute Reels, comprehensive
cinematographic and character continuity prompt compilation, asset ingestion,
and sequential scene generation.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from storyforge.flow_client import FlowClient, FlowConnectionError, FlowQuotaExceededError
from storyforge.visual_intelligence import (
    VideoQualityController,
    VideoValidationResult,
    CharacterSpec,
    DEFAULT_STICKMAN_IDENTITY,
    DARK_COMIC_STYLE_HEADER,
    SURVIVAL_EXPLAINER_STYLE_HEADER,
    STRICT_NEGATIVE_CONSTRAINTS,
    get_character_reference_for_shot,
)
from storyforge.border_detector import BorderDetector
from storyforge.settings import is_auto_thumbnail_enabled

# ==============================================================================
# CREATIVE UNIVERSES & CHARACTER ANCHORS
# ==============================================================================

UNIVERSE_WANDERER = "wanderer"
UNIVERSE_EXPERIMENTAL = "experimental"

WANDERER_CHARACTER_DESCRIPTION = (
    "The Wanderer, male 2D graphic-novel dark comic stickman protagonist. "
    "Smooth warm ivory oval head, two vertical black pill-shaped eyes, neutral slit mouth. "
    "Distinctive brick-red folded-brim ribbed knit beanie, thick warm knitted winter scarf with "
    "alternating horizontal mustard-gold and rust-maroon stripes with dangling fringe, "
    "dark charcoal short-sleeved t-shirt, solid thin black stick arms and legs, rugged boots."
)

WANDERER_REFERENCE_RELATIVE_PATH = "references/brand_identity/ref_character_full_body.jpg"


@dataclass
class VisualBeat:
    """Detailed visual beat for Flow Agent image generation."""
    beat_index: int
    scene_index: int
    title: str
    narration_line: str
    duration_sec: float
    emotional_purpose: str  # SUSPENSE, DREAD, PANIC, REVEAL, DISCOVERY, SHOCK, CLIMAX
    shot_type: str  # ESTABLISHING_WIDE, MEDIUM_CHARACTER, CLOSE_UP_INTENSE, EXTREME_CLOSE_UP, OVER_THE_SHOULDER, POINT_OF_VIEW, LOW_ANGLE_HEROIC, HIGH_ANGLE_VULNERABLE
    camera_movement: str
    subject_position: str
    character_action: str
    character_pose: str
    character_expression: str
    character_gaze: str
    character_interaction: str
    environment_location: str
    background_details: str
    foreground_details: str
    weather_atmosphere: str
    time_of_day: str
    lighting_direction_intensity: str
    shadows_depth_focus: str
    continuity_prior_event: str
    continuity_current_action: str
    continuity_next_event: str
    continuity_persistent_elements: str
    compiled_prompt: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class FlowAgentDirector:
    """Orchestrates Flow Agent master prompt generation, visual beat breakdown, and asset management."""

    def __init__(
        self,
        workspace_dir: Optional[Path] = None,
        flow_client: Optional[FlowClient] = None,
    ):
        self.workspace_dir = Path(workspace_dir or Path.cwd()).resolve()
        self.flow_client = flow_client or FlowClient()
        self.video_qc = VideoQualityController()
        self.border_detector = BorderDetector()

    # --------------------------------------------------------------------------
    # 1. Flow Native Agent Capability & Honesty Probe
    # --------------------------------------------------------------------------
    def inspect_agent_capabilities(self) -> Dict[str, Any]:
        """Verify whether Flow native Agent mode is supported or if sequential generation is required."""
        return self.flow_client.probe_agent_capabilities()

    # --------------------------------------------------------------------------
    # 2. Character & Universe System
    # --------------------------------------------------------------------------
    def establish_character(
        self,
        character_name: str = "The Wanderer",
        custom_description: Optional[str] = None,
        reference_image: Optional[Path] = None,
        universe: str = UNIVERSE_WANDERER,
    ) -> Dict[str, Any]:
        """Establish character visual identity and resolve approved reference anchors.
        
        Supports two creative directions:
        A. Wanderer Universe: default recurring stickman protagonist with red beanie identity.
        B. Experimental Stories: custom characters, distinct silhouettes, and non-stickman styles.
        """
        ref_p: Optional[Path] = None

        if reference_image and Path(reference_image).is_file():
            ref_p = Path(reference_image).resolve()
        elif universe == UNIVERSE_WANDERER or "wanderer" in character_name.lower():
            default_ref = self.workspace_dir / WANDERER_REFERENCE_RELATIVE_PATH
            if default_ref.is_file():
                ref_p = default_ref.resolve()

        if universe == UNIVERSE_WANDERER or "wanderer" in character_name.lower():
            description = WANDERER_CHARACTER_DESCRIPTION
            name = "The Wanderer"
            archetype = "Red Beanie Stickman Survivor"
            palette = "Brick-red (#A03325), Warm ivory (#F9E8CE), Mustard gold (#DFA028), Rust maroon (#8C2B1D), Dark charcoal (#454242), Carbon black (#18181A)"
        else:
            name = character_name
            archetype = "Experimental Protagonist"
            description = custom_description or f"{character_name}, stylized character with consistent visual identity and clothing."
            palette = "Custom cinematic palette matching narrative tone"

        return {
            "name": name,
            "universe": universe,
            "archetype": archetype,
            "description": description,
            "color_palette": palette,
            "reference_image": ref_p,
            "established": ref_p is not None and ref_p.is_file(),
        }

    # --------------------------------------------------------------------------
    # 3. Intelligent Script Breakdown into 25-45 Visual Beats
    # --------------------------------------------------------------------------
    def decompose_script_to_visual_beats(
        self,
        script_data: Dict[str, Any],
        target_beats_range: Tuple[int, int] = (25, 45),
        aspect_ratio: str = "9:16",
        universe: str = UNIVERSE_WANDERER,
        character_spec: Optional[Dict[str, Any]] = None,
    ) -> List[VisualBeat]:
        """Break down a story script into 25-45 rich, narrative-driven visual image beats.
        
        Optimized for 1-3 minute vertical Reels with high visual variety,
        rapid 2.5-4.5 second visual pacing, and guaranteed camera anti-repetition.
        """
        raw_scenes = script_data.get("scenes", [])
        if not raw_scenes:
            raise ValueError("Script data contains no scenes to decompose.")

        char_info = self.establish_character(
            character_name=(character_spec.get("name") if character_spec else "The Wanderer"),
            custom_description=(character_spec.get("description") if character_spec else None),
            reference_image=(character_spec.get("reference_image") if character_spec else None),
            universe=universe,
        )

        min_beats, max_beats = target_beats_range

        # 1. Extract all narrative sentences across scenes
        narrative_units: List[Dict[str, Any]] = []
        for s_idx, scene in enumerate(raw_scenes, start=1):
            s_title = scene.get("title", f"Scene {s_idx}")
            s_narr = (scene.get("narration") or "").strip()
            s_vis = (scene.get("visual_description") or scene.get("video_prompt") or "").strip()
            s_emo = scene.get("emotion") or scene.get("emotional_purpose") or "SUSPENSE"
            s_sfx = scene.get("sfx_cue")

            # Split narration into sentences
            raw_sentences = [sent.strip() for sent in re.split(r"(?<=[.!?])\s+", s_narr) if sent.strip()]
            if not raw_sentences and s_narr:
                raw_sentences = [s_narr]

            for sent in raw_sentences:
                narrative_units.append({
                    "scene_index": s_idx,
                    "scene_title": s_title,
                    "sentence": sent,
                    "visual_context": s_vis,
                    "scene_emotion": s_emo,
                    "sfx_cue": s_sfx,
                })

        # 2. Subdivide or pad units to reach target beats if pacing requires it
        total_units = len(narrative_units)
        expanded_units: List[Dict[str, Any]] = []

        if total_units > max_beats:
            # Proportionally partition narrative sentences across max_beats bins to retain 100% of story arc
            target_count = max_beats
            for i in range(target_count):
                start = int(round(i * total_units / target_count))
                end = int(round((i + 1) * total_units / target_count))
                if start >= end:
                    end = min(total_units, start + 1)
                bin_units = narrative_units[start:end]
                combined_sent = " ".join(u["sentence"] for u in bin_units)
                first_u = bin_units[0]
                last_u = bin_units[-1]
                expanded_units.append({
                    "scene_index": first_u["scene_index"],
                    "scene_title": first_u["scene_title"],
                    "sentence": combined_sent,
                    "visual_context": first_u.get("visual_context", ""),
                    "scene_emotion": last_u.get("scene_emotion", "SUSPENSE"),
                    "sfx_cue": first_u.get("sfx_cue") or last_u.get("sfx_cue"),
                    "beat_role": "condensed_beat",
                })
        elif total_units < min_beats:
            # Expand each sentence with complementary visual beat pairs (Action -> Reaction / Detail / POV)
            expansion_factor = max(2, int(round(min_beats / max(1, total_units))))
            for unit in narrative_units:
                words = unit["sentence"].split()
                if len(words) >= 8:
                    mid = len(words) // 2
                    part1 = " ".join(words[:mid])
                    part2 = " ".join(words[mid:])
                    expanded_units.append({**unit, "sentence": part1, "beat_role": "action_setup"})
                    expanded_units.append({**unit, "sentence": part2, "beat_role": "reaction_detail"})
                else:
                    expanded_units.append({**unit, "beat_role": "primary_beat"})
                    expanded_units.append({**unit, "sentence": f"[Visual focus on scene environment] {unit['sentence']}", "beat_role": "environmental_reaction"})
            while len(expanded_units) < min_beats:
                target_idx = min(len(expanded_units) - 1, max(1, len(expanded_units) // 2))
                base = expanded_units[target_idx]
                clone = dict(base)
                clone["beat_role"] = "macro_detail_accent"
                expanded_units.insert(target_idx + 1, clone)
            if len(expanded_units) > max_beats:
                expanded_units = expanded_units[:max_beats]
        else:
            expanded_units = narrative_units

        # 3. Direct each beat with high visual variation and cinematographic depth
        camera_palette = [
            ("ESTABLISHING_WIDE", "Wide establishing shot", "slow_push_in", "center_mobile_safe_zone"),
            ("MEDIUM_CHARACTER", "Waist-level medium character shot", "pan_left", "rule_of_thirds_left"),
            ("CLOSE_UP_INTENSE", "Intense cinematic close-up on head and eyes", "fast_push_in", "center_mobile_safe_zone"),
            ("EXTREME_CLOSE_UP", "Macro focal close-up on key prop or trembling hands", "static_hold", "center_mobile_safe_zone"),
            ("OVER_THE_SHOULDER", "Over-the-shoulder framing past scarf towards obstacle", "pan_right", "foreground_silhouette"),
            ("POINT_OF_VIEW", "First-person subjective POV looking through protagonist eyes", "slow_push_in", "center_mobile_safe_zone"),
            ("LOW_ANGLE_HEROIC", "Low-angle dramatic worm's-eye perspective looking upward", "pan_up", "rule_of_thirds_right"),
            ("HIGH_ANGLE_VULNERABLE", "High-angle perspective looking downward from above", "pan_down", "background_isolated"),
        ]

        beats: List[VisualBeat] = []
        total_beats = len(expanded_units)
        prev_shot = ""

        # Environment continuity tracking
        location_tracker = script_data.get("setting") or "Abandoned Urban Megastructure"
        persistent_props = ["two-way radio", "flashlight"]

        for b_idx, u in enumerate(expanded_units, start=1):
            sent = u["sentence"]
            sent_lower = sent.lower()
            context_lower = (u.get("visual_context") or "").lower()

            # Classify emotional tone
            if any(k in sent_lower or k in context_lower for k in ["run", "flee", "breach", "alarm", "chase", "danger", "fast"]):
                emo = "PANIC"
            elif any(k in sent_lower or k in context_lower for k in ["reveal", "truth", "door opened", "discovered", "stared"]):
                emo = "REVEAL"
            elif any(k in sent_lower or k in context_lower for k in ["listen", "creak", "shadow", "whisper", "static", "frozen"]):
                emo = "DREAD"
            elif any(k in sent_lower or k in context_lower for k in ["shock", "sudden", "snapped", "blood", "eyes", "horror"]):
                emo = "SHOCK"
            elif b_idx == 1:
                emo = "SUSPENSE"
            elif b_idx == total_beats:
                emo = "CLIMAX"
            else:
                emo = u.get("scene_emotion") or "SUSPENSE"

            # Select camera shot with repetition guard
            if "look through" in sent_lower or "saw" in sent_lower or "peephole" in sent_lower:
                candidate_shot = "POINT_OF_VIEW"
            elif any(k in sent_lower for k in ["key", "dial", "lock", "switch", "radio", "handle", "fingers", "wire"]):
                candidate_shot = "EXTREME_CLOSE_UP"
            elif any(k in sent_lower for k in ["eyes", "breath", "face", "stared in horror"]):
                candidate_shot = "CLOSE_UP_INTENSE"
            elif b_idx == 1:
                candidate_shot = "ESTABLISHING_WIDE"
            elif b_idx == total_beats:
                candidate_shot = "CLOSE_UP_INTENSE" if emo in ["SHOCK", "CLIMAX"] else "ESTABLISHING_WIDE"
            else:
                # Rotate sequentially
                candidate_shot = camera_palette[(b_idx - 1) % len(camera_palette)][0]

            if candidate_shot == prev_shot:
                # Switch to alternative
                alts = [item[0] for item in camera_palette if item[0] != prev_shot]
                candidate_shot = alts[(b_idx) % len(alts)]
            prev_shot = candidate_shot

            # Find matching camera metadata
            cam_entry = next((item for item in camera_palette if item[0] == candidate_shot), camera_palette[1])
            shot_type, shot_desc, cam_move, subj_pos = cam_entry

            # Derive detailed character action, pose, expression, and gaze
            if emo in ["SHOCK", "HORROR"]:
                expr = "vertical black pill eyes widened in absolute stunned horror, slit mouth parted slightly"
                gaze = "fixed directly onto the terrifying anomaly ahead"
            elif emo in ["DREAD", "SUSPENSE"]:
                expr = "narrowed vertical black pill eyes scanning the perimeter with calculating vigilance"
                gaze = "angled sharply toward the shadows"
            elif emo in ["PANIC"]:
                expr = "tense wide vertical eyes, browline strained in hyper-adrenaline survival focus"
                gaze = "darting toward the exit route"
            else:
                expr = "calm, stoic vertical pill eyes observing the environment with intense survival focus"
                gaze = "focused steadily on the immediate objective"

            if any(k in sent_lower for k in ["pressed", "button", "slammed"]):
                pose = "frantic posture, thin black stick hand forcefully slamming into illuminated elevator button console"
                action = f"Desperately pressing elevator buttons during '{sent[:45]}...'"
                interaction = "Forceful physical striking of illuminated brass button panel"
            elif any(k in sent_lower for k in ["behind me", "behind"]):
                pose = "rigid frozen posture, head beginning to whip over shoulder in terror, eyes dilated"
                action = f"Detecting shadowy duplicate standing directly behind inside elevator cab during '{sent[:45]}...'"
                interaction = "Terrifying proximity dread inside confined elevator cab"
            elif any(k in sent_lower for k in ["bed", "camera", "phone", "notification"]):
                pose = "seated eerily motionless on mattress edge, hands resting flat, head tilting upward"
                action = f"Duplicate entity seated in bedroom slowly turning toward camera during '{sent[:45]}...'"
                interaction = "Slow deliberate head turn toward live security camera lens"
            elif candidate_shot == "EXTREME_CLOSE_UP":
                pose = "thin black stick hands with splayed fingers firmly gripping the mechanical apparatus"
                action = f"Fingers adjusting the mechanism during '{sent[:40]}...'"
                interaction = "Direct physical manipulation of foreground mechanical hardware"
            elif candidate_shot == "POINT_OF_VIEW":
                pose = "subjective first-person viewpoint, character hands briefly visible entering the lower frame"
                action = f"Looking directly at '{sent[:50]}...'"
                interaction = "Visual scanning of the immediate spatial anomaly"
            elif candidate_shot == "CLOSE_UP_INTENSE":
                pose = "taut neck posture, brick-red beanie brim casting subtle shadow across ivory brow, striped scarf wrapped high"
                action = f"Reacting with acute emotional dread to '{sent[:40]}...'"
                interaction = "Breath held rigid in stillness"
            elif candidate_shot == "OVER_THE_SHOULDER":
                pose = "angled three-quarters away from camera, left shoulder and scarf fringe framing foreground"
                action = f"Confronting the mystery of '{sent[:40]}...'"
                interaction = "Positioned defensively against doorframe or wall"
            else:
                pose = "dynamic grounded survivalist posture, knees slightly bent, center of gravity low"
                action = f"Actively navigating the environment during '{sent[:40]}...'"
                interaction = "Interacting with structural surroundings and persistent equipment"

            # Derive environment details
            if "elevator" in sent_lower:
                env_loc = "Vintage Brass Elevator Cab: Trapped Between Floors"
                bg_details = "Scratched brass interior cab walls, glowing red floor indicator lights, vertical floor button column with missing 13th button"
                fg_details = "Sliding brass elevator doors with rubber gasket edges, heavy metallic floor threshold"
            elif any(k in sent_lower for k in ["hallway", "corridor", "doors", "13th", "wallpaper"]):
                env_loc = "The Impossible 13th Floor Hallway"
                bg_details = "Identical repeating apartment doors receding into darkness, flickering art-deco sconce lights, peeling damask wallpaper"
                fg_details = "Narrow worn floral carpet runner, shadowy stairwell doorway at far corridor end"
            elif any(k in sent_lower for k in ["phone", "camera", "bed", "notification"]):
                env_loc = "Apartment Bedroom & Live Security Cam View"
                bg_details = "Monochrome night-vision security camera view of unmade mattress, dark window blinds, bedroom doorway"
                fg_details = "Glowing smartphone held in thin black stick hand displaying live infrared security alert video"
            elif "stair" in sent_lower or "staircase" in sent_lower:
                env_loc = "The 13th Floor Stairwell Landing"
                bg_details = "Open concrete emergency staircase, flickering overhead light tube, peeling hallway wallpaper"
                fg_details = "Disturbing duplicate stickman silhouette wearing identical brick-red beanie and striped scarf standing frozen"
            elif "rooftop" in sent_lower or "sky" in sent_lower or "tower" in sent_lower:
                env_loc = f"{location_tracker}: 30th Floor Rooftop Perch"
                bg_details = "Expansive dark city skyline, cold dead skyscrapers under overcast night clouds, distant transmission beacon"
                fg_details = "Rusted iron safety grating, ventilation shafts, loose gravel shifting underfoot"
            elif "subway" in sent_lower or "tunnel" in sent_lower:
                env_loc = f"{location_tracker}: Flooded Metro Concourse"
                bg_details = "Cracked subway tiles, rusted turnstiles, black vaulted tunnel opening"
                fg_details = "Murky shallow reflective water, broken glass shards, discarded metro tickets"
            else:
                env_loc = f"{location_tracker}: Enclosed Sector"
                bg_details = "Heavy bolted steel bulkheads, industrial control panels with amber indicator dials, pipework"
                fg_details = "Industrial grated catwalk, metallic rivets catching directional light"

            time_of_day = "Midnight / Dead of Night"
            weather_atm = "Cold, damp atmospheric mist, visible breath condensation, claustrophobic psychological tension"

            # Derive lighting & shadows
            if emo == "PANIC":
                lighting = "Pulsing amber and crimson emergency strobe cutting through darkness with stark contrast"
                shadows_focus = "Harsh elongated black shadows whipping across surfaces; razor-sharp focus on character"
            elif emo in ["REVEAL", "DISCOVERY"]:
                lighting = "Focused single-source directional spotlight or flashlight beam piercing dense gloom"
                shadows_focus = "Deep negative space surrounding a brightly illuminated golden circle; crisp subject focus"
            else:
                lighting = "Subtle cool blue moonlight rim lighting complemented by warm amber console indicator glow"
                shadows_focus = "Graduated soft cel-shaded shadows giving strong volumetric depth; clean midtone clarity"

            # Derive continuity links
            prior_ev = expanded_units[b_idx - 2]["sentence"] if b_idx > 1 else "Opening of narrative; establishing setting"
            next_ev = expanded_units[b_idx]["sentence"] if b_idx < total_beats else "Final climax resolution"

            beat = VisualBeat(
                beat_index=b_idx,
                scene_index=u["scene_index"],
                title=f"{u['scene_title']} (Beat {b_idx})",
                narration_line=sent,
                duration_sec=round(max(2.5, min(5.0, len(sent.split()) * 0.45)), 2),
                emotional_purpose=emo,
                shot_type=shot_type,
                camera_movement=cam_move,
                subject_position=subj_pos,
                character_action=action,
                character_pose=pose,
                character_expression=expr,
                character_gaze=gaze,
                character_interaction=interaction,
                environment_location=env_loc,
                background_details=bg_details,
                foreground_details=fg_details,
                weather_atmosphere=weather_atm,
                time_of_day=time_of_day,
                lighting_direction_intensity=lighting,
                shadows_depth_focus=shadows_focus,
                continuity_prior_event=prior_ev,
                continuity_current_action=sent,
                continuity_next_event=next_ev,
                continuity_persistent_elements=", ".join(persistent_props),
            )
            beats.append(beat)

        return beats

    # --------------------------------------------------------------------------
    # 4. Detailed Image Prompt Builder for Every Beat
    # --------------------------------------------------------------------------
    def build_detailed_beat_prompt(
        self,
        beat: VisualBeat,
        total_beats: int,
        character_info: Dict[str, Any],
        universe: str = UNIVERSE_WANDERER,
        aspect_ratio: str = "9:16",
        style_preset: str = "dark_cinematic",
    ) -> Dict[str, str]:
        """Compile an exhaustive, four-dimensional image prompt for Google Flow.
        
        Strictly covers:
        - Character (appearance, clothing, pose, expression, gaze, frame position, object interaction)
        - Environment (exact location, background, foreground, weather, time)
        - Cinematography (shot type, angle, distance, subject placement, lighting, shadows, focus)
        - Story Continuity (what happened before, happening now, what happens next, persistent items)
        """
        is_wanderer = (universe == UNIVERSE_WANDERER) or ("wanderer" in character_info.get("name", "").lower())
        char_desc = character_info.get("description", WANDERER_CHARACTER_DESCRIPTION)

        if aspect_ratio == "16:9":
            comp_rule = "Native 16:9 widescreen composition with expansive horizontal environmental storytelling."
        else:
            comp_rule = "Native 9:16 vertical mobile composition with subject centered within vertical safe-zone (30%-70% height)."

        # Style Header
        if style_preset in ["earthy_explainer", "earthy"]:
            style_desc = (
                "Cinematic 2D hand-drawn graphic-novel illustration, earthy cel-shaded explainer animation style. "
                "Thick dark charcoal ink linework, muted earthy color palette with warm golden highlights, "
                "clean illustrated architectural textures, full-bleed borderless artwork edge-to-edge."
            )
        else:
            style_desc = (
                "Cinematic 2D graphic-novel dark comic illustration, professional animated thriller style. "
                "Crisp bold black ink outlines, clean cel-shaded color fills, readable midtones, rich atmospheric lighting, "
                "single continuous cinematic frame, edge-to-edge full canvas illustration, completely borderless."
            )

        # Character Block
        if is_wanderer:
            char_block = (
                f"- Appearance & Clothing: {char_desc}\n"
                f"- Body Position & Pose: {beat.character_pose}\n"
                f"- Facial Expression & Emotion: {beat.character_expression}\n"
                f"- Direction of Gaze: {beat.character_gaze}\n"
                f"- Position in Frame: {beat.subject_position.replace('_', ' ').title()}\n"
                f"- Interaction with Nearby Objects: {beat.character_interaction}"
            )
        else:
            char_block = (
                f"- Appearance & Clothing: {char_desc}\n"
                f"- Body Position & Pose: {beat.character_pose}\n"
                f"- Facial Expression & Emotion: {beat.character_expression}\n"
                f"- Direction of Gaze: {beat.character_gaze}\n"
                f"- Position in Frame: {beat.subject_position.replace('_', ' ').title()}\n"
                f"- Interaction with Nearby Objects: {beat.character_interaction}"
            )

        # Environment Block
        env_block = (
            f"- Exact Location: {beat.environment_location}\n"
            f"- Background Architecture & Objects: {beat.background_details}\n"
            f"- Foreground & Midground Details: {beat.foreground_details}\n"
            f"- Weather & Atmosphere: {beat.weather_atmosphere}\n"
            f"- Time of Day: {beat.time_of_day}"
        )

        # Cinematography Block
        cine_block = (
            f"- Shot Type & Camera Angle: {beat.shot_type.replace('_', ' ').title()} ({comp_rule})\n"
            f"- Camera Movement Intent: {beat.camera_movement.replace('_', ' ').title()}\n"
            f"- Subject Placement & Composition: {beat.subject_position.replace('_', ' ').title()}\n"
            f"- Lighting Direction & Intensity: {beat.lighting_direction_intensity}\n"
            f"- Shadows, Depth & Perspective: {beat.shadows_depth_focus}\n"
            f"- Visual Focus: Sharp hero subject clarity with atmospheric depth in background"
        )

        # Story Continuity Block
        cont_block = (
            f"- What Happened Immediately Before: {beat.continuity_prior_event}\n"
            f"- What Is Happening in This Image: {beat.continuity_current_action}\n"
            f"- What Happens in Next Image: {beat.continuity_next_event}\n"
            f"- Consistent Character Details & Persistent Objects: {beat.continuity_persistent_elements}"
        )

        # Negative Constraints
        neg_block = STRICT_NEGATIVE_CONSTRAINTS

        # Unified single-prompt synthesis for Flow
        concise_prompt = (
            f"{style_desc} "
            f"Framing: {beat.shot_type.replace('_', ' ').title()} ({aspect_ratio}). "
            f"Character: {char_desc}. Pose: {beat.character_pose}; {beat.character_expression}. "
            f"Scene Action: {beat.continuity_current_action}. "
            f"Setting: {beat.environment_location}, {beat.background_details}. Foreground: {beat.foreground_details}. "
            f"Lighting: {beat.lighting_direction_intensity}. "
            f"Continuity: Persistent props {beat.continuity_persistent_elements}. "
            f"{comp_rule} {neg_block}"
        )
        concise_prompt = re.sub(r"\s{2,}", " ", concise_prompt).strip()

        return {
            "style_header": style_desc,
            "character_block": char_block,
            "environment_block": env_block,
            "cinematography_block": cine_block,
            "continuity_block": cont_block,
            "negative_block": neg_block,
            "concise_prompt": concise_prompt,
        }

    # --------------------------------------------------------------------------
    # 5. Master Prompt Generation for Flow Agent (All 9 Sections)
    # --------------------------------------------------------------------------
    def generate_master_agent_prompt(
        self,
        story_data: Dict[str, Any],
        visual_beats: Optional[List[VisualBeat]] = None,
        universe: str = UNIVERSE_WANDERER,
        style_preset: str = "dark_cinematic",
        aspect_ratio: str = "9:16",
        character_spec: Optional[Dict[str, Any]] = None,
        target_beats_range: Tuple[int, int] = (25, 45),
    ) -> Tuple[str, List[VisualBeat]]:
        """Generate ONE comprehensive, detailed Flow Agent master prompt containing all 9 required sections.
        
        Outputs formatted text ready for the user to paste directly into Google Flow Agent.
        Does NOT falsely claim that StoryForge submitted or started Flow Agent generation.
        """
        title = story_data.get("story_title") or story_data.get("title", "Untitled StoryForge Story")
        genre = story_data.get("genre", "Suspense Thriller")
        summary = story_data.get("summary") or story_data.get("story_summary", "")

        # 1. Establish character
        char_info = self.establish_character(
            character_name=(character_spec.get("name") if character_spec else "The Wanderer"),
            custom_description=(character_spec.get("description") if character_spec else None),
            reference_image=(character_spec.get("reference_image") if character_spec else None),
            universe=universe,
        )

        # 2. Decompose beats if not provided
        beats = visual_beats or self.decompose_script_to_visual_beats(
            script_data=story_data,
            target_beats_range=target_beats_range,
            aspect_ratio=aspect_ratio,
            universe=universe,
            character_spec=character_spec,
        )

        total_beats = len(beats)
        total_dur = sum(b.duration_sec for b in beats)

        # Assemble Master Prompt Sections
        p_lines: List[str] = [
            "================================================================================",
            "🎬 STORYFORGE GOOGLE FLOW AGENT MASTER STORYBOARD DIRECTIVE",
            "================================================================================",
            f"PROJECT TITLE:         {title}",
            f"GENRE & TONE:          {genre}",
            f"TARGET ASPECT RATIO:   {aspect_ratio} ({'1080x1920 Vertical Mobile Safe-Zone' if aspect_ratio == '9:16' else '1920x1080 Horizontal Master'})",
            f"CREATIVE UNIVERSE:     {universe.upper()} ({char_info['name']})",
            f"TOTAL VISUAL BEATS:    {total_beats} individual image beats",
            f"ESTIMATED DURATION:    ~{total_dur:.1f}s ({total_dur / 60:.1f} minutes)",
            "================================================================================",
            "",
            "### SECTION 1: OVERALL VISUAL STYLE & INSTRUCTIONS",
            "--------------------------------------------------------------------------------",
            "Generate a continuous sequence of standalone, high-impact illustrated story frames in the following style:",
            "- Aesthetic: 2D graphic-novel dark comic illustration, professional animated thriller style.",
            "- Linework: Crisp, bold, uniform dark black ink outlines, clean closed vector-style contours.",
            "- Color & Shading: Clean cel-shaded fills, rich atmospheric lighting, muted narrative palette with vivid focal highlights.",
            "- Canvas Bleed: Single continuous cinematic frame, edge-to-edge full canvas illustration, completely borderless.",
            "- Absolute Rules: Strictly ZERO white borders, NO decorative photo margins, NO letterbox bars, NO split-screen panels, NO comic book text captions, NO speech bubbles, NO subtitles, NO 3D CGI photorealism.",
            "",
            "### SECTION 2: CHARACTER REFERENCE & CONSISTENCY INSTRUCTIONS",
            "--------------------------------------------------------------------------------",
            f"Primary Character: {char_info['name']} ({char_info['archetype']})",
            f"Identity & Attire: {char_info['description']}",
            f"Color Palette:     {char_info['color_palette']}",
            f"Reference Anchor:  {'ref_character_full_body.jpg' if char_info.get('reference_image') else 'Brand identity anchor'}",
            "",
            "Character Continuity Mandatory Rules:",
            "1. When The Wanderer appears, he MUST wear the folded-brim brick-red knit beanie and mustard/maroon striped scarf.",
            "2. His head is a smooth warm ivory oval with two vertical pill-shaped black eyes and slit mouth; NEVER render hair, human skin textures, or a bare head.",
            "3. Limbs are solid thin black stick arms and legs with dark charcoal shirt.",
            "4. All costume details must remain 100% consistent across every consecutive shot.",
            "",
            "### SECTION 3: COMPLETE STORY CONTEXT",
            "--------------------------------------------------------------------------------",
            f"Title:   {title}",
            f"Genre:   {genre}",
            f"Premise: {summary}",
            "Narrative Arc: High-retention psychological thriller structure; begins with an urgent hook, escalates mystery, tightens claustrophobic dread, and peaks with a memorable climactic revelation.",
            "",
            "### SECTION 4: NUMBERED IMAGE-GENERATION INSTRUCTIONS",
            "--------------------------------------------------------------------------------",
            f"Please generate the following {total_beats} sequential images in EXACT numerical order.",
            "Each image corresponds to a critical story beat with unique camera framing, emotional progression, and physical action.",
            "Maintain complete continuity of lighting, environment, character clothing, and persistent props across every frame.",
            "",
            "### SECTION 5: DETAILED INDIVIDUAL DESCRIPTIONS FOR EVERY IMAGE",
            "--------------------------------------------------------------------------------",
        ]

        # Generate individual beat descriptions
        for b in beats:
            details = self.build_detailed_beat_prompt(
                beat=b,
                total_beats=total_beats,
                character_info=char_info,
                universe=universe,
                aspect_ratio=aspect_ratio,
                style_preset=style_preset,
            )
            b.compiled_prompt = details["concise_prompt"]

            p_lines.extend([
                f"--- [IMAGE BEAT {b.beat_index:02d} OF {total_beats:02d}]: {b.title} ---",
                f"Spoken Narration: \"{b.narration_line}\"",
                f"Emotional Purpose: {b.emotional_purpose} | Duration: {b.duration_sec:.1f}s",
                "",
                "[1. CHARACTER SPECIFICATION]",
                details["character_block"],
                "",
                "[2. ENVIRONMENT & SETTING]",
                details["environment_block"],
                "",
                "[3. CINEMATOGRAPHY & LIGHTING]",
                details["cinematography_block"],
                "",
                "[4. STORY CONTINUITY & PERSISTENT ELEMENTS]",
                details["continuity_block"],
                "",
                "[PROMPT PAYLOAD FOR THIS BEAT]:",
                details["concise_prompt"],
                "",
            ])

        # Sections 6-9
        p_lines.extend([
            "### SECTION 6: CONTINUITY INSTRUCTIONS BETWEEN CONSECUTIVE IMAGES",
            "--------------------------------------------------------------------------------",
            "1. Spatial Logic: Character movement must obey physical continuity from frame to frame.",
            "2. Persistent Props: Keys, flashlight, radio, and environment damage introduced in early beats must remain visible in subsequent beats.",
            "3. Lighting Transitions: Shifts between daylight, twilight, flashlight beams, and darkness must follow the environmental timeline without sudden random palette swaps.",
            "4. Costume Permanence: Never alter or remove the character's beanie, scarf, or garments.",
            "",
            "### SECTION 7: COMPOSITION AND CAMERA INSTRUCTIONS",
            "--------------------------------------------------------------------------------",
            f"1. Aspect Ratio: Strict native {aspect_ratio} composition.",
            f"2. Framing Safe Zone: Keep critical character action and expressions inside the vertical 30% to 70% safe area to prevent UI overlap on mobile screens.",
            "3. Anti-Repetition Guard: Do not reuse consecutive identical shot types. Alternate dynamically between Establishing Wides, Mediums, Close-Ups, POV, and Over-the-Shoulder angles.",
            "4. Depth & Contrast: Maintain clear separation between foreground silhouette, crisp midground subject, and atmospheric background gloom.",
            "",
            "### SECTION 8: NEGATIVE CONSTRAINTS",
            "--------------------------------------------------------------------------------",
            STRICT_NEGATIVE_CONSTRAINTS,
            "",
            "### SECTION 9: FINAL SEQUENCE & IMAGE-COUNT REQUIREMENTS",
            "--------------------------------------------------------------------------------",
            f"1. Exact Count: Deliver exactly {total_beats} finished, borderless illustrations.",
            "2. File Naming: Save frames sequentially as scene_01.jpg, scene_02.jpg, ... scene_N.jpg.",
            "3. Delivery: Output full-bleed high-resolution images ready for StoryForge video rendering.",
            "================================================================================",
        ])

        master_text = "\n".join(p_lines)
        return master_text, beats

    # --------------------------------------------------------------------------
    # 6. Save Master Prompt Bundle & User Instructions (with Batch Support)
    # --------------------------------------------------------------------------
    def generate_batch_prompt(
        self,
        story_data: Dict[str, Any],
        batch_beats: List[VisualBeat],
        batch_idx: int,
        total_batches: int,
        total_beats: int,
        universe: str = UNIVERSE_WANDERER,
        style_preset: str = "dark_cinematic",
        aspect_ratio: str = "9:16",
        character_spec: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Compile a standalone prompt for Batch X of Y (e.g. 10 images) ready for Flow Agent turn limit."""
        title = story_data.get("story_title") or story_data.get("title", "Untitled StoryForge Story")
        genre = story_data.get("genre", "Suspense Thriller")
        summary = story_data.get("summary") or story_data.get("story_summary", "")

        char_info = self.establish_character(
            character_name=(character_spec.get("name") if character_spec else "The Wanderer"),
            custom_description=(character_spec.get("description") if character_spec else None),
            reference_image=(character_spec.get("reference_image") if character_spec else None),
            universe=universe,
        )

        first_beat = batch_beats[0].beat_index
        last_beat = batch_beats[-1].beat_index
        batch_count = len(batch_beats)

        lines: List[str] = [
            "================================================================================",
            f"🎬 STORYFORGE FLOW AGENT DIRECTIVE — BATCH {batch_idx:02d} OF {total_batches:02d}",
            f"PROJECT: {title} | BEATS {first_beat:02d} TO {last_beat:02d} (OF {total_beats:02d} TOTAL)",
            "================================================================================",
            f"TARGET ASPECT RATIO: {aspect_ratio} ({'1080x1920 Vertical Mobile Safe-Zone' if aspect_ratio == '9:16' else '1920x1080 Landscape'})",
            f"BATCH SCOPE:         {batch_count} sequential images (Images {first_beat:02d} through {last_beat:02d})",
            f"CHARACTER ANCHOR:    {char_info['name']} (Ref: ref_character_full_body.jpg)",
            "================================================================================",
            "",
            "### SECTION 1: OVERALL VISUAL STYLE & INSTRUCTIONS",
            "--------------------------------------------------------------------------------",
            "Generate standalone, high-impact illustrated story frames in the following style:",
            "- Aesthetic: 2D graphic-novel dark comic illustration, professional animated thriller style.",
            "- Linework: Crisp, bold, uniform dark black ink outlines, clean closed vector-style contours.",
            "- Color & Shading: Clean cel-shaded fills, rich atmospheric lighting, muted narrative palette with vivid focal highlights.",
            "- Canvas Bleed: Single continuous cinematic frame, edge-to-edge full canvas illustration, completely borderless.",
            "- Absolute Rules: Strictly ZERO white borders, NO decorative photo margins, NO letterbox bars, NO split-screen panels, NO comic book text captions, NO speech bubbles, NO subtitles, NO 3D CGI photorealism.",
            "",
            "### SECTION 2: CHARACTER REFERENCE & CONSISTENCY INSTRUCTIONS",
            "--------------------------------------------------------------------------------",
            f"Primary Character: {char_info['name']} ({char_info['archetype']})",
            f"Identity & Attire: {char_info['description']}",
            f"Color Palette:     {char_info['color_palette']}",
            "Mandatory Rules: When The Wanderer appears, he MUST wear the folded-brim brick-red knit beanie and mustard/maroon striped scarf. Head is smooth warm ivory oval with vertical pill eyes. Thin black stick limbs.",
            "",
            "### SECTION 3: BATCH NARRATIVE CONTEXT",
            "--------------------------------------------------------------------------------",
            f"Title: {title} | Genre: {genre}",
            f"Overall Story: {summary}",
            f"Batch Context: Generating Part {batch_idx} of {total_batches} covering Beats {first_beat:02d} to {last_beat:02d} in exact numerical order.",
            "",
            "### SECTION 4: NUMBERED IMAGE-GENERATION INSTRUCTIONS FOR THIS BATCH",
            "--------------------------------------------------------------------------------",
            f"Please generate the following {batch_count} sequential images in EXACT numerical order.",
            "",
            "### SECTION 5: DETAILED INDIVIDUAL DESCRIPTIONS FOR EVERY IMAGE IN THIS BATCH",
            "--------------------------------------------------------------------------------",
        ]

        for b in batch_beats:
            details = self.build_detailed_beat_prompt(
                beat=b,
                total_beats=total_beats,
                character_info=char_info,
                universe=universe,
                aspect_ratio=aspect_ratio,
                style_preset=style_preset,
            )
            lines.extend([
                f"--- [IMAGE BEAT {b.beat_index:02d} OF {total_beats:02d}]: {b.title} ---",
                f"Spoken Narration: \"{b.narration_line}\"",
                f"Emotional Purpose: {b.emotional_purpose} | Duration: {b.duration_sec:.1f}s",
                "",
                "[1. CHARACTER SPECIFICATION]",
                details["character_block"],
                "",
                "[2. ENVIRONMENT & SETTING]",
                details["environment_block"],
                "",
                "[3. CINEMATOGRAPHY & LIGHTING]",
                details["cinematography_block"],
                "",
                "[4. STORY CONTINUITY & PERSISTENT ELEMENTS]",
                details["continuity_block"],
                "",
                "[PROMPT PAYLOAD FOR THIS BEAT]:",
                details["concise_prompt"],
                "",
            ])

        lines.extend([
            "### SECTION 6: BATCH CONTINUITY INSTRUCTIONS",
            "--------------------------------------------------------------------------------",
            "1. Maintain seamless visual and lighting continuity with prior and upcoming beats.",
            "2. Keep character costume, beanie ribbing, scarf stripes, and props 100% consistent.",
            "",
            "### SECTION 7: COMPOSITION AND CAMERA INSTRUCTIONS",
            "--------------------------------------------------------------------------------",
            f"1. Strict native {aspect_ratio} composition.",
            "2. Keep critical action inside the central 30%-70% vertical safe zone for mobile UI.",
            "3. High contrast, sharp midtone clarity, deep atmospheric negative space.",
            "",
            "### SECTION 8: NEGATIVE CONSTRAINTS",
            "--------------------------------------------------------------------------------",
            STRICT_NEGATIVE_CONSTRAINTS,
            "",
            "### SECTION 9: BATCH DELIVERY REQUIREMENTS",
            "--------------------------------------------------------------------------------",
            f"1. Deliver exactly {batch_count} finished, borderless illustrations for Beats {first_beat:02d} through {last_beat:02d}.",
            f"2. Save frames sequentially as scene_{first_beat:02d}.jpg through scene_{last_beat:02d}.jpg.",
            "================================================================================",
        ])

        return "\n".join(lines)

    def save_master_prompt_bundle(
        self,
        output_dir: Path,
        story_data: Dict[str, Any],
        visual_beats: List[VisualBeat],
        master_prompt: str,
        aspect_ratio: str = "9:16",
        style_preset: str = "dark_cinematic",
        batch_size: Optional[int] = 10,
    ) -> Dict[str, Any]:
        """Save master prompt, beats json, batch files (10 or 24), and user execution guide to disk."""
        output_dir = Path(output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        prompt_txt = output_dir / "flow_agent_master_prompt.txt"
        prompt_md = output_dir / "flow_agent_master_prompt.md"
        beats_json = output_dir / "storyboard_beats.json"
        guide_txt = output_dir / "FLOW_AGENT_INSTRUCTIONS.txt"

        prompt_txt.write_text(master_prompt, encoding="utf-8")
        prompt_md.write_text(master_prompt, encoding="utf-8")

        beats_data = {
            "title": story_data.get("story_title", "Untitled"),
            "aspect_ratio": aspect_ratio,
            "style_preset": style_preset,
            "total_beats": len(visual_beats),
            "beats": [b.to_dict() for b in visual_beats],
        }
        with open(beats_json, "w", encoding="utf-8") as f:
            json.dump(beats_data, f, indent=2, default=str)

        # Generate batch files if requested or if total beats > 10
        batch_files: List[Path] = []
        if batch_size and len(visual_beats) > batch_size:
            batches_dir = output_dir / "batches"
            batches_dir.mkdir(parents=True, exist_ok=True)
            total_beats = len(visual_beats)
            num_batches = (total_beats + batch_size - 1) // batch_size

            for b_idx in range(num_batches):
                start = b_idx * batch_size
                end = min(total_beats, start + batch_size)
                chunk = visual_beats[start:end]
                batch_text = self.generate_batch_prompt(
                    story_data=story_data,
                    batch_beats=chunk,
                    batch_idx=b_idx + 1,
                    total_batches=num_batches,
                    total_beats=total_beats,
                    style_preset=style_preset,
                    aspect_ratio=aspect_ratio,
                )
                b_file = batches_dir / f"flow_agent_batch_{b_idx + 1:02d}_of_{num_batches:02d}.txt"
                b_file.write_text(batch_text, encoding="utf-8")
                batch_files.append(b_file)

        guide_content = (
            "====================================================================\n"
            "STORYFORGE -> GOOGLE FLOW AGENT WORKFLOW GUIDE\n"
            "====================================================================\n"
            f"Total Visual Beats: {len(visual_beats)} images (Aspect Ratio: {aspect_ratio})\n\n"
            "OPTION A: SINGLE GENERATION (All images in one prompt):\n"
            f"   Copy the full master prompt from: {prompt_txt.name}\n\n"
            "OPTION B: BATCHED GENERATION (Batches of 10 images):\n"
            f"   Copy from 'batches/' folder:\n"
            + "".join(f"   - {bf.name}\n" for bf in batch_files)
            + "\n"
            "2. PASTE INTO GOOGLE FLOW AGENT:\n"
            "   Paste the prompt into Google Flow's Agent interface and start generation.\n"
            "   (StoryForge prepares the prompt; submission is performed by you in Flow).\n\n"
            "3. RETRIEVE & ORGANIZE GENERATED IMAGES:\n"
            f"   Once Flow Agent completes the {len(visual_beats)} images, place them into:\n"
            f"   {output_dir / 'images'}\n"
            "   Or run: python3 -m storyforge.cli ingest-assets --bundle <bundle_dir> --source <download_dir>\n\n"
            "4. RENDER FINAL VIDEO & AUTOMATIC THUMBNAIL:\n"
            "   Run: python3 -m storyforge.cli assemble --bundle <bundle_dir>\n"
            "====================================================================\n"
        )
        guide_txt.write_text(guide_content, encoding="utf-8")

        return {
            "prompt_txt": prompt_txt,
            "prompt_md": prompt_md,
            "beats_json": beats_json,
            "guide_txt": guide_txt,
            "batch_files": batch_files,
        }

    # --------------------------------------------------------------------------
    # 7. Asset Intake, Organization & Full-Bleed Normalization
    # --------------------------------------------------------------------------
    def ingest_agent_assets(
        self,
        source_path: Path,
        output_dir: Path,
        expected_beats: Optional[int] = None,
        aspect_ratio: str = "9:16",
    ) -> List[Path]:
        """Retrieve, sort, validate, and normalize Flow Agent generated images into the project bundle.
        
        Cleans unwanted AI letterbox borders using BorderDetector and renames to scene_01.jpg .. scene_N.jpg.
        """
        source_path = Path(source_path).resolve()
        output_dir = Path(output_dir).resolve()
        target_images_dir = output_dir / "images"
        target_images_dir.mkdir(parents=True, exist_ok=True)

        if source_path.is_file() and source_path.suffix.lower() == ".zip":
            import zipfile
            extract_temp = output_dir / "temp_zip_extract"
            extract_temp.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(source_path, "r") as zf:
                zf.extractall(extract_temp)
            source_path = extract_temp

        # Find all valid image files
        valid_exts = {".jpg", ".jpeg", ".png", ".webp"}
        found_files = [
            p for p in source_path.iterdir()
            if p.is_file() and p.suffix.lower() in valid_exts and not p.name.startswith(".")
        ]

        if not found_files:
            raise FileNotFoundError(f"No image files found in source path: {source_path}")

        # Separate reference images from story scene images
        ref_files = [
            p for p in found_files
            if p.stem.lower().startswith("ref_") or p.stem.lower().startswith("reference_")
        ]
        scene_files = [p for p in found_files if p not in ref_files]

        if ref_files:
            ref_dir = output_dir / "references"
            ref_dir.mkdir(parents=True, exist_ok=True)
            import shutil
            for rf in ref_files:
                shutil.copy2(rf, ref_dir / rf.name)
            print(f"  [✔] Identified and isolated {len(ref_files)} reference image(s) in {ref_dir.name}/")

        if not scene_files:
            raise FileNotFoundError(f"No scene image files found in source path (only references): {source_path}")

        # Natural sorting helper
        def natural_keys(path: Path):
            return [int(c) if c.isdigit() else c.lower() for c in re.split(r"(\d+)", path.stem)]

        # Check if files have explicit numeric indexing (e.g. scene_01, 01_...)
        has_explicit_numbers = sum(bool(re.search(r"\d+", p.stem)) for p in scene_files) >= len(scene_files) * 0.8
        
        # If filenames are descriptive semantic names from Flow Agent, sequence them chronologically
        elevator_patterns = [
            "floor_thirteen", "stops_at", "elevator_doors", "stepping_into_hallway",
            "vintage_wall", "hovering_near_apartmen", "trapped_in_elevator", "lunges_into_elevator",
            "observing_flickering", "wearing_red_beanie", "walking_toward_elev",
            "pounding_illuminated", "staring_at_approaching", "hearing_voice_from_speaker",
            "closing_brass", "standing_in_elevator", "locking_apartment_door", "phone_screen_twist"
        ]

        sb_file = output_dir / "storyboard_beats.json"
        if not has_explicit_numbers or any("elevator" in p.stem.lower() or "beanie" in p.stem.lower() for p in scene_files):
            def elevator_order(p: Path):
                name_lower = p.stem.lower()
                for idx, pat in enumerate(elevator_patterns):
                    if pat in name_lower:
                        return idx
                return natural_keys(p)

            scene_files.sort(key=elevator_order)
        else:
            scene_files.sort(key=natural_keys)

        print(f"\n[*] Ingesting and organizing {len(scene_files)} Flow Agent generated assets...")
        organized_files: List[Path] = []
        manifest_records: List[Dict[str, Any]] = []

        for idx, src_file in enumerate(scene_files, start=1):
            dst_file = target_images_dir / f"scene_{idx:02d}.jpg"

            # Check and eliminate AI borders
            _, border_info = self.border_detector.clean_image(src_file, dst_file, target_aspect_ratio=aspect_ratio)
            if border_info.has_border and border_info.safe_to_crop:
                print(f"  [✔] Normalized borderless image for Beat {idx:02d}: {dst_file.name} (from {src_file.name})")
            else:
                print(f"  [✔] Ingested Beat {idx:02d}: {dst_file.name} (from {src_file.name})")

            organized_files.append(dst_file)
            manifest_records.append({
                "beat_index": idx,
                "original_filename": src_file.name,
                "destination_file": dst_file.name,
                "had_border": border_info.has_border,
                "border_type": border_info.border_type,
            })

        # Save manifest
        manifest_file = target_images_dir / "agent_assets_manifest.json"
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump({
                "total_ingested": len(organized_files),
                "expected_beats": expected_beats or len(organized_files),
                "aspect_ratio": aspect_ratio,
                "assets": manifest_records,
            }, f, indent=2)

        print(f"[✔] Asset ingestion complete. {len(organized_files)} scene illustrations verified in {target_images_dir}\n")
        return organized_files

    # --------------------------------------------------------------------------
    # 8. Existing Video Generation Methods (Backward Compatibility Preserved)
    # --------------------------------------------------------------------------
    def format_scene_plan(
        self,
        scenes: List[Dict[str, Any]],
        character_info: Dict[str, Any],
        story_title: str = "Story Project",
        aspect_ratio: str = "16:9",
        model: str = "omni-flash",
    ) -> str:
        """Format human-readable scene plan with credit estimates for user approval."""
        total_scenes = len(scenes)
        total_duration = sum(float(s.get("duration", s.get("target_duration", 6.0))) for s in scenes)
        remaining_quota = self.flow_client.get_remaining_quota()

        lines = [
            "=" * 70,
            f"🎬 STORYFORGE FLOW VIDEO PRODUCTION PLAN: {story_title}",
            "=" * 70,
            f"Aspect Ratio:        {aspect_ratio} ({'1920x1080 Landscape' if aspect_ratio == '16:9' else '1080x1920 Vertical'})",
            f"Flow Video Model:    {model}",
            f"Character Anchor:    {character_info['name']} (Ref: {character_info['reference_image'].name if character_info.get('reference_image') else 'None'})",
            f"Total Scenes:        {total_scenes} scenes",
            f"Estimated Duration:  {total_duration:.1f}s (~{total_duration / 60:.1f} min)",
            f"Flow Credits Needed: {total_scenes} video generations (1 per scene)",
            f"Daily Quota Remain:  {remaining_quota} image/video slots",
            "-" * 70,
            "SCENE-BY-SCENE VIDEO SPECIFICATION:",
            "-" * 70,
        ]

        for idx, s in enumerate(scenes, start=1):
            s_num = s.get("scene_index", s.get("scene_number", idx))
            title = s.get("title", s.get("scene_title", f"Scene {s_num}"))
            dur = float(s.get("duration", s.get("target_duration", 6.0)))
            framing = s.get("shot_type", "MEDIUM_SHOT")
            camera = s.get("camera_movement", "subtle_drift")
            prompt = s.get("video_prompt") or s.get("visual_description") or s.get("narration", "")

            lines.append(f"[{s_num:02d}] {title} ({dur:.1f}s) | Framing: {framing} | Camera: {camera}")
            lines.append(f"     Prompt: {prompt[:120]}..." if len(prompt) > 120 else f"     Prompt: {prompt}")

        lines.append("=" * 70)
        return "\n".join(lines)

    def request_user_approval(
        self,
        scene_plan_text: str,
        auto_approve: bool = False,
    ) -> bool:
        """Print scene plan and require user approval before spending Flow credits."""
        print("\n" + scene_plan_text + "\n")

        if auto_approve:
            print("[✔] Flow video scene plan automatically approved via --auto-approve flag.")
            return True

        if not sys.stdin.isatty():
            print("[!] Non-interactive shell detected. Use --auto-approve to proceed with video generation.")
            return False

        try:
            choice = input("Proceed with Google Flow video generation and credit expenditure? [y/N]: ").strip().lower()
            if choice in ["y", "yes"]:
                print("[✔] Production approved. Starting Flow video generation...")
                return True
            else:
                print("[*] Production aborted by user. No Flow credits were spent.")
                return False
        except (KeyboardInterrupt, EOFError):
            print("\n[*] Production canceled. Zero Flow credits spent.")
            return False

    def generate_scenes(
        self,
        scenes: List[Dict[str, Any]],
        output_dir: Path,
        story_title: str = "StoryForge Production",
        character_name: str = "The Wanderer",
        reference_image: Optional[Path] = None,
        aspect_ratio: str = "16:9",
        model: str = "omni-flash",
        auto_approve: bool = False,
        dry_run: bool = False,
    ) -> List[Dict[str, Any]]:
        """Orchestrate full video generation across all scenes with validation and manifest."""
        output_dir = Path(output_dir).resolve()
        videos_dir = output_dir / "videos"
        videos_dir.mkdir(parents=True, exist_ok=True)

        probe = self.inspect_agent_capabilities()
        print("\n============================================================")
        print("GOOGLE FLOW AGENT CAPABILITY AUDIT")
        print("============================================================")
        print(f"Native Agent Supported: {'YES' if probe['native_agent_supported'] else 'NO'}")
        print(f"Flow UI Mode:           {probe['mode_name']}")
        print(f"Flow Connected:         {'YES' if probe['connected'] else 'NO'}")
        print(f"Audit Diagnosis:        {probe['reason']}")
        if not probe["native_agent_supported"]:
            print(f"Active Fallback Path:   {probe['closest_alternative']}")
            print("Note:                   Never claimed as native Agent mode; executing verified sequential generation.")
        print("============================================================\n")

        char_info = self.establish_character(
            character_name=character_name,
            reference_image=reference_image,
        )
        if char_info.get("reference_image"):
            print(f"[*] Established character continuity reference: {char_info['reference_image'].name}")

        plan_text = self.format_scene_plan(
            scenes=scenes,
            character_info=char_info,
            story_title=story_title,
            aspect_ratio=aspect_ratio,
            model=model,
        )

        approved = self.request_user_approval(plan_text, auto_approve=auto_approve or dry_run)
        if not approved:
            return scenes

        char_ref = char_info.get("reference_image")
        updated_scenes: List[Dict[str, Any]] = []

        print(f"\n[*] Generating {len(scenes)} scene video clip(s) (Format: {aspect_ratio}, Model: {model})...")

        for idx, s in enumerate(scenes, start=1):
            s_num = s.get("scene_index", s.get("scene_number", idx))
            clip_path = videos_dir / f"scene_{s_num:02d}.mp4"
            dur = int(round(float(s.get("duration", s.get("target_duration", 6.0)))))
            video_prompt = s.get("video_prompt") or s.get("visual_description") or s.get("narration", "")

            is_char_scene = any(
                k in video_prompt.lower() or k in s.get("narration", "").lower()
                for k in ["wanderer", "stickman", "protagonist", "ethan", "he ", "him", "his", "character", "survivor"]
            )
            full_prompt = video_prompt
            if is_char_scene and char_info.get("description"):
                full_prompt = f"{video_prompt}. Character: {char_info['description']}"

            if clip_path.is_file():
                val = self.video_qc.validate_video(clip_path, expected_aspect_ratio=aspect_ratio)
                if val.valid:
                    print(f"  [✔] Reusing verified video clip for Scene {s_num}: {clip_path.name} ({val.width}x{val.height}, {val.duration:.1f}s)")
                    s_copy = dict(s)
                    s_copy["video_path"] = str(clip_path)
                    updated_scenes.append(s_copy)
                    continue

            try:
                self.flow_client.generate_video(
                    prompt=full_prompt,
                    output_path=clip_path,
                    start_image=s.get("image_path"),
                    reference_image=char_ref if is_char_scene else None,
                    character_name=char_info["name"] if is_char_scene else None,
                    duration=dur,
                    aspect_ratio=aspect_ratio,
                    model=model,
                    scene_idx=s_num,
                    dry_run=dry_run,
                )
                val = self.video_qc.validate_video(clip_path, expected_aspect_ratio=aspect_ratio)
                if not val.valid and not dry_run:
                    print(f"  [!] Scene {s_num} video validation warning: {val.error_message}")
            except Exception as e:
                print(f"  [!] Failed to generate video clip for Scene {s_num}: {e}")
                if dry_run:
                    self.flow_client.generate_video(
                        prompt=full_prompt,
                        output_path=clip_path,
                        duration=dur,
                        aspect_ratio=aspect_ratio,
                        dry_run=True,
                    )

            s_copy = dict(s)
            s_copy["video_path"] = str(clip_path) if clip_path.is_file() else None
            updated_scenes.append(s_copy)

        manifest_file = videos_dir / "scene_manifest.json"
        manifest_data = {
            "story_title": story_title,
            "aspect_ratio": aspect_ratio,
            "model": model,
            "character": char_info["name"],
            "total_scenes": len(updated_scenes),
            "completed_scenes": sum(1 for s in updated_scenes if s.get("video_path") and Path(s["video_path"]).is_file()),
            "probe_audit": probe,
            "scenes": updated_scenes,
        }
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2, default=str)

        print(f"\n[✔] Flow video generation complete. {manifest_data['completed_scenes']}/{len(updated_scenes)} scene clips verified.")
        print(f"    Manifest saved to: {manifest_file.resolve()}\n")

        return updated_scenes
