import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from scenecraft.script_handoff import (
    parse_markdown_script,
    load_script,
    validate_script,
    save_script,
    ScriptValidationResult,
)
from scenecraft.story_gen import (
    generate_story,
    generate_auto_story,
    call_gemini_api,
    mask_api_key,
)
from scenecraft.visual_intelligence import get_style_preset_config


class TestScriptHandoffAndVersioning(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_parse_markdown_script(self):
        md = (
            "# The Bunker Hatch\n"
            "**Genre:** Survival Mystery\n"
            "**Aspect Ratio:** 9:16\n"
            "**Style:** earthy_explainer\n"
            "**Premise:** A lone survivor finds an unlocked hatch.\n\n"
            "### Scene 1: The Ledge\n"
            "- Narration: When night fell, the sirens ceased.\n"
            "- Visual: The Wanderer standing on concrete roof.\n"
            "- Camera: zoom_in\n"
            "- SFX: sfx_alarm\n\n"
            "### Scene 2: The Breach\n"
            "- Narration: The hatch was warm to the touch.\n"
            "- Visual: Close up of rusted steel wheel.\n"
            "- Camera: pan_left\n"
            "- SFX: sfx_knock\n\n"
            "### Scene 3: Inside\n"
            "- Narration: Footsteps echoed in the dark.\n"
            "- Visual: Deep shadow corridor under yellow light.\n"
            "- Camera: zoom_in\n"
            "- SFX: sfx_footsteps\n"
        )
        parsed = parse_markdown_script(md)
        self.assertEqual(parsed["story_title"], "The Bunker Hatch")
        self.assertEqual(parsed["genre"], "Survival Mystery")
        self.assertEqual(parsed["aspect_ratio"], "9:16")
        self.assertEqual(parsed["style"], "earthy_explainer")
        self.assertEqual(len(parsed["scenes"]), 3)
        self.assertEqual(parsed["scenes"][0]["narration"], "When night fell, the sirens ceased.")
        self.assertEqual(parsed["scenes"][1]["sfx_cue"], "sfx_knock")

    def test_non_destructive_script_versioning(self):
        data = {
            "story_title": "The Signal Tower",
            "genre": "Suspense",
            "aspect_ratio": "9:16",
            "scenes": [
                {"scene_index": 1, "title": "S1", "narration": "First beat.", "visual_description": "V1."},
                {"scene_index": 2, "title": "S2", "narration": "Second beat.", "visual_description": "V2."},
                {"scene_index": 3, "title": "S3", "narration": "Third beat.", "visual_description": "V3."},
            ],
        }
        # Save version 1
        path_v1, v1_num = save_script(data, base_dir=self.workspace, format="json")
        self.assertEqual(v1_num, 1)
        self.assertTrue(path_v1.is_file())
        self.assertEqual(path_v1.name, "v1.json")

        # Save revision without overwriting: should create v2
        data["premise"] = "Updated premise for revision"
        path_v2, v2_num = save_script(data, base_dir=self.workspace, format="json")
        self.assertEqual(v2_num, 2)
        self.assertTrue(path_v2.is_file())
        self.assertEqual(path_v2.name, "v2.json")

        # Ensure v1 was NOT modified or deleted
        self.assertTrue(path_v1.is_file())
        v1_data = json.loads(path_v1.read_text(encoding="utf-8"))
        self.assertEqual(v1_data.get("version"), 1)
        self.assertNotIn("premise", v1_data)

    def test_script_validation_passes_valid_script(self):
        data = {
            "story_title": "The Rooftop Signal",
            "genre": "Suspense",
            "aspect_ratio": "9:16",
            "scenes": [
                {"scene_index": 1, "title": "S1", "narration": "When the city fell quiet at dusk, you climbed.", "visual_description": "The Wanderer on the roof."},
                {"scene_index": 2, "title": "S2", "narration": "The radio hissed with automated coordinates.", "visual_description": "Hand holding glowing green radio."},
                {"scene_index": 3, "title": "S3", "narration": "You reached the ladder just before the cloud hit.", "visual_description": "Stickman descending iron ladder into bunker."},
            ],
        }
        res = validate_script(data)
        self.assertTrue(res.valid)
        self.assertEqual(len(res.errors), 0)
        self.assertEqual(res.total_scenes, 3)

    def test_script_validation_fails_missing_fields(self):
        # Empty title and missing scene narration
        bad_data = {
            "story_title": "",
            "aspect_ratio": "4:3",  # invalid aspect ratio
            "scenes": [
                {"scene_index": 1, "title": "S1", "narration": "", "visual_description": "No narration here."},
            ],
        }
        res = validate_script(bad_data)
        self.assertFalse(res.valid)
        self.assertTrue(any("title" in e.lower() for e in res.errors))
        self.assertTrue(any("aspect ratio" in e.lower() for e in res.errors))
        self.assertTrue(any("minimum is 3" in e.lower() for e in res.errors))


class TestGeminiFallbackArchitecture(unittest.TestCase):
    def test_mask_api_key(self):
        self.assertEqual(mask_api_key(None), "[NONE]")
        self.assertEqual(mask_api_key("short"), "***")
        self.assertEqual(mask_api_key("dummy_mock_key_testing_1234"), "dumm...1234")

    def test_default_story_gen_uses_local_engine_without_gemini(self):
        # With default fallback_mode="local", Gemini API must NOT be called even if API key exists
        with patch("scenecraft.story_gen.call_gemini_api") as mock_gemini:
            story = generate_story("The Underground Depot", fallback_mode="local")
            mock_gemini.assert_not_called()
            self.assertEqual(story["story_title"], "The Underground Depot")
            self.assertTrue(len(story["scenes"]) >= 4)

    def test_fallback_none_raises_error_when_no_script(self):
        with self.assertRaises(RuntimeError) as ctx:
            generate_story("The Lost Station", fallback_mode="none")
        self.assertIn("fallback is disabled", str(ctx.exception))

    def test_gemini_quota_exhaustion_stops_without_retry(self):
        # Mock call_gemini_api returning HTTP 429 quota exhausted
        with patch("scenecraft.story_gen.call_gemini_api", return_value=(None, "Gemini API Quota Exceeded (HTTP 429)")):
            with self.assertRaises(RuntimeError) as ctx:
                generate_story(
                    "The Broken Transmitter",
                    api_key="mock_key",
                    fallback_mode="gemini",
                    allow_local_on_gemini_fail=False,
                )
            self.assertIn("Quota Exceeded", str(ctx.exception))

    def test_gemini_failure_with_allow_local_fallback(self):
        with patch("scenecraft.story_gen.call_gemini_api", return_value=(None, "Connection timed out")):
            story = generate_story(
                "The Backup Generator",
                api_key="mock_key",
                fallback_mode="gemini",
                allow_local_on_gemini_fail=True,
            )
            # Successfully fell back to procedural engine
            self.assertEqual(story["story_title"], "The Backup Generator")
            self.assertTrue(len(story["scenes"]) >= 4)


class TestVoiceAuditionAndPresets(unittest.TestCase):
    def test_style_presets_load_dark_cinematic_and_earthy_explainer(self):
        dark_cfg = get_style_preset_config("dark_cinematic")
        self.assertIsNotNone(dark_cfg)

        earthy_cfg = get_style_preset_config("earthy_explainer")
        self.assertIsNotNone(earthy_cfg)
        self.assertIn("Earthy Explainer", earthy_cfg.get("style_name", ""))
        self.assertEqual(earthy_cfg.get("character_name"), "The Wanderer")


if __name__ == "__main__":
    unittest.main()
