"""Voice management, engine inspection, and sample synthesis for Scenecraft (`scenecraft voices`)."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import Optional

from scenecraft.config import get_config
from scenecraft.tts import get_tts_engine
from scenecraft.tts.omnivoice import OmniVoiceTTS
from scenecraft.tts.kokoro import KokoroTTS
from scenecraft.tts.edge_tts import EdgeTTS
from scenecraft.tts.piper import PiperTTS
from scenecraft.tts.elevenlabs import ElevenLabsTTS
from scenecraft.tts.openai import OpenAITTS


PREVIEW_SAMPLE_TEXT = "Welcome to Scenecraft video production. This is an automated voice test."


def run_voices(
    engine: Optional[str] = None,
    preview: Optional[str] = None,
    preview_engine: Optional[str] = None,
    voice: Optional[str] = None,
    out_dir: Optional[Path | str] = None,
) -> int:
    """List available TTS engines and voices or generate a spoken preview."""
    cfg = get_config()

    target_preview = preview or preview_engine
    if target_preview:
        return _run_preview(target_preview, voice, out_dir)

    print("=" * 70)
    print("🎙  SCENECRAFT VOICE ENGINES & PROFILES")
    print("=" * 70)
    print(f"Active Config Engine: {cfg.tts_engine.upper()}")
    print("-" * 70)

    target_filter = engine.lower().strip() if engine else None

    # 1. Kokoro
    if not target_filter or target_filter in ("kokoro", "kokoro-onnx"):
        kokoro = KokoroTTS()
        k_avail = kokoro.is_available()
        k_pkg = kokoro.is_package_installed()
        k_model, k_voices = kokoro.get_paths()
        if k_avail:
            k_status = "[✔ READY] (Local ONNX, Apache 2.0 - 100% Offline)"
        elif not k_pkg:
            k_status = "[✘ NOT INSTALLED] Run: pip install \"scenecraft[kokoro]\""
        else:
            k_status = "[⚠ MISSING MODELS] Run: scenecraft setup --tts kokoro"

        print(f"\n1. Kokoro-82M (Local Offline ONNX)")
        print(f"   Status:  {k_status}")
        print(f"   Default: {cfg.kokoro_voice}")
        v_list = kokoro.list_voices()
        v_preview = ", ".join(v_list[:10]) + (f" (+{len(v_list) - 10} more)" if len(v_list) > 10 else "")
        print(f"   Voices:  {v_preview}")

    # 2. Edge-TTS
    if not target_filter or target_filter in ("edge-tts", "edge_tts", "edge"):
        edge = EdgeTTS()
        e_avail = edge.is_available()
        e_status = "[✔ READY] (Zero-setup cloud - Requires Internet)" if e_avail else "[✘ NOT INSTALLED] Run: pip install edge-tts"
        print(f"\n2. Microsoft Edge-TTS (Cloud Neural)")
        print(f"   Status:  {e_status}")
        print(f"   Default: {cfg.edge_voice}")
        print(f"   Voices:  {', '.join(edge.list_voices()[:6])} (+more)")

    # 3. OmniVoice
    if not target_filter or target_filter in ("omnivoice", "voicestudio"):
        omni = OmniVoiceTTS()
        o_avail = omni.is_available()
        o_status = f"[✔ READY] (Active on {omni.base_url})" if o_avail else f"[✘ OFFLINE] (Not responding on {omni.base_url})"
        print(f"\n3. OmniVoice / VoiceStudio (Local Daemon)")
        print(f"   Status:  {o_status}")
        print(f"   Default: {cfg.voice_id}")
        print(f"   Voices:  {', '.join(omni.list_voices())}")

    # 4. Piper
    if not target_filter or target_filter in ("piper",):
        piper = PiperTTS()
        p_avail = piper.is_available()
        p_status = "[✔ READY] (Local Binary)" if p_avail else "[✘ NOT INSTALLED] Download from github.com/rhasspy/piper"
        print(f"\n4. Piper (Local Offline Neural)")
        print(f"   Status:  {p_status}")
        print(f"   Default: {cfg.piper_voice}")
        print(f"   Voices:  {', '.join(piper.list_voices())}")

    # 5. ElevenLabs
    if not target_filter or target_filter in ("elevenlabs", "eleven_labs"):
        eleven = ElevenLabsTTS()
        el_avail = eleven.is_available()
        el_status = "[✔ READY] (API Key detected)" if el_avail else "[⚠ KEY MISSING] Set ELEVENLABS_API_KEY in .env"
        print(f"\n5. ElevenLabs (Paid Cloud API)")
        print(f"   Status:  {el_status}")
        print(f"   Default: {cfg.elevenlabs_voice}")
        print(f"   Voices:  {', '.join(eleven.list_voices()[:4])} (+more)")

    # 6. OpenAI
    if not target_filter or target_filter in ("openai",):
        openai = OpenAITTS()
        oa_avail = openai.is_available()
        oa_status = "[✔ READY] (API Key detected)" if oa_avail else "[⚠ KEY MISSING] Set OPENAI_API_KEY in .env"
        print(f"\n6. OpenAI Speech (Paid Cloud API)")
        print(f"   Status:  {oa_status}")
        print(f"   Default: {cfg.openai_voice}")
        print(f"   Voices:  {', '.join(openai.list_voices())}")

    print("\n" + "=" * 70)
    print("💡 To test a voice, run:")
    print("   scenecraft voices --preview kokoro --voice af_heart")
    print("   scenecraft voices --preview edge-tts --voice en-US-AndrewMultilingualNeural")
    print("=" * 70)
    return 0


def _run_preview(engine_name: str, voice: Optional[str] = None, out_dir: Optional[Path | str] = None) -> int:
    """Generate audio sample for specified engine and voice."""
    target_engine = engine_name.lower().strip()
    engine = get_tts_engine(target_engine)

    target_dir = Path(out_dir) if out_dir else Path.cwd() / "output" / "previews"
    target_dir.mkdir(parents=True, exist_ok=True)

    chosen_voice = voice or "default"
    safe_voice = chosen_voice.replace(":", "_").replace("/", "_")
    out_file = target_dir / f"preview_{target_engine}_{safe_voice}.wav"

    print(f"[*] Generating voice preview for '{target_engine}'...")
    print(f"    Voice:  {chosen_voice}")
    print(f"    Target: {out_file}")

    try:
        dur = engine.generate(
            text=PREVIEW_SAMPLE_TEXT,
            output_path=out_file,
            voice=voice,
            speed=1.0,
        )
        print(f"\n[✔] Voice preview generated successfully ({dur:.2f}s):")
        print(f"    {out_file.resolve()}\n")
        return 0
    except Exception as e:
        print(f"\n[✘] Voice preview failed: {e}\n")
        return 1
