"""Unit tests for Scenecraft Visual Intelligence Engine."""

import json
import tempfile
import unittest
from pathlib import Path

from scenecraft.visual_intelligence import (
    CharacterSpec,
    CameraCompositionEngine,
    LightingAtmosphereEngine,
    VisualContinuityEngine,
    CinematicPromptEngine,
    ImageQualityController,
    ImageValidationResult,
    DEFAULT_STICKMAN_IDENTITY,
)
from scenecraft.prompt_builder import ScenePrompt, build_prompts_from_scenes


class TestVisualIntelligence(unittest.TestCase):
    def setUp(self):
        self.camera_engine = CameraCompositionEngine()
        self.lighting_engine = LightingAtmosphereEngine()
        self.continuity_engine = VisualContinuityEngine()
        self.prompt_engine = CinematicPromptEngine()
        self.quality_controller = ImageQualityController()

    # 1. CHARACTER CONSISTENCY ENGINE
    def test_default_stickman_character(self):
        char = CharacterSpec()
        self.assertTrue(char.is_stickman)
        self.assertIn("brick-red ribbed knit beanie", char.clothing)
        self.assertIn("striped mustard-gold", char.clothing)
        desc = char.prompt_description()
        self.assertIn("ivory oval head", desc)

    def test_custom_non_stickman_character(self):
        custom_data = {
            "name": "Captain Vance",
            "role": "Submarine Commander",
            "visual_anchor": "Weathered 50-year-old naval commander in charcoal service sweater with silver anchor pin and deep crow's feet eyes.",
            "clothing": "charcoal service sweater, naval officer cap",
            "color_palette": "Charcoal grey, navy blue, muted brass",
        }
        char = CharacterSpec.from_dict(custom_data)
        self.assertFalse(char.is_stickman)
        self.assertEqual(char.name, "Captain Vance")
        desc = char.prompt_description()
        self.assertIn("Captain Vance", desc)
        self.assertIn("charcoal service sweater", desc)
        self.assertNotIn("stickman", desc.lower())

    # 2. CAMERA & COMPOSITION INTELLIGENCE
    def test_camera_shot_selection_and_anti_repetition(self):
        # Scene 1 is establishing
        shot1 = self.camera_engine.select_shot_type(1, 5, "SUSPENSE", "Standing in apartment", previous_shot=None)
        self.assertEqual(shot1, "WIDE_ESTABLISHING")

        # If next candidate would be WIDE, anti-repetition guard must force a different angle
        shot2 = self.camera_engine.select_shot_type(2, 5, "SUSPENSE", "Standing in apartment", previous_shot=shot1)
        self.assertNotEqual(shot1, shot2)

        # Peephole action triggers POV
        shot_pov = self.camera_engine.select_shot_type(3, 5, "SUSPENSE", "Peering through the front door peephole", previous_shot=None)
        self.assertEqual(shot_pov, "POINT_OF_VIEW")

        # Deadbolt action triggers CLOSE_UP
        shot_cu = self.camera_engine.select_shot_type(4, 5, "SUSPENSE", "Turning the heavy deadbolt lock", previous_shot=None)
        self.assertEqual(shot_cu, "CLOSE_UP_INTENSE")

    # 3. LIGHTING & ATMOSPHERE ENGINE
    def test_lighting_atmosphere_matches_emotion(self):
        panic_light = self.lighting_engine.get_lighting_atmosphere("PANIC")
        self.assertIn("emergency red", panic_light.lower())
        self.assertIn("zero visual clutter", panic_light)

        dread_light = self.lighting_engine.get_lighting_atmosphere("DREAD")
        self.assertIn("moonlight", dread_light.lower())

        discovery_light = self.lighting_engine.get_lighting_atmosphere("DISCOVERY")
        self.assertIn("flashlight", discovery_light.lower())

    # 4. VISUAL CONTINUITY ENGINE
    def test_visual_continuity_tracks_props_and_environment(self):
        c_engine = VisualContinuityEngine()
        # Scene 1 mentions phone
        notes1 = c_engine.update_and_get_continuity_notes("You pick up your smartphone from the desk.", 1)
        self.assertIn("smartphone", notes1)

        # Scene 2 mentions faucet water
        notes2 = c_engine.update_and_get_continuity_notes("You twist the bathroom faucet as water fills the basin.", 2)
        self.assertIn("smartphone", notes2)
        self.assertIn("water", notes2)

    # 5. CINEMATIC PROMPT COMPILER
    def test_prompt_compiler_structure(self):
        char = CharacterSpec()
        prompt, shot_type = self.prompt_engine.build_scene_prompt(
            scene_idx=1,
            total_scenes=5,
            title="The Lockdown",
            narration="You live on the 30th floor overlooking the dark city.",
            visual_action="Stickman standing by floor-to-ceiling panoramic glass windows looking out over a massive city skyline.",
            character=char,
            emotion="SUSPENSE",
            aspect_ratio="9:16",
        )
        self.assertIn("Cinematic 2D graphic-novel", prompt)
        self.assertIn("9:16 vertical", prompt)
        self.assertIn("brick-red ribbed knit beanie", prompt)
        self.assertIn("panoramic glass windows", prompt)
        self.assertIn("NO multiple panels", prompt)
        self.assertIn("NO comic book grid", prompt)

    # 6. IMAGE QUALITY CONTROLLER
    def test_quality_controller_rejects_missing_file(self):
        res = self.quality_controller.validate_image(Path("/nonexistent/image.jpg"))
        self.assertFalse(res.valid)
        self.assertIn("File not found", res.error_message)

    def test_quality_controller_rejects_truncated_file(self):
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(b"tiny truncated garbage")
            tmp_path = Path(f.name)

        try:
            res = self.quality_controller.validate_image(tmp_path)
            self.assertFalse(res.valid)
            self.assertIn("truncated or too small", res.error_message)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    # 7. PROMPT BUILDER INTEGRATION
    def test_build_prompts_from_scenes_with_custom_character(self):
        scenes_data = [
            {"scene_index": 1, "title": "Beat 1", "narration": "First scene.", "visual_description": "Looking at door."},
            {"scene_index": 2, "title": "Beat 2", "narration": "Second scene.", "visual_description": "Turning the deadbolt."},
            {"scene_index": 3, "title": "Beat 3", "narration": "Third scene.", "visual_description": "Peering through peephole."},
        ]
        char_dict = {
            "name": "Miller",
            "role": "Foreman",
            "visual_anchor": "Rugged industrial foreman in orange high-vis vest and steel helmet.",
            "clothing": "orange high-vis vest and steel helmet",
        }
        prompts = build_prompts_from_scenes(scenes_data, aspect_ratio="9:16", character_data=char_dict)
        self.assertEqual(len(prompts), 3)
        self.assertEqual(prompts[0].character.name, "Miller")
        # Check that consecutive shots have different framing
        self.assertNotEqual(prompts[0].shot_type, prompts[1].shot_type)
        self.assertNotEqual(prompts[1].shot_type, prompts[2].shot_type)


if __name__ == "__main__":
    unittest.main()
