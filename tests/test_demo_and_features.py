"""Tests for Scenecraft demo, project init, images-dir ingestion, and state resume."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from PIL import Image

from scenecraft.demo_cmd import run_demo
from scenecraft.init_cmd import run_init
from scenecraft.pipeline import ScenecraftPipeline, load_pipeline_state, save_pipeline_state


class TestDemoCommand(unittest.TestCase):
    """Test scenecraft demo runs 100% offline using bundled assets."""

    def test_run_demo_creates_valid_video(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            code = run_demo(out_dir=tmpdir, quiet=True)
            self.assertEqual(code, 0)
            mp4_path = Path(tmpdir) / "demo_video.mp4"
            self.assertTrue(mp4_path.is_file())
            self.assertGreater(mp4_path.stat().st_size, 1000)


class TestInitCommand(unittest.TestCase):
    """Test project scaffolding via scenecraft init."""

    def test_run_init_scaffolds_project(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            code = run_init(name="test_bunker", target_dir=tmpdir)
            self.assertEqual(code, 0)

            proj_dir = Path(tmpdir) / "test_bunker"
            self.assertTrue(proj_dir.is_dir())
            self.assertTrue((proj_dir / "project.json").is_file())
            self.assertTrue((proj_dir / "README.md").is_file())
            self.assertTrue((proj_dir / "images").is_dir())
            self.assertTrue((proj_dir / "scripts" / "story_script.txt").is_file())

            # Validate json contents
            with open(proj_dir / "project.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(len(data.get("scenes", [])), 3)


class TestPipelineFeatures(unittest.TestCase):
    """Test dry-run, images-dir ingestion, and state resume."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)
        self.project_data = {
            "title": "Unit Test Story",
            "genre": "survival",
            "aspect_ratio": "9:16",
            "scenes": [
                {
                    "scene_index": 1,
                    "title": "Scene 1",
                    "narration": "First scene narration.",
                    "visual_description": "First visual beat.",
                    "duration": 3.0,
                },
                {
                    "scene_index": 2,
                    "title": "Scene 2",
                    "narration": "Second scene narration.",
                    "visual_description": "Second visual beat.",
                    "duration": 3.0,
                }
            ]
        }
        self.project_file = self.tmp_path / "project.json"
        with open(self.project_file, "w", encoding="utf-8") as f:
            json.dump(self.project_data, f, indent=2)

    def tearDown(self):
        self.tmp.cleanup()

    def test_pipeline_dry_run(self):
        pipeline = ScenecraftPipeline(
            workspace_dir=self.tmp_path,
            dry_run=True,
            quiet=True,
        )
        res = pipeline.run_plan(self.project_file)
        self.assertTrue(res.get("dry_run"))
        self.assertEqual(res.get("title"), "Unit Test Story")

    def test_pipeline_images_dir_ingestion(self):
        # Create custom images directory with 2 dummy images
        custom_images = self.tmp_path / "custom_imgs"
        custom_images.mkdir()
        for idx in (1, 2):
            img = Image.new("RGB", (100, 100), color=(idx * 50, idx * 50, idx * 50))
            img.save(custom_images / f"scene_{idx:02d}.jpg")

        pipeline = ScenecraftPipeline(
            workspace_dir=self.tmp_path,
            images_dir=custom_images,
            dry_run=True,
            quiet=True,
        )
        res = pipeline.run_plan(self.project_file)
        self.assertTrue(res.get("dry_run"))

    def test_state_load_and_save(self):
        bundle = self.tmp_path / "test_bundle"
        bundle.mkdir()
        save_pipeline_state(bundle, {"narration": True, "visuals": True})
        loaded = load_pipeline_state(bundle)
        self.assertTrue(loaded.get("narration"))
        self.assertTrue(loaded.get("visuals"))
        self.assertFalse(loaded.get("assembly", False))


if __name__ == "__main__":
    unittest.main()
