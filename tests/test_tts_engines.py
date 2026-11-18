"""Tests for Scenecraft TTS engines, auto fallback, and voices command."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from scenecraft.tts import (
    AutoFallbackTTS,
    EdgeTTS,
    ElevenLabsTTS,
    KokoroTTS,
    OmniVoiceTTS,
    OpenAITTS,
    PiperTTS,
    get_tts_engine,
)
from scenecraft.voices_cmd import run_voices


class TestTTSEngineRegistry(unittest.TestCase):
    """Test registry retrieval for all supported engines."""

    def test_get_auto_engine(self):
        engine = get_tts_engine("auto")
        self.assertIsInstance(engine, AutoFallbackTTS)

    def test_get_explicit_engines(self):
        self.assertIsInstance(get_tts_engine("kokoro"), KokoroTTS)
        self.assertIsInstance(get_tts_engine("edge_tts"), EdgeTTS)
        self.assertIsInstance(get_tts_engine("edge-tts"), EdgeTTS)
        self.assertIsInstance(get_tts_engine("piper"), PiperTTS)
        self.assertIsInstance(get_tts_engine("omnivoice"), OmniVoiceTTS)
        self.assertIsInstance(get_tts_engine("elevenlabs"), ElevenLabsTTS)
        self.assertIsInstance(get_tts_engine("openai"), OpenAITTS)

    def test_unknown_engine_raises_value_error(self):
        with self.assertRaises(ValueError):
            get_tts_engine("nonexistent_tts_engine")


class TestAutoFallbackTTS(unittest.TestCase):
    """Test priority order (OmniVoice -> Kokoro -> Edge-TTS) and runtime fallback."""

    def test_prefers_omnivoice_when_available(self):
        omni = MagicMock(spec=OmniVoiceTTS)
        omni.engine_name = "omnivoice"
        omni.is_available.return_value = True
        omni.generate.return_value = 2.5

        kokoro = MagicMock(spec=KokoroTTS)
        kokoro.engine_name = "kokoro"
        kokoro.is_available.return_value = True

        edge = MagicMock(spec=EdgeTTS)
        edge.engine_name = "edge-tts"
        edge.is_available.return_value = True

        fallback = AutoFallbackTTS()
        fallback.priority_engines = [
            ("omnivoice", omni, "OmniVoice"),
            ("kokoro", kokoro, "Kokoro"),
            ("edge-tts", edge, "Edge-TTS"),
        ]

        self.assertTrue(fallback.is_available())
        name, active, _ = fallback.resolve_best_engine()
        self.assertEqual(name, "omnivoice")
        self.assertEqual(active, omni)

        dur = fallback.generate("hello", Path("/fake/out.wav"))
        self.assertEqual(dur, 2.5)
        omni.generate.assert_called_once()
        kokoro.generate.assert_not_called()

    def test_falls_back_to_kokoro_when_omni_unavailable(self):
        omni = MagicMock(spec=OmniVoiceTTS)
        omni.engine_name = "omnivoice"
        omni.is_available.return_value = False

        kokoro = MagicMock(spec=KokoroTTS)
        kokoro.engine_name = "kokoro"
        kokoro.is_available.return_value = True
        kokoro.generate.return_value = 3.0

        edge = MagicMock(spec=EdgeTTS)
        edge.engine_name = "edge-tts"
        edge.is_available.return_value = True

        fallback = AutoFallbackTTS()
        fallback.priority_engines = [
            ("omnivoice", omni, "OmniVoice"),
            ("kokoro", kokoro, "Kokoro"),
            ("edge-tts", edge, "Edge-TTS"),
        ]

        name, active, _ = fallback.resolve_best_engine()
        self.assertEqual(name, "kokoro")
        self.assertEqual(active, kokoro)

        dur = fallback.generate("hello", Path("/fake/out.wav"))
        self.assertEqual(dur, 3.0)
        kokoro.generate.assert_called_once()

    def test_falls_back_at_runtime_if_primary_fails(self):
        primary = MagicMock(spec=KokoroTTS)
        primary.engine_name = "kokoro"
        primary.is_available.return_value = True
        primary.generate.side_effect = RuntimeError("Kokoro model inference failed")

        secondary = MagicMock(spec=EdgeTTS)
        secondary.engine_name = "edge-tts"
        secondary.is_available.return_value = True
        secondary.generate.return_value = 1.8

        fallback = AutoFallbackTTS()
        fallback.priority_engines = [
            ("kokoro", primary, "Kokoro"),
            ("edge-tts", secondary, "Edge-TTS"),
        ]

        dur = fallback.generate("hello", Path("/fake/out.wav"))
        self.assertEqual(dur, 1.8)
        primary.generate.assert_called_once()
        secondary.generate.assert_called_once()


class TestCloudEnginesEnvKeys(unittest.TestCase):
    """Ensure ElevenLabs and OpenAI read only from env and give friendly errors."""

    def test_elevenlabs_missing_key(self):
        with patch.dict(os.environ, {}, clear=True):
            engine = ElevenLabsTTS()
            self.assertFalse(engine.is_available())
            with self.assertRaises(RuntimeError) as ctx:
                engine.generate("Hello world", Path("/tmp/out.wav"))
            self.assertIn("ELEVENLABS_API_KEY", str(ctx.exception))

    def test_openai_missing_key(self):
        with patch.dict(os.environ, {}, clear=True):
            engine = OpenAITTS()
            self.assertFalse(engine.is_available())
            with self.assertRaises(RuntimeError) as ctx:
                engine.generate("Hello world", Path("/tmp/out.wav"))
            self.assertIn("OPENAI_API_KEY", str(ctx.exception))


class TestVoicesCommand(unittest.TestCase):
    """Test scenecraft voices list and preview."""

    def test_run_voices_list(self):
        code = run_voices()
        self.assertEqual(code, 0)

    def test_run_voices_filter_engine(self):
        code = run_voices(engine="kokoro")
        self.assertEqual(code, 0)

    @patch("scenecraft.voices_cmd.get_tts_engine")
    def test_run_voices_preview_success(self, mock_get_engine):
        mock_engine = MagicMock()
        mock_engine.is_available.return_value = True
        mock_engine.generate.side_effect = lambda text, output_path, voice=None, speed=1.0: 2.0
        mock_get_engine.return_value = mock_engine

        with tempfile.TemporaryDirectory() as tmpdir:
            code = run_voices(preview="kokoro", voice="af_heart", out_dir=tmpdir)
            self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
