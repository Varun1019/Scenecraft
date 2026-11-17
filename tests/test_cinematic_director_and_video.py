"""Unit and integration tests for Cinematic Scene Director, VideoEngine motions, and Dual-Format Thumbnails."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from storyforge.scene_director import SceneDirector, CINEMATIC_SHOTS, SUPPORTED_MOVEMENTS
from storyforge.video_engine import VideoEngine
from storyforge.thumbnail_generator import ThumbnailGenerator


class TestCinematicDirectorAndVideo(unittest.TestCase):

    def setUp(self):
        self.test_scenes = [
            {
                "scene_index": 1,
                "title": "The Rooftop Survivor - Hook",
                "narration": "They told us the bunker was safe, but the ground beneath us didn't agree.",
                "visual_description": "The Wanderer standing atop a crumbling concrete roof, looking out over a desolate twilight skyline.",
                "emotion": "SUSPENSE",
            },
            {
                "scene_index": 2,
                "title": "The Warning Static",
                "narration": "My portable radio crackled with three words: do not enter.",
                "visual_description": "Close-up of The Wanderer holding a scratched two-way radio, glowing red indicator lights reflecting on his beanie.",
                "emotion": "MYSTERY",
            },
            {
                "scene_index": 3,
                "title": "The Approaching Front",
                "narration": "A towering wall of chemical dust swallowed thirty city blocks in seconds.",
                "visual_description": "Colossal storm front of toxic dust surging across the horizon beneath a dark amber sky.",
                "emotion": "PANIC",
            },
            {
                "scene_index": 4,
                "title": "The Sealed Hatch",
                "narration": "The emergency ladder ended at an iron hatch. The padlock was unlatched.",
                "visual_description": "Looking down at a weathered hatch door with a heavy iron padlock hanging open.",
                "emotion": "SHOCK",
            },
            {
                "scene_index": 5,
                "title": "The Discovery",
                "narration": "Someone had climbed inside only minutes before.",
                "visual_description": "The Wanderer leaning into the hatch opening, eyes wide, looking into the darkness below.",
                "emotion": "REVEAL",
            },
        ]

    def test_scene_director_shot_and_motion_variety(self):
        """SceneDirector must guarantee shot and camera movement variation without consecutive repeats."""
        director = SceneDirector(style_preset="earthy_explainer")
        beats = director.plan_sequence(self.test_scenes, aspect_ratio="9:16")

        self.assertEqual(len(beats), 5)

        shot_types = [b.shot_type for b in beats]
        cam_moves = [b.camera_movement for b in beats]
        transitions = [b.transition_to_next for b in beats]

        # Verify all shots are recognized
        for st in shot_types:
            self.assertIn(st, CINEMATIC_SHOTS, f"Invalid shot type: {st}")

        # Verify all movements are supported
        for cm in cam_moves:
            self.assertIn(cm, SUPPORTED_MOVEMENTS, f"Invalid camera movement: {cm}")

        # Repetition Guard: NO consecutive identical shots
        for i in range(len(shot_types) - 1):
            self.assertNotEqual(
                shot_types[i], shot_types[i + 1],
                f"Consecutive identical shot detected at scene {i+1} and {i+2}: {shot_types[i]}"
            )

        # Repetition Guard: NO consecutive identical camera movements
        for i in range(len(cam_moves) - 1):
            self.assertNotEqual(
                cam_moves[i], cam_moves[i + 1],
                f"Consecutive identical camera movement detected at scene {i+1} and {i+2}: {cam_moves[i]}"
            )

        # Shot variety: at least 3 distinct shot types across 5 scenes
        self.assertGreaterEqual(len(set(shot_types)), 3)
        # Movement variety: at least 3 distinct movements across 5 scenes
        self.assertGreaterEqual(len(set(cam_moves)), 3)

        # Transition validation
        for tr in transitions:
            self.assertIn(tr, ["hard_cut", "crossfade", "dip_to_black"])

    def test_video_engine_nvenc_detection(self):
        """VideoEngine must probe for NVENC support and expose nvenc_available boolean."""
        engine = VideoEngine()
        self.assertIsInstance(engine.nvenc_available, bool)

    @patch("subprocess.run")
    def test_video_engine_motion_filter_generation(self, mock_run):
        """VideoEngine.render_scene_clip must generate valid FFmpeg filter strings for all motions."""
        mock_run.return_value = MagicMock(returncode=0)
        engine = VideoEngine()
        engine.nvenc_available = False

        motions = [
            ("slow_push_in", "zoom+0.0008"),
            ("fast_push_in", "zoom+0.0022"),
            ("pull_back", "zoom-0.0014"),
            ("pan_left", "1-on/"),
            ("pan_right", "on/"),
            ("pan_up", "1-on/"),
            ("pan_down", "on/"),
            ("subtle_drift", "zoom+0.0004"),
            ("static_hold", "1.04"),
        ]

        dummy_img = Path("/tmp/dummy_image.jpg")
        dummy_out = Path("/tmp/dummy_clip.mp4")

        for mov, expected_sub in motions:
            mock_run.reset_mock()
            engine.render_scene_clip(
                image_path=dummy_img,
                duration=3.0,
                out_clip=dummy_out,
                movement=mov,
                subject_position="rule_of_thirds_left",
                transition_in="crossfade",
                transition_out="dip_to_black",
                apply_effects=True,
            )
            self.assertTrue(mock_run.called)
            cmd = mock_run.call_args[0][0]
            cmd_str = " ".join(cmd)
            self.assertIn("-vf", cmd)
            vf_idx = cmd.index("-vf")
            vf_filter = cmd[vf_idx + 1]
            self.assertIn(expected_sub, vf_filter, f"Movement {mov} missing expression {expected_sub}")
            self.assertIn("fade=t=in", vf_filter)
            self.assertIn("fade=t=out", vf_filter)

    def test_thumbnail_generator_dual_format_renders(self):
        """ThumbnailGenerator must render high-contrast local fallback compositions for 9:16 and 16:9."""
        thumb_gen = ThumbnailGenerator()

        with tempfile.TemporaryDirectory() as td:
            temp_dir = Path(td)
            thumb_916 = temp_dir / "thumb_916.png"
            thumb_169 = temp_dir / "thumb_169.png"

            # Render 9:16 thumbnail
            thumb_gen.generate_thumbnail(
                prompt="The Wanderer holding unlatched padlock atop bunker roof",
                output_path=thumb_916,
                title_hook="THE ROOFTOP SURVIVOR",
                aspect_ratio="9:16",
                style_preset="earthy_explainer",
                use_flow=False,
            )
            self.assertTrue(thumb_916.is_file(), "9:16 thumbnail was not created")
            self.assertGreater(thumb_916.stat().st_size, 1024, "9:16 thumbnail file is empty or corrupted")

            # Render 16:9 thumbnail
            thumb_gen.generate_thumbnail(
                prompt="The Wanderer holding unlatched padlock atop bunker roof",
                output_path=thumb_169,
                title_hook="THE ROOFTOP SURVIVOR",
                aspect_ratio="16:9",
                style_preset="earthy_explainer",
                use_flow=False,
            )
            self.assertTrue(thumb_169.is_file(), "16:9 thumbnail was not created")
            self.assertGreater(thumb_169.stat().st_size, 1024, "16:9 thumbnail file is empty or corrupted")


if __name__ == "__main__":
    unittest.main()
