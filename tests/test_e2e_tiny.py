"""Tiny offline End-to-End video assembly test.

Renders 2 scenes (3 seconds total) using synthetic placeholder images and audio,
verifying complete FFmpeg rendering, stream codecs, and decode integrity in < 10 seconds.
No external network, Whisper, LaMa, Flow, or OmniVoice required.
"""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from scenecraft.audio_manager import AudioManager
from scenecraft.pipeline import verify_video
from scenecraft.video_engine import VideoEngine


class TestTinyE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            raise unittest.SkipTest("FFmpeg/FFprobe system binary required for E2E video rendering test.")

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="scenecraft_e2e_"))

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_tiny_e2e_render_and_verification(self):
        """Render a real 2-scene 3-second MP4 video and verify decode integrity."""
        # 1. Create two 1080x1920 solid-color images
        img1_p = self.test_dir / "scene_01.png"
        img2_p = self.test_dir / "scene_02.png"
        Image.new("RGB", (1080, 1920), color=(30, 40, 60)).save(img1_p)
        Image.new("RGB", (1080, 1920), color=(60, 40, 30)).save(img2_p)

        # 2. Generate a 3-second test WAV audio using FFmpeg
        audio_p = self.test_dir / "narration.wav"
        subprocess.run(
            [
                "ffmpeg", "-y", "-v", "error",
                "-f", "lavfi", "-i", "sine=frequency=440:duration=3.0",
                "-ar", "44100", "-ac", "2",
                str(audio_p)
            ],
            check=True
        )

        # 3. Render 2 scene clips (1.5 seconds each) using VideoEngine
        engine = VideoEngine(AudioManager())
        clip1_p = self.test_dir / "clip_01.mp4"
        clip2_p = self.test_dir / "clip_02.mp4"

        engine.render_scene_clip(
            image_path=img1_p,
            duration=1.5,
            out_clip=clip1_p,
            movement="slow_push_in",
            width=1080,
            height=1920,
            apply_effects=False
        )
        self.assertTrue(clip1_p.is_file(), "Clip 1 failed to render")

        engine.render_scene_clip(
            image_path=img2_p,
            duration=1.5,
            out_clip=clip2_p,
            movement="static_hold",
            width=1080,
            height=1920,
            apply_effects=False
        )
        self.assertTrue(clip2_p.is_file(), "Clip 2 failed to render")

        # 4. Concatenate clips into final master video with audio
        concat_txt = self.test_dir / "concat.txt"
        concat_txt.write_text(f"file '{clip1_p.as_posix()}'\nfile '{clip2_p.as_posix()}'\n", encoding="utf-8")

        final_mp4 = self.test_dir / "final_short.mp4"
        cmd = [
            "ffmpeg", "-y", "-v", "error",
            "-f", "concat", "-safe", "0", "-i", str(concat_txt),
            "-i", str(audio_p),
            "-c:v", "libx264", "-preset", "ultrafast",
            "-c:a", "aac", "-b:a", "128k",
            "-shortest",
            str(final_mp4)
        ]
        subprocess.run(cmd, check=True)
        self.assertTrue(final_mp4.is_file(), "Final MP4 failed to produce")

        # 5. Validate output using Scenecraft stream integrity verifier
        meta = verify_video(final_mp4)
        self.assertAlmostEqual(meta["duration"], 3.0, delta=0.5)
        self.assertEqual(meta["width"], 1080)
        self.assertEqual(meta["height"], 1920)
        self.assertEqual(meta["video_codec"], "h264")
        self.assertEqual(meta["audio_codec"], "aac")


if __name__ == "__main__":
    unittest.main()
