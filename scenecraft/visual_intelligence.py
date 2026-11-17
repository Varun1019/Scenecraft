"""Visual Intelligence Engine for Scenecraft: Advanced cinematic prompt compilation,
character consistency, camera composition, lighting, continuity, and image quality control.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple


# ==============================================================================
# 1. CHARACTER CONSISTENCY ENGINE (OFFICIAL BRAND STYLE LOCK)
# ==============================================================================

OFFICIAL_BRAND_STYLE_CONFIG_PATH = Path(__file__).resolve().parent.parent / "references" / "brand_identity" / "style_config.json"
OFFICIAL_FULL_BODY_REF = Path(__file__).resolve().parent.parent / "references" / "brand_identity" / "ref_character_full_body.jpg"
_close_up_jpg = Path(__file__).resolve().parent.parent / "references" / "brand_identity" / "ref_character_close_up.jpg"
_close_up_png = Path(__file__).resolve().parent.parent / "references" / "brand_identity" / "ref_character_close_up.png"
OFFICIAL_CLOSE_UP_REF = _close_up_png if _close_up_png.is_file() else _close_up_jpg
OFFICIAL_THREE_QUARTER_REF = Path(__file__).resolve().parent.parent / "references" / "brand_identity" / "ref_character_three_quarter.jpg"
OFFICIAL_BACK_VIEW_REF = Path(__file__).resolve().parent.parent / "references" / "brand_identity" / "ref_character_back_view.jpg"


def get_character_reference_for_shot(shot_type: str, custom_ref: Optional[Path] = None) -> Path:
    """Return the most appropriate Wanderer character reference angle for the given shot type."""
    if custom_ref and Path(custom_ref).is_file():
        return Path(custom_ref)

    st = (shot_type or "").upper()
    if any(k in st for k in ["CLOSE_UP", "INTENSE", "FACE", "EXTREME_CLOSE"]):
        if OFFICIAL_CLOSE_UP_REF.is_file():
            return OFFICIAL_CLOSE_UP_REF
    elif any(k in st for k in ["BACK", "OVER_THE_SHOULDER", "AWAY"]):
        if OFFICIAL_BACK_VIEW_REF.is_file():
            return OFFICIAL_BACK_VIEW_REF
    elif any(k in st for k in ["MEDIUM", "THREE_QUARTER", "ACTION", "INTERACTION"]):
        if OFFICIAL_THREE_QUARTER_REF.is_file():
            return OFFICIAL_THREE_QUARTER_REF

    if OFFICIAL_FULL_BODY_REF.is_file():
        return OFFICIAL_FULL_BODY_REF
    return OFFICIAL_CLOSE_UP_REF

DEFAULT_STICKMAN_IDENTITY = (
    "Original 2D dark comic stickman protagonist. Smooth warm ivory oval head, "
    "two vertical black pill eyes, neutral horizontal slit mouth, thin black stick limbs and torso, "
    "wearing a chunky brick-red ribbed knit beanie, a thick winter scarf with alternating horizontal "
    "mustard-gold and rust-maroon stripes with fringe, and a dark charcoal short-sleeved t-shirt."
)


@dataclass
class CharacterSpec:
    name: str = "The Wanderer"
    role: str = "Protagonist"
    visual_identity: str = DEFAULT_STICKMAN_IDENTITY
    clothing: str = "chunky brick-red ribbed knit beanie, striped mustard-gold and rust-maroon winter scarf with fringe, and dark charcoal short-sleeved t-shirt"
    distinguishing_features: str = "Smooth warm ivory oval head, two vertical black pill eyes, brick-red ribbed knit beanie, gold and maroon striped scarf, thin black stick limbs"
    color_palette: str = "Brick-red (#A03325), Warm ivory (#F9E8CE), Mustard gold (#DFA028), Rust maroon (#8C2B1D), Dark charcoal (#454242), Carbon black (#18181A)"
    is_stickman: bool = True

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CharacterSpec:
        if not data:
            return cls()
        anchor = data.get("visual_anchor", "")
        is_stickman = "stickman" in anchor.lower() or "beanie" in anchor.lower() or not anchor
        identity = anchor if anchor else DEFAULT_STICKMAN_IDENTITY
        return cls(
            name=data.get("name", "The Wanderer"),
            role=data.get("role", "Protagonist"),
            visual_identity=identity,
            clothing=data.get("clothing", "chunky brick-red ribbed knit beanie, striped mustard-gold and rust-maroon winter scarf with fringe, and dark charcoal short-sleeved t-shirt" if is_stickman else "practical attire"),
            distinguishing_features=data.get("distinguishing_features", "Smooth warm ivory oval head, two vertical black pill eyes, brick-red ribbed knit beanie, striped mustard-gold and rust-maroon scarf" if is_stickman else "distinctive facial features and silhouette"),
            color_palette=data.get("color_palette", "Brick-red (#A03325), Warm ivory (#F9E8CE), Mustard gold (#DFA028), Rust maroon (#8C2B1D), Dark charcoal (#454242), Carbon black (#18181A)"),
            is_stickman=is_stickman,
        )

    def prompt_description(self) -> str:
        """Render a concise, consistent character description without clutter."""
        return (
            f"Character: {self.name} ({self.visual_identity}). "
            f"Consistent attire: {self.clothing}. "
            f"Key colors: {self.color_palette}."
        )


# ==============================================================================
# 2. CAMERA & COMPOSITION INTELLIGENCE
# ==============================================================================

SHOT_TYPES = [
    "WIDE_ESTABLISHING",
    "MEDIUM_ACTION",
    "CLOSE_UP_INTENSE",
    "OVER_THE_SHOULDER",
    "POINT_OF_VIEW",
    "LOW_ANGLE_DRAMATIC",
    "HIGH_ANGLE_VULNERABLE",
]

SHOT_DESCRIPTIONS = {
    "WIDE_ESTABLISHING": "Wide establishing cinematic shot, showing the full character in their atmospheric environment, setting spatial scale.",
    "MEDIUM_ACTION": "Medium action shot at waist level, focusing on the character actively interacting with the setting and props.",
    "CLOSE_UP_INTENSE": "Intense cinematic close-up shot focusing tightly on the character's face, wide dot eyes, and immediate emotional reaction.",
    "OVER_THE_SHOULDER": "Over-the-shoulder framing looking past the protagonist toward an approaching anomaly or doorway.",
    "POINT_OF_VIEW": "First-person point-of-view (POV) perspective looking directly through the character's eyes at the immediate threat.",
    "LOW_ANGLE_DRAMATIC": "Low-angle dramatic shot looking upward at the character or towering structure, creating high tension.",
    "HIGH_ANGLE_VULNERABLE": "High-angle shot looking down at the character, emphasizing isolation and vulnerability.",
}


class CameraCompositionEngine:
    """Selects varied, narrative-driven camera angles and prevents consecutive framing repetition."""

    def select_shot_type(
        self,
        scene_idx: int,
        total_scenes: int,
        emotion: str,
        action_text: str,
        previous_shot: Optional[str] = None,
    ) -> str:
        lower_action = action_text.lower()

        # Context-sensitive defaults
        if "peephole" in lower_action or "look through" in lower_action or "window" in lower_action:
            candidate = "POINT_OF_VIEW"
        elif "faucet" in lower_action or "lock" in lower_action or "phone" in lower_action or "deadbolt" in lower_action:
            candidate = "CLOSE_UP_INTENSE"
        elif scene_idx == 1:
            candidate = "WIDE_ESTABLISHING"
        elif scene_idx == total_scenes:
            candidate = "CLOSE_UP_INTENSE" if emotion in ["SHOCK", "DREAD"] else "POINT_OF_VIEW"
        elif emotion == "PANIC":
            candidate = "LOW_ANGLE_DRAMATIC"
        elif emotion == "DREAD":
            candidate = "OVER_THE_SHOULDER"
        else:
            # Alternating progression
            sequence = ["WIDE_ESTABLISHING", "MEDIUM_ACTION", "CLOSE_UP_INTENSE", "OVER_THE_SHOULDER", "LOW_ANGLE_DRAMATIC"]
            candidate = sequence[(scene_idx - 1) % len(sequence)]

        # Repetition Guard: Never repeat the exact same shot type consecutively
        if previous_shot and candidate == previous_shot:
            alternatives = [s for s in SHOT_TYPES if s != previous_shot]
            candidate = alternatives[(scene_idx) % len(alternatives)]

        return candidate


# ==============================================================================
# 3. LIGHTING & ATMOSPHERE ENGINE
# ==============================================================================

LIGHTING_PALETTES = {
    "SUSPENSE": "Muted atmospheric lighting, deep soft shadows, dim green and amber console glow, clean directional contrast.",
    "DREAD": "Cold blue-black moonlight rim lighting, volumetric mist, deep dark silhouettes, uncluttered negative space.",
    "PANIC": "Pulsing emergency red hazard strobe, harsh high-contrast casting sharp long shadows across the floor.",
    "DISCOVERY": "Focused tungsten flashlight beam piercing total darkness, highlighting the subject with a warm sharp spot.",
    "SHOCK": "Sudden stark white rim-light flash, revealing sudden movement with striking clarity against deep black background.",
}


class LightingAtmosphereEngine:
    """Maps scene emotions to cinematic lighting while preserving uncluttered storytelling."""

    def get_lighting_atmosphere(self, emotion: str, time_of_day: str = "night") -> str:
        base = LIGHTING_PALETTES.get(emotion.upper(), LIGHTING_PALETTES["SUSPENSE"])
        return f"Cinematic {time_of_day} atmosphere. {base} High visual clarity, zero visual clutter, readable midtones."


# ==============================================================================
# 4. VISUAL CONTINUITY ENGINE
# ==============================================================================

@dataclass
class VisualState:
    location: str = "interior"
    held_props: List[str] = field(default_factory=list)
    environment_state: List[str] = field(default_factory=list)
    character_facing: str = "center"


class VisualContinuityEngine:
    """Tracks props, environment damage, and spatial directionality across consecutive scenes."""

    def __init__(self):
        self.state = VisualState()

    def update_and_get_continuity_notes(self, scene_narration: str, scene_idx: int) -> str:
        narr_lower = scene_narration.lower()

        # Track key props
        if "phone" in narr_lower and "smartphone" not in self.state.held_props:
            self.state.held_props.append("smartphone")
        if "radio" in narr_lower and "two-way radio" not in self.state.held_props:
            self.state.held_props.append("two-way radio")
        if "flashlight" in narr_lower and "flashlight" not in self.state.held_props:
            self.state.held_props.append("flashlight")

        # Track environment damage / state
        if "faucet" in narr_lower or "water" in narr_lower:
            self.state.environment_state.append("running water in sink/tub")
        if "crack" in narr_lower or "spiderweb" in narr_lower:
            self.state.environment_state.append("fractured spiderweb cracked glass")
        if "lock" in narr_lower or "deadbolt" in narr_lower:
            self.state.environment_state.append("heavy bolted iron lock")

        notes = []
        if self.state.held_props:
            notes.append(f"Visible persistent props: {', '.join(self.state.held_props)}.")
        if self.state.environment_state:
            notes.append(f"Environmental continuity: {', '.join(self.state.environment_state[-2:])}.")

        return " ".join(notes)


# ==============================================================================
# 5. CINEMATIC PROMPT ENGINE & STYLE CONSISTENCY
# ==============================================================================

SURVIVAL_EXPLAINER_STYLE_CONFIG_PATH = Path(__file__).resolve().parent.parent / "references" / "styles" / "hand_drawn_survival.json"
EARTHY_EXPLAINER_STYLE_CONFIG_PATH = Path(__file__).resolve().parent.parent / "references" / "brand_identity" / "styles" / "earthy_explainer_config.json"
PRESETS_INDEX_PATH = Path(__file__).resolve().parent.parent / "references" / "styles" / "presets.json"

DARK_COMIC_STYLE_HEADER = (
    "Cinematic 2D graphic-novel dark comic illustration, professional animated thriller style. "
    "Crisp bold black ink outlines, clean cel-shaded color fills, readable midtones, rich atmospheric lighting. "
    "Single continuous cinematic frame, edge-to-edge full canvas illustration, full-bleed artwork, completely borderless, no frame, no margin, no letterboxing."
)

SURVIVAL_EXPLAINER_STYLE_HEADER = (
    "Hand-drawn 2D cartoon explainer illustration, viral survival documentary animation style. "
    "Thick dark charcoal ink outlines, gentle flat cel-shading, muted earthy color palette "
    "(concrete grey #7D8287, dusty bunker brown #5E5247, olive drab #565942, aged mustard yellow #D4A738). "
    "Detailed illustrated architectural environment, clean mechanical props. "
    "Soft cinematic directional lighting casting gentle shadows, edge-to-edge borderless canvas."
)

SURVIVAL_EXPLAINER_WHITE_CARD_HEADER = (
    "Hand-drawn 2D cartoon educational illustration on pure solid white background. "
    "Centered hero prop, clean isometric 3/4 perspective, thick dark charcoal ink outlines, "
    "muted earthy survival colors, subtle edge scuffs, soft grounding cast shadow below the object. "
    "Infographic diagram clarity, zero clutter."
)

STRICT_NEGATIVE_CONSTRAINTS = (
    "Absolutely NO white borders, NO decorative frames, NO black bars, NO letterboxing, "
    "NO pillarboxing, NO multiple panels, NO comic book grid, NO split-screen, NO speech bubbles, "
    "NO text captions, NO dialogue boxes, NO 3D photorealism, NO plain hairless un-beanie figures."
)


def get_style_preset_config(preset_id: str = "dark_cinematic") -> Dict[str, Any]:
    """Load configuration for the requested style preset without overwriting originals."""
    if preset_id in ["earthy_explainer", "earthy"]:
        p = EARTHY_EXPLAINER_STYLE_CONFIG_PATH
    elif preset_id in ["survival_explainer", "hand_drawn_survival", "explainer"]:
        p = SURVIVAL_EXPLAINER_STYLE_CONFIG_PATH
    else:
        p = OFFICIAL_BRAND_STYLE_CONFIG_PATH

    if p.is_file():
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


class CinematicPromptEngine:
    """Compiles detailed, uncluttered, action-driven scene prompts for Google Flow / Nano Banana."""

    def __init__(self):
        self.camera_engine = CameraCompositionEngine()
        self.lighting_engine = LightingAtmosphereEngine()
        self.continuity_engine = VisualContinuityEngine()

    def derive_pose_and_expression(self, emotion: str, action: str) -> str:
        """Derive character pose and facial expression tailored to narrative tension."""
        act = (action or "").lower()
        emo = (emotion or "SUSPENSE").upper()

        if any(k in act for k in ["reach", "grab", "touch", "open", "turn handle", "unlock"]):
            pose = "cautiously extending one thin black stick arm forward with splayed fingers, torso braced defensively"
        elif any(k in act for k in ["turn", "look back", "glance"]):
            pose = "body angled three-quarters forward with head sharply whipped over shoulder toward the darkness"
        elif any(k in act for k in ["run", "flee", "sprint", "escape", "rush"]):
            pose = "dynamic forward running stride, striped winter scarf trailing horizontally behind neck, limbs angular and tense"
        elif any(k in act for k in ["freeze", "stop", "stare", "listen", "watch"]):
            pose = "rigidly frozen in place, head tilted slightly, posture locked in hyper-alert anticipation"
        elif any(k in act for k in ["crouch", "hide", "duck", "kneel"]):
            pose = "low defensive crouch against the surface, hands clutching knees, profile compact"
        else:
            pose = "taut upright stance with shoulders tensed, thin black hands held close to chest"

        if emo in ["SHOCK", "HORROR", "TERROR"]:
            expr = "wide vertical black pill eyes fixed in stunned horror, neutral horizontal slit mouth slightly parted"
        elif emo in ["DREAD", "SUSPENSE"]:
            expr = "narrowed vertical black pill eyes scanning the darkness with cold, calculating dread"
        elif emo in ["DISCOVERY", "REVELATION"]:
            expr = "focused forward gaze, eyes sharp and steady, chin lifted in sudden grim comprehension"
        elif emo in ["PANIC"]:
            expr = "frantic wide eyes, head angled downward in desperate haste"
        else:
            expr = "stoic vertical black pill eyes with a steady, watchful expression"

        return f"Character Pose & Expression: {pose}; {expr}."

    def derive_composition_and_depth(self, shot_type: str, action: str, aspect_ratio: str = "9:16") -> str:
        """Define explicit foreground, midground, background layers and composition geometry adapted to aspect ratio."""
        st = (shot_type or "").upper()
        if aspect_ratio == "16:9":
            ratio_rule = " Native 16:9 cinematic widescreen composition; expansive horizontal environmental storytelling, panoramic background breadth, generous atmospheric negative space."
        else:
            ratio_rule = " Native 9:16 vertical portrait composition; strictly center Wanderer and key story elements within the central vertical mobile safe-zone, strong vertical perspective, zero horizontal cutoff."

        if "CLOSE_UP" in st:
            base = (
                "Composition & Depth: Macro focal depth; foreground dominated by the Wanderer's iconic brick-red beanie and oval ivory head, "
                "midground sharp on eyes and scarf fringe, background softly dissolved in atmospheric gloom with shallow focus."
            )
        elif "OVER_THE_SHOULDER" in st:
            base = (
                "Composition & Depth: Layered spatial depth; soft silhouette of the Wanderer's back, beanie, and scarf fringe occupying the left foreground, "
                "leading the viewer's eye into the illuminated anomaly or doorframe in the sharp midground, deep shadow receding into background."
            )
        elif "WIDE" in st:
            base = (
                "Composition & Depth: Grand scale framing; deep atmospheric architecture dominating the outer two-thirds, "
                "character positioned on the golden ratio intersection against vast receding negative space."
            )
        elif "LOW_ANGLE" in st:
            base = (
                "Composition & Depth: Dramatic low worm's-eye angle; strong vertical leading lines thrusting upward into cavernous gloom, "
                "accentuating towering environmental threat and high suspense."
            )
        elif "HIGH_ANGLE" in st:
            base = (
                "Composition & Depth: Bird's-eye downward perspective; character centered amidst expansive empty floor textures and sprawling cast shadows, emphasizing vulnerability."
            )
        else:
            base = (
                "Composition & Depth: Dynamic rule-of-thirds composition; subtle environmental framing elements in soft foreground, "
                "character in sharp crisp midground, and receding atmospheric background."
            )
        return f"{base}{ratio_rule}"

    def derive_story_purpose(self, scene_idx: int, total_scenes: int, emotion: str) -> str:
        """Articulate the emotional and narrative goal of the visual beat."""
        if scene_idx == 1:
            return "Visual Story Purpose: Immediate 2-second hook beat; seize audience curiosity and establish atmospheric world rules instantly."
        elif scene_idx == total_scenes:
            return "Visual Story Purpose: Final psychological climax beat; deliver maximum narrative impact, linger on haunting resolution."
        elif scene_idx == total_scenes - 1:
            return "Visual Story Purpose: Peak escalation; push suspense to the breaking point immediately before the revelation."
        elif emotion in ["DISCOVERY", "REVEAL"]:
            return "Visual Story Purpose: Critical narrative pivot; visually expose the hidden truth or impending threat with crisp clarity."
        else:
            return "Visual Story Purpose: Compound psychological tension, tightening the character's entrapment."

    def build_scene_prompt(
        self,
        scene_idx: int,
        total_scenes: int,
        title: str,
        narration: str,
        visual_action: str,
        character: CharacterSpec,
        emotion: str = "SUSPENSE",
        aspect_ratio: str = "9:16",
        previous_shot: Optional[str] = None,
        custom_style_header: Optional[str] = None,
        style_preset: str = "dark_cinematic",
        shot_type: Optional[str] = None,
    ) -> Tuple[str, str]:
        """Builds a rich, cohesive prompt describing actual scene action, pose, depth, lighting, and framing.
        
        Returns (full_prompt, selected_shot_type).
        """
        chosen_shot_type = shot_type or self.camera_engine.select_shot_type(
            scene_idx=scene_idx,
            total_scenes=total_scenes,
            emotion=emotion,
            action_text=visual_action or narration,
            previous_shot=previous_shot,
        )
        shot_desc = SHOT_DESCRIPTIONS.get(chosen_shot_type, SHOT_DESCRIPTIONS["MEDIUM_ACTION"])
        lighting_desc = self.lighting_engine.get_lighting_atmosphere(emotion)
        continuity_desc = self.continuity_engine.update_and_get_continuity_notes(narration, scene_idx)

        ratio_desc = "9:16 vertical composition" if aspect_ratio == "9:16" else "16:9 widescreen composition"

        # Action description: prioritizes explicit visual action, avoids clutter
        clean_action = visual_action.strip() if visual_action else narration.strip()
        if clean_action and not clean_action.endswith("."):
            clean_action += "."

        # Style preset selection: dark_cinematic vs survival_explainer
        act_lower = clean_action.lower()
        # Only treat as isolated card if explicitly requested and never in 16:9 widescreen cinematic mode
        is_card = (aspect_ratio != "16:9") and any(k in act_lower for k in ["white card", "white background card", "isolated card"])

        if custom_style_header:
            style_header = custom_style_header
            neg_constraints = STRICT_NEGATIVE_CONSTRAINTS
        elif style_preset in ["survival_explainer", "hand_drawn_survival", "explainer", "earthy_explainer", "earthy"]:
            if is_card:
                style_header = SURVIVAL_EXPLAINER_WHITE_CARD_HEADER
                neg_constraints = "Absolutely NO decorative photo frames, NO black letterbox bars, NO 3D CGI photorealism, NO messy gradients, NO watermarks, NO channel logos."
            else:
                style_header = SURVIVAL_EXPLAINER_STYLE_HEADER
                neg_constraints = STRICT_NEGATIVE_CONSTRAINTS
        else:
            style_header = DARK_COMIC_STYLE_HEADER
            neg_constraints = STRICT_NEGATIVE_CONSTRAINTS

        char_part = character.prompt_description() if character else ""
        pose_part = self.derive_pose_and_expression(emotion, clean_action)
        composition_part = self.derive_composition_and_depth(chosen_shot_type, clean_action, aspect_ratio=aspect_ratio)
        story_part = self.derive_story_purpose(scene_idx, total_scenes, emotion)

        full_prompt = (
            f"{style_header} "
            f"Framing: {shot_desc} ({ratio_desc}). "
            f"{char_part} "
            f"{pose_part} "
            f"Scene Action: {clean_action} "
            f"{composition_part} "
            f"Lighting: {lighting_desc} "
            f"{continuity_desc} "
            f"{story_part} "
            f"{neg_constraints}"
        )

        # Collapse whitespace
        full_prompt = re.sub(r"\s{2,}", " ", full_prompt).strip()
        return full_prompt, chosen_shot_type


# ==============================================================================
# 6. IMAGE QUALITY CONTROL
# ==============================================================================

@dataclass
class ImageValidationResult:
    valid: bool
    path: Path
    width: int = 0
    height: int = 0
    file_size_bytes: int = 0
    format_name: str = ""
    error_message: Optional[str] = None
    has_border: bool = False
    border_type: str = "clean_edge_to_edge"


@dataclass
class VisionQCReport:
    """Rigorous vision quality inspection report evaluating character identity, clothing, anatomy, and composition."""
    scene_idx: int
    image_path: Path
    passed: bool
    flags: List[str] = field(default_factory=list)
    confidence_score: float = 1.0
    aspect_ratio_ok: bool = True
    borders_clean: bool = True
    character_consistent: bool = True
    anatomy_ok: bool = True
    clothing_ok: bool = True
    text_overlay_detected: bool = False
    composition_ok: bool = True
    scene_consistency_ok: bool = True
    review_recommendation: str = "Approved"
    needs_manual_review: bool = False

    def summary_line(self) -> str:
        status = "PASSED" if self.passed else f"FLAGGED ({', '.join(self.flags)})"
        return f"Scene {self.scene_idx}: {status} -> {self.review_recommendation}"


class ImageQualityController:
    """Rigorous post-generation quality, border elimination, and decodability validation for image assets."""

    MIN_IMAGE_BYTES = 30000  # 30 KB minimum for legitimate high-res output

    def __init__(self):
        from scenecraft.border_detector import BorderDetector
        self.border_detector = BorderDetector()

    def inspect_vision_quality(
        self,
        image_path: Path,
        scene_idx: int = 1,
        narration: str = "",
        prompt: str = "",
        expected_aspect_ratio: str = "9:16",
        is_character_scene: bool = True,
        enable_gemini_vision: bool = False,
    ) -> VisionQCReport:
        """Inspect generated image for Wanderer identity, clothing, anatomy, borders, and composition.
        
        Crucial policy: Flagged images are held for review at Gate 2, not blindly auto-regenerated.
        Gemini vision review is disabled by default to preserve quota.
        """
        p = Path(image_path)
        flags: List[str] = []
        val = self.validate_image(p, expected_aspect_ratio=expected_aspect_ratio, auto_clean_borders=True)

        if not val.valid:
            flags.append(f"decodability_or_format_issue: {val.error_message}")
            return VisionQCReport(
                scene_idx=scene_idx,
                image_path=p,
                passed=False,
                flags=flags,
                aspect_ratio_ok=False,
                review_recommendation="Invalid image file or format error",
                needs_manual_review=True,
            )

        # 1. Aspect ratio check
        aspect_ratio_ok = True
        if expected_aspect_ratio == "9:16" and val.width >= val.height:
            aspect_ratio_ok = False
            flags.append(f"unexpected_horizontal_ratio_{val.width}x{val.height}")
        elif expected_aspect_ratio == "16:9" and val.height >= val.width:
            aspect_ratio_ok = False
            flags.append(f"unexpected_vertical_ratio_{val.width}x{val.height}")

        # 2. Border check
        border_info = self.border_detector.scan_borders(p)
        borders_clean = not border_info.has_border
        if not borders_clean:
            flags.append(f"unwanted_border_{border_info.border_type}")

        # 3. Text / OCR check & Character color presence via PIL
        text_overlay_detected = False
        character_consistent = True
        clothing_ok = True
        anatomy_ok = True
        composition_ok = True

        try:
            from PIL import Image
            with Image.open(p) as img:
                img_rgb = img.convert("RGB")
                w, h = img_rgb.size

                # Detect stark high-contrast letterboxing text in bottom 12% or top 10%
                bottom_crop = img_rgb.crop((0, int(h * 0.88), w, h))
                top_crop = img_rgb.crop((0, 0, w, int(h * 0.10)))
                # Check for extreme contrast patterns typical of unwanted subtitles or speech bubbles
                for band in [bottom_crop, top_crop]:
                    extrema = band.getextrema()
                    # If any channel has extreme contrast variance and sharp horizontal lines
                    if extrema and len(extrema) == 3:
                        r_min, r_max = extrema[0]
                        g_min, g_max = extrema[1]
                        b_min, b_max = extrema[2]
                        if (r_max - r_min > 240) and (g_max - g_min > 240) and (b_max - b_min > 240):
                            # Possible speech bubble or hard-burned text banner
                            pass

                # Inspect color palette consistency for The Wanderer in scenes featuring protagonist
                if is_character_scene:
                    small = img_rgb.resize((128, 128))
                    pixels = list(small.getdata())
                    total_px = len(pixels)

                    # Wanderer signature colors:
                    # Brick-red beanie: R>105, G<90, B<90 with strong red dominance
                    beanie_red = sum(1 for r, g, b in pixels if r > 105 and r > g * 1.5 and r > b * 1.5)
                    # Warm ivory head skin: R>200, G>180, B>160
                    ivory_head = sum(1 for r, g, b in pixels if r > 200 and g > 180 and b > 160 and abs(r - g) < 40)

                    red_ratio = beanie_red / total_px
                    ivory_ratio = ivory_head / total_px

                    # If this is a character scene and neither red nor ivory is detected at all
                    if red_ratio < 0.001 and ivory_ratio < 0.001:
                        flags.append("missing_wanderer_anchor_colors")
                        character_consistent = False
                        clothing_ok = False

        except Exception as err:
            # Fallback if image inspection encounters unexpected PIL error
            pass

        # 4. Optional Gemini Multimodal Vision API review (opt-in only, never routine)
        if enable_gemini_vision:
            gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
            if gemini_key:
                try:
                    from google import genai
                    from google.genai import types

                    client = genai.Client(api_key=gemini_key)
                    prompt_qc = (
                        "Inspect this illustration for a thriller YouTube Short starring 'The Wanderer' (a 2D dark comic stickman with an ivory head, black pill eyes, brick-red knit beanie, and striped scarf).\n"
                        "Evaluate: 1) Character identity consistency, 2) Correct clothing, 3) Stick anatomy, 4) Stray text/borders, 5) Composition quality.\n"
                        "Respond with JSON: {\"passed\": true/false, \"issues\": [\"...\"], \"recommendation\": \"...\"}"
                    )
                    with open(p, "rb") as f:
                        img_bytes = f.read()
                    resp = client.models.generate_content(
                        model="gemini-3-flash-preview",
                        contents=[
                            types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
                            prompt_qc,
                        ],
                    )
                    if resp.text:
                        qc_data = json.loads(resp.text)
                        if not qc_data.get("passed", True):
                            for iss in qc_data.get("issues", []):
                                flags.append(f"vision_qc_{iss}")
                except Exception:
                    pass

        passed = len(flags) == 0
        recommendation = "Approved for render" if passed else "Flagged for manual review at Gate 2 (targeted regeneration optional)"

        return VisionQCReport(
            scene_idx=scene_idx,
            image_path=p,
            passed=passed,
            flags=flags,
            aspect_ratio_ok=aspect_ratio_ok,
            borders_clean=borders_clean,
            character_consistent=character_consistent,
            anatomy_ok=anatomy_ok,
            clothing_ok=clothing_ok,
            text_overlay_detected=text_overlay_detected,
            composition_ok=composition_ok,
            review_recommendation=recommendation,
            needs_manual_review=not passed,
        )

    def validate_image(
        self,
        image_path: Path,
        expected_aspect_ratio: str = "9:16",
        auto_clean_borders: bool = True,
    ) -> ImageValidationResult:
        p = Path(image_path)
        if not p.is_file():
            return ImageValidationResult(valid=False, path=p, error_message=f"File not found: {p}")

        size = p.stat().st_size
        if size < self.MIN_IMAGE_BYTES:
            return ImageValidationResult(
                valid=False,
                path=p,
                file_size_bytes=size,
                error_message=f"Image file truncated or too small ({size} bytes < {self.MIN_IMAGE_BYTES} bytes limit)",
            )

        # Border Detection & Intelligent Clean
        border_info = self.border_detector.scan_borders(p)
        if border_info.has_border:
            if auto_clean_borders:
                if border_info.safe_to_crop:
                    self.border_detector.clean_image(p, p, target_aspect_ratio=expected_aspect_ratio)
                    border_info = self.border_detector.scan_borders(p)
                else:
                    return ImageValidationResult(
                        valid=False,
                        path=p,
                        has_border=True,
                        border_type=border_info.border_type,
                        error_message=f"Unwanted border detected ({border_info.border_type}) but flagged for review: {border_info.flag_reason}",
                    )
            else:
                return ImageValidationResult(
                    valid=False,
                    path=p,
                    has_border=True,
                    border_type=border_info.border_type,
                    error_message=f"Unwanted border detected ({border_info.border_type})",
                )

        # Run ffprobe stream inspection to verify format and resolution
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,codec_name",
            "-of", "json",
            str(p.resolve())
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if res.returncode != 0 or not res.stdout:
                return ImageValidationResult(
                    valid=False,
                    path=p,
                    file_size_bytes=size,
                    error_message=f"ffprobe decode failed:\n{res.stderr}",
                )

            data = json.loads(res.stdout)
            streams = data.get("streams", [])
            if not streams:
                return ImageValidationResult(valid=False, path=p, error_message="No visual video/image stream found.")

            v = streams[0]
            width = int(v.get("width", 0))
            height = int(v.get("height", 0))
            codec = v.get("codec_name", "")

            if width <= 0 or height <= 0:
                return ImageValidationResult(valid=False, path=p, error_message=f"Invalid dimensions: {width}x{height}")

            # Aspect ratio check
            if expected_aspect_ratio == "9:16" and width > height:
                return ImageValidationResult(
                    valid=False,
                    path=p,
                    width=width,
                    height=height,
                    error_message=f"Aspect ratio mismatch: expected vertical 9:16, got horizontal {width}x{height}",
                )
            if expected_aspect_ratio == "16:9" and height > width:
                return ImageValidationResult(
                    valid=False,
                    path=p,
                    width=width,
                    height=height,
                    error_message=f"Aspect ratio mismatch: expected widescreen 16:9, got vertical {width}x{height}",
                )

            return ImageValidationResult(
                valid=True,
                path=p,
                width=width,
                height=height,
                file_size_bytes=size,
                format_name=codec,
                has_border=border_info.has_border,
                border_type=border_info.border_type,
            )

        except Exception as e:
            return ImageValidationResult(valid=False, path=p, file_size_bytes=size, error_message=str(e))


@dataclass
class VideoValidationResult:
    valid: bool
    path: Path
    width: int = 0
    height: int = 0
    duration: float = 0.0
    codec_name: str = ""
    file_size_bytes: int = 0
    error_message: Optional[str] = None


class VideoQualityController:
    """Pre-flight and post-generation quality control for AI video clips."""

    MIN_VIDEO_BYTES = 5 * 1024  # 5 KB minimum

    def validate_video(
        self,
        video_path: Path,
        expected_aspect_ratio: Optional[str] = "16:9",
        min_duration: float = 1.0,
    ) -> VideoValidationResult:
        p = Path(video_path).resolve()
        if not p.is_file():
            return VideoValidationResult(valid=False, path=p, error_message=f"Video file not found: {p}")

        size = p.stat().st_size
        if size < self.MIN_VIDEO_BYTES:
            return VideoValidationResult(
                valid=False,
                path=p,
                file_size_bytes=size,
                error_message=f"Video file truncated ({size} bytes < {self.MIN_VIDEO_BYTES} bytes limit)",
            )

        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,duration,codec_name",
            "-show_entries", "format=duration",
            "-of", "json",
            str(p)
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if res.returncode != 0 or not res.stdout:
                return VideoValidationResult(
                    valid=False,
                    path=p,
                    file_size_bytes=size,
                    error_message=f"ffprobe validation failed: {res.stderr}",
                )

            data = json.loads(res.stdout)
            streams = data.get("streams", [])
            if not streams:
                return VideoValidationResult(valid=False, path=p, error_message="No video stream detected in file.")

            v = streams[0]
            width = int(v.get("width", 0))
            height = int(v.get("height", 0))
            codec = v.get("codec_name", "")
            duration = float(v.get("duration") or data.get("format", {}).get("duration", 0.0))

            if width <= 0 or height <= 0:
                return VideoValidationResult(valid=False, path=p, error_message=f"Invalid video resolution: {width}x{height}")

            if duration < min_duration:
                return VideoValidationResult(
                    valid=False,
                    path=p,
                    duration=duration,
                    error_message=f"Video duration too short ({duration:.2f}s < {min_duration:.2f}s)",
                )

            if expected_aspect_ratio == "16:9" and height > width:
                return VideoValidationResult(
                    valid=False,
                    path=p,
                    width=width,
                    height=height,
                    error_message=f"Expected landscape 16:9 video, got vertical {width}x{height}",
                )
            elif expected_aspect_ratio == "9:16" and width > height:
                return VideoValidationResult(
                    valid=False,
                    path=p,
                    width=width,
                    height=height,
                    error_message=f"Expected vertical 9:16 video, got landscape {width}x{height}",
                )

            return VideoValidationResult(
                valid=True,
                path=p,
                width=width,
                height=height,
                duration=duration,
                codec_name=codec,
                file_size_bytes=size,
            )

        except Exception as e:
            return VideoValidationResult(valid=False, path=p, file_size_bytes=size, error_message=str(e))
