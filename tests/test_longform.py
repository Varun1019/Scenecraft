"""Tests for Scenecraft long-form AI video production engine."""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from scenecraft.story_engine_longform import LongformStoryEngine, LongformStoryPlan, LongformSceneBeat
from scenecraft.flow_client import FlowClient, FlowConnectionError, SUPPORTED_FLOW_VIDEO_MODELS
from scenecraft.video_engine import VideoEngine, EXPORT_PROFILE_LANDSCAPE, EXPORT_PROFILE_VERTICAL
from scenecraft.shorts_extractor import ShortsExtractor
from scenecraft.thumbnail_generator import ThumbnailGenerator
from scenecraft.pipeline_longform import LongformPipeline


class TestLongformStoryEngine(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.engine = LongformStoryEngine(workspace_dir=Path(self.temp_dir))

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_generate_plan_structure(self):
        plan = self.engine.generate_plan(
            theme="You are trapped inside a supermarket during a zombie apocalypse",
            genre="zombie_apocalypse",
            target_minutes=15,
        )
        self.assertIsInstance(plan, LongformStoryPlan)
        self.assertGreaterEqual(len(plan.scenes), 16)
        self.assertIn("supermarket", plan.premise.lower())
        self.assertTrue(len(plan.opening_hook_narration) > 50)
        self.assertTrue(len(plan.cliffhanger) > 20)
        self.assertGreater(plan.total_estimated_duration, 60.0)

        # Check scene attributes
        first_scene = plan.scenes[0]
        self.assertEqual(first_scene.act, "Act I: Containment")
        self.assertIn("16:9", first_scene.video_prompt)
        self.assertGreater(first_scene.target_duration, 0)

        # Check short candidate detection
        short_candidates = [s for s in plan.scenes if s.is_short_candidate]
        self.assertGreaterEqual(len(short_candidates), 2)

    def test_serialization(self):
        plan = self.engine.generate_plan(target_minutes=10)
        out_json = Path(self.temp_dir) / "test_plan.json"
        plan.to_json(out_json)
        self.assertTrue(out_json.is_file())

        loaded = LongformStoryPlan.from_dict(json.loads(out_json.read_text(encoding="utf-8")))
        self.assertEqual(loaded.title, plan.title)
        self.assertEqual(len(loaded.scenes), len(plan.scenes))


class TestFlowVideoModelsAndValidation(unittest.TestCase):
    def setUp(self):
        self.client = FlowClient()

    def test_supported_models(self):
        self.assertIn("omni-flash", SUPPORTED_FLOW_VIDEO_MODELS)
        self.assertIn("veo-3.1-lite", SUPPORTED_FLOW_VIDEO_MODELS)
        self.assertIn("veo-3.1-fast", SUPPORTED_FLOW_VIDEO_MODELS)
        self.assertIn("veo-3.1-quality", SUPPORTED_FLOW_VIDEO_MODELS)

    def test_invalid_model_rejected(self):
        with self.assertRaises(FlowConnectionError) as ctx:
            self.client.generate_video(
                prompt="Test prompt",
                output_path=Path(tempfile.gettempdir()) / "nonexistent.mp4",
                model="imaginary-super-video-v99",
            )
        self.assertIn("Unsupported Flow video model", str(ctx.exception))


class TestVideoFormattingAndProfiles(unittest.TestCase):
    def test_export_profiles(self):
        self.assertEqual(EXPORT_PROFILE_LANDSCAPE["width"], 1920)
        self.assertEqual(EXPORT_PROFILE_LANDSCAPE["height"], 1080)
        self.assertEqual(EXPORT_PROFILE_LANDSCAPE["aspect_ratio"], "16:9")

        self.assertEqual(EXPORT_PROFILE_VERTICAL["width"], 1080)
        self.assertEqual(EXPORT_PROFILE_VERTICAL["height"], 1920)
        self.assertEqual(EXPORT_PROFILE_VERTICAL["aspect_ratio"], "9:16")


class TestShortsExtractor(unittest.TestCase):
    def setUp(self):
        self.extractor = ShortsExtractor()
        self.scenes = [
            {"scene_index": 1, "title": "S1", "narration": "Hook 1", "duration": 6.0, "is_short_candidate": True, "short_hook": "Hook A", "start_time": 0.0},
            {"scene_index": 2, "title": "S2", "narration": "Action 2", "duration": 6.0, "is_short_candidate": False, "start_time": 6.0},
            {"scene_index": 3, "title": "S3", "narration": "Action 3", "duration": 6.0, "is_short_candidate": False, "start_time": 12.0},
            {"scene_index": 4, "title": "S4", "narration": "Action 4", "duration": 6.0, "is_short_candidate": False, "start_time": 18.0},
            {"scene_index": 5, "title": "S5", "narration": "Action 5", "duration": 6.0, "is_short_candidate": False, "start_time": 24.0},
            {"scene_index": 6, "title": "S6", "narration": "Climax 6", "duration": 6.0, "is_short_candidate": True, "short_hook": "Hook B", "start_time": 30.0},
            {"scene_index": 7, "title": "S7", "narration": "Climax 7", "duration": 6.0, "is_short_candidate": False, "start_time": 36.0},
            {"scene_index": 8, "title": "S8", "narration": "Climax 8", "duration": 6.0, "is_short_candidate": False, "start_time": 42.0},
        ]

    def test_candidate_selection(self):
        candidates = self.extractor.select_short_candidates(self.scenes, target_count=2, min_duration=24.0)
        self.assertGreaterEqual(len(candidates), 1)
        for cand in candidates:
            self.assertGreaterEqual(cand["duration"], 24.0)
            self.assertIsNotNone(cand["hook"])
            self.assertIsNotNone(cand["cliffhanger"])


class TestThumbnailGenerator(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.gen = ThumbnailGenerator()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_fallback_thumbnail_rendering(self):
        out_path = Path(self.temp_dir) / "thumb_test.png"
        self.gen.generate_thumbnail(
            prompt="Trapped survivor in dark supermarket",
            output_path=out_path,
            title_hook="NO ESCAPE",
            use_flow=False,
        )
        self.assertTrue(out_path.is_file())
        self.assertGreater(out_path.stat().st_size, 5000)


class TestPipelineResumeAndStructure(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.pipeline = LongformPipeline(workspace_dir=Path(self.temp_dir))

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_pipeline_dry_run_with_mock_clips(self):
        # Test full production directory structure creation with mock clips for fast offline verification
        project_dir = self.pipeline.produce(
            theme="Test Supermarket Apocalypse",
            genre="survival_horror",
            duration_minutes=1,  # Fast 1-min test
            project_name="test_prod_run",
            use_mock_video_if_flow_offline=True,
            max_scenes=4,
        )
        self.assertTrue(project_dir.is_dir())

        # Verify all standardized subdirectories exist
        expected_subdirs = ["story", "video", "audio", "shorts", "thumbnail", "metadata"]
        for sd in expected_subdirs:
            self.assertTrue((project_dir / sd).is_dir(), f"Missing directory: {sd}")

        # Verify expected files
        self.assertTrue((project_dir / "story" / "script.txt").is_file())
        self.assertTrue((project_dir / "story" / "scene_breakdown.json").is_file())
        self.assertTrue((project_dir / "video" / "master_video.mp4").is_file())
        self.assertTrue((project_dir / "thumbnail" / "thumbnail.png").is_file())
        self.assertTrue((project_dir / "metadata" / "title.txt").is_file())

        # Verify Shorts extracted
        shorts_files = list((project_dir / "shorts").glob("*.mp4"))
        self.assertGreaterEqual(len(shorts_files), 1)


if __name__ == "__main__":
    unittest.main()
