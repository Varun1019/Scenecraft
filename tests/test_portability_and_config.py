"""Tests for configuration, Windows path escaping, cleaner, doctor, and TTS fallback."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from scenecraft.config import ScenecraftConfig, get_config
from scenecraft.doctor import SystemDoctor
from scenecraft.tts import get_tts_engine
from scenecraft.video_engine import escape_ffmpeg_filter_path


class TestConfig(unittest.TestCase):
    def test_default_config(self):
        cfg = ScenecraftConfig()
        self.assertEqual(cfg.video_width, 1080)
        self.assertEqual(cfg.video_height, 1920)
        self.assertEqual(cfg.fps, 30)
        self.assertEqual(cfg.voice_id, "6f7af622")
        self.assertEqual(cfg.encoder, "auto")

    def test_config_env_override(self):
        with patch.dict(os.environ, {"SCENECRAFT_VOICE_ID": "test_voice_99", "SCENECRAFT_FPS": "60"}):
            cfg = ScenecraftConfig.load()
            self.assertEqual(cfg.voice_id, "test_voice_99")
            self.assertEqual(cfg.fps, 60)


class TestWindowsPathEscaping(unittest.TestCase):
    def test_posix_path(self):
        p = "/tmp/subtitles/sub.ass"
        escaped = escape_ffmpeg_filter_path(p)
        self.assertEqual(escaped, "/tmp/subtitles/sub.ass")

    def test_windows_drive_letter_and_spaces_escaping(self):
        # Emulate Windows path with drive colon, backslashes, and spaces
        win_path = r"C:\Users\John Doe\Videos\subtitles.ass"
        escaped = escape_ffmpeg_filter_path(win_path)
        expected = "C\\:/Users/John Doe/Videos/subtitles.ass"
        self.assertEqual(escaped, expected)

        # Confirm filter string construction does not conflict quoting with spaces
        filter_str = f"ass=filename='{escaped}'"
        expected_filter = "ass=filename='C\\:/Users/John Doe/Videos/subtitles.ass'"
        self.assertEqual(filter_str, expected_filter)


class TestCleanerCorners(unittest.TestCase):
    def test_cleaner_options(self):
        from scenecraft.cleaner import CleanerOptions
        opts_br = CleanerOptions(corner="bottom-right")
        self.assertEqual(opts_br.corner, "bottom-right")
        opts_tl = CleanerOptions(corner="top-left")
        self.assertEqual(opts_tl.corner, "top-left")

    def test_watermark_box_calculation(self):
        from scenecraft.cleaner import corner_box
        box_br = corner_box(1080, 1920, "bottom-right", 0.15, 0.08, 0.01)
        self.assertGreater(box_br[0], 0)
        self.assertGreater(box_br[1], 0)
        self.assertEqual(box_br[2], 1080)
        self.assertEqual(box_br[3], 1920)


class TestDoctorChecks(unittest.TestCase):
    def test_system_doctor_all_checks(self):
        doc = SystemDoctor()
        checks = doc.run_all_checks()
        self.assertGreaterEqual(len(checks), 8)
        report = doc.format_report()
        self.assertIn("SCENECRAFT SYSTEM DIAGNOSTICS & DOCTOR", report)


class TestTTSFallback(unittest.TestCase):
    def test_get_tts_engine(self):
        engine = get_tts_engine("edge_tts")
        self.assertIsNotNone(engine)

    @patch("urllib.request.urlopen")
    def test_omnivoice_fallback_to_edge_when_offline(self, mock_urlopen):
        mock_urlopen.side_effect = Exception("Connection refused")
        from scenecraft.tts.omnivoice import OmniVoiceTTS
        engine = OmniVoiceTTS(base_url="http://127.0.0.1:9999")
        self.assertFalse(engine.is_available())


if __name__ == "__main__":
    unittest.main()
