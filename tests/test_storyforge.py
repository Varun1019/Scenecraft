"""Unit tests for StoryForge using standard library unittest."""

import unittest
from pathlib import Path

from storyforge.audio_manager import AudioManager, LicenseError
from storyforge.prompt_builder import build_prompts_from_scenes
from storyforge.story_gen import generate_story
from storyforge.flow_client import FlowClient


class TestStoryForge(unittest.TestCase):
    def test_audio_manager_licenses(self):
        mgr = AudioManager()
        # Test valid asset
        asset = mgr.verify_asset("apocalypse_ambient_drone.wav")
        self.assertEqual(asset["status"], "VERIFIED")
        self.assertTrue(asset["youtube_monetization_safe"])

        # Test rejection of unverified asset
        with self.assertRaises(LicenseError):
            mgr.verify_asset("random_unverified_copyrighted_song.mp3")

    def test_audio_manager_sfx_cache_and_lookup(self):
        mgr = AudioManager()
        # Verify cache is lazy loaded
        self.assertIsNone(mgr._imported_sfx_index)

        # 1. Manifest lookup works
        path_manifest = mgr.get_sfx("sfx_knock_door")
        self.assertTrue(path_manifest.is_file())
        self.assertTrue(path_manifest.name.endswith(".wav"))

        # 2. Imported lookup works and populates cache
        imported_index = mgr._get_imported_sfx_index()
        self.assertIsNotNone(mgr._imported_sfx_index)
        self.assertIsInstance(imported_index, dict)

        if len(imported_index) > 0:
            sfx_stem = next(iter(imported_index))
            path1 = mgr.get_sfx(sfx_stem)
            self.assertTrue(path1.is_file())
            self.assertIs(mgr._imported_sfx_index, imported_index)
            path2 = mgr.get_sfx(f"{sfx_stem}.mp3")
            self.assertEqual(path1, path2)

        # Clear cache works
        mgr.clear_sfx_cache()
        self.assertIsNone(mgr._imported_sfx_index)

    def test_audio_manager_missing_directory_and_duplicates(self):
        import tempfile
        import json
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            dummy_licenses = tmp_path / "assets" / "licenses.json"
            dummy_licenses.parent.mkdir(parents=True)
            dummy_licenses.write_text(json.dumps({"verified_assets": {}}), encoding="utf-8")

            mgr = AudioManager(dummy_licenses)
            # Directory does not exist -> safely returns empty dict
            index = mgr._get_imported_sfx_index()
            self.assertEqual(index, {})

            # Unknown asset raises LicenseError
            with self.assertRaises(LicenseError):
                mgr.get_sfx("nonexistent_sound")

            # Duplicate stems handling
            mock_sfx_dir = tmp_path / "assets" / "imported" / "stickman_animation" / "skills" / "vox-doc-sound" / "sfx"
            sub1 = mock_sfx_dir / "folder_a"
            sub2 = mock_sfx_dir / "folder_b"
            sub1.mkdir(parents=True)
            sub2.mkdir(parents=True)
            file1 = sub1 / "test_hit.mp3"
            file2 = sub2 / "test_hit.wav"
            file1.write_text("audio1")
            file2.write_text("audio2")

            mgr.clear_sfx_cache()
            built = mgr._get_imported_sfx_index()
            self.assertIn("test_hit", built)
            # Deterministic: folder_a comes before folder_b alphabetically
            self.assertEqual(built["test_hit"], file1.resolve())
            resolved = mgr.get_sfx("test_hit")
            self.assertEqual(resolved, file1.resolve())

    def test_prompt_builder(self):
        scenes_data = [
            {
                "title": "Opening",
                "narration": "You stand on the balcony.",
                "visual_description": "Stickman looking at dark city.",
                "camera_movement": "zoom_in",
                "sfx_cue": "sfx_alarm"
            }
        ]
        prompts = build_prompts_from_scenes(scenes_data)
        self.assertEqual(len(prompts), 1)
        p = prompts[0]
        self.assertEqual(p.scene_index, 1)
        self.assertIn("brick-red ribbed knit beanie", p.full_prompt())
        self.assertIn("Stickman looking at dark city", p.full_prompt())

    def test_story_generation(self):
        story = generate_story("Night in the Tower")
        self.assertIn("scenes", story)
        self.assertGreaterEqual(len(story["scenes"]), 3)
        for s in story["scenes"]:
            self.assertIn("narration", s)
            self.assertIn("visual_description", s)

    def test_flow_client_quota(self):
        client = FlowClient()
        quota = client.get_remaining_quota()
        self.assertTrue(0 <= quota <= client.daily_limit)


    def test_auto_story_generation(self):
        from storyforge.story_gen import generate_auto_story
        story = generate_auto_story()
        self.assertIn("story_title", story)
        self.assertIn("scenes", story)
        self.assertGreaterEqual(len(story["scenes"]), 4)

    def test_horizontal_subtitle_styling(self):
        from storyforge.narration import _write_styled_ass
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".ass", delete=False) as tf:
            p = Path(tf.name)
        try:
            _write_styled_ass(["Dialogue: 0,0:00:01.00,0:00:03.00,Default,,0,0,0,,Test Line"], p, aspect_ratio="16:9")
            content = p.read_text(encoding="utf-8")
            self.assertIn("PlayResX: 1920", content)
            self.assertIn("PlayResY: 1080", content)
            self.assertIn("MarginV, Encoding", content)
        finally:
            if p.exists():
                p.unlink()


if __name__ == "__main__":
    unittest.main()
