"""Unit tests for VoiceStudio integration in Scenecraft."""

import unittest
from pathlib import Path
from scenecraft.voicestudio_client import VoiceStudioClient
from scenecraft.narration import synthesize_scene_narration, get_audio_duration


class TestVoiceStudioIntegration(unittest.TestCase):
    def setUp(self):
        self.client = VoiceStudioClient()
        self.test_dir = Path("/tmp/scenecraft_voicestudio_tests")
        self.test_dir.mkdir(parents=True, exist_ok=True)

    def test_client_init(self):
        self.assertTrue(self.client.base_url.startswith("http"))

    def test_health_and_availability(self):
        if not self.client.is_available():
            self.skipTest("VoiceStudio server not running on port 3900")

        health = self.client.get_health()
        self.assertEqual(health.get("status"), "ok")
        self.assertIn("device", health)
        self.assertIn("version", health)

    def test_list_profiles(self):
        if not self.client.is_available():
            self.skipTest("VoiceStudio server not running on port 3900")

        profiles = self.client.list_profiles()
        self.assertIsInstance(profiles, list)
        self.assertGreaterEqual(len(profiles), 1)
        profile_ids = [p["id"] for p in profiles]
        self.assertIn("demo0001", profile_ids)

    def test_direct_speech_generation(self):
        if not self.client.is_available():
            self.skipTest("VoiceStudio server not running on port 3900")

        out_wav = self.test_dir / "direct_speech.wav"
        if out_wav.exists():
            out_wav.unlink()

        dur = self.client.generate_speech(
            text="Testing Voice Studio direct synthesis.",
            output_path=out_wav,
            voice="default",
            model="tts-1",
            response_format="wav",
        )
        self.assertTrue(out_wav.is_file())
        self.assertGreater(out_wav.stat().st_size, 1000)
        self.assertGreater(dur, 0.5)

    def test_narration_synthesize_scene(self):
        if not self.client.is_available():
            self.skipTest("VoiceStudio server not running on port 3900")

        out_audio = self.test_dir / "scene_vs.wav"
        out_vtt = self.test_dir / "scene_vs.vtt"
        for p in (out_audio, out_vtt):
            if p.exists():
                p.unlink()

        dur = synthesize_scene_narration(
            text="The elevator stopped on a floor that should not exist.",
            out_audio=out_audio,
            out_vtt=out_vtt,
            voice="voicestudio:demo0001",
        )
        self.assertTrue(out_audio.is_file())
        self.assertTrue(out_vtt.is_file())
        self.assertGreater(dur, 1.0)
        vtt_content = out_vtt.read_text(encoding="utf-8")
        self.assertTrue(vtt_content.startswith("WEBVTT"))
        self.assertIn("elevator", vtt_content)

    def test_permanent_narrator_locked_config(self):
        from scenecraft.voicestudio_client import get_permanent_narrator_config
        cfg = get_permanent_narrator_config()
        self.assertEqual(cfg["voice_id"], "6f7af622")
        self.assertEqual(cfg["engine"], "omnivoice")
        self.assertEqual(cfg["seed"], 42101)
        self.assertEqual(cfg["default_speed"], 0.90)
        self.assertTrue(cfg.get("locked", False))

    def test_delivery_params_modulation(self):
        from scenecraft.voicestudio_client import get_scene_delivery_params
        # Escalation / Panic -> slightly faster (0.97x with base 0.90x)
        p_panic = get_scene_delivery_params(emotion="PANIC", tension_level=8)
        self.assertEqual(p_panic["speed"], 0.97)
        self.assertIn("Urgent", p_panic["instructions"])

        # Reveal / Climax -> slower (0.86x with base 0.90x)
        p_shock = get_scene_delivery_params(emotion="SHOCK", tension_level=9)
        self.assertEqual(p_shock["speed"], 0.86)
        self.assertIn("Deliberate", p_shock["instructions"])

        # Conversational / Baseline -> default 0.90x
        p_conv = get_scene_delivery_params(emotion="CONVERSATIONAL", tension_level=4)
        self.assertEqual(p_conv["speed"], 0.90)
        self.assertIn("conversational", p_conv["instructions"].lower())

    def test_speed_and_expressive_delivery_execution(self):
        if not self.client.is_available():
            self.skipTest("VoiceStudio server not running on port 3900")

        # Test baseline speed 0.88x vs escalation 0.95x
        txt = "Never check the peephole at 3:17 AM."
        out_base = self.test_dir / "test_spd_088.wav"
        out_fast = self.test_dir / "test_spd_095.wav"

        dur_base = self.client.generate_speech(text=txt, output_path=out_base, voice="default", speed=0.88)
        dur_fast = self.client.generate_speech(text=txt, output_path=out_fast, voice="default", speed=0.95)

        self.assertTrue(out_base.is_file())
        self.assertTrue(out_fast.is_file())
        self.assertGreater(dur_base, 0.5)
        self.assertGreater(dur_fast, 0.5)


if __name__ == "__main__":
    unittest.main()
