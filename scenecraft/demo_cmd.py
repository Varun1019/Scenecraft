"""Offline zero-network quickstart video demonstration for Scenecraft (`scenecraft demo`)."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Optional

from scenecraft.audio_manager import AudioManager
from scenecraft.pipeline import verify_video
from scenecraft.tts import get_tts_engine
from scenecraft.video_engine import VideoEngine


def run_demo(
    live_tts: bool = False,
    out_dir: Optional[Path | str] = None,
    quiet: bool = False,
) -> int:
    """Render a 10-second offline demo video using bundled fixtures."""
    assets_dir = Path(__file__).resolve().parent.parent / "assets"
    demo_assets = assets_dir / "demo"

    if not demo_assets.is_dir():
        print("[!] Error: Demo fixtures not found in assets/demo", file=sys.stderr)
        return 1

    project_file = demo_assets / "project.json"
    with open(project_file, "r", encoding="utf-8") as f:
        proj_data = json.load(f)

    target_dir = Path(out_dir).resolve() if out_dir else Path.cwd() / "output" / "demo"
    target_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = target_dir / "temp_render"
    temp_dir.mkdir(parents=True, exist_ok=True)

    if not quiet:
        print("\n" + "=" * 70)
        print("🎬 SCENECRAFT QUICKSTART DEMO (100% Offline)")
        print("=" * 70)
        print(f"Project Title: {proj_data.get('title')}")
        print(f"Format:        9:16 Vertical Short (1080x1920)")
        print(f"Live TTS:      {'Enabled' if live_tts else 'Using bundled audio fixture (zero network)'}")
        print(f"Output Target: {target_dir}")
        print("-" * 70)

    # 1. Narration audio & subtitles
    bundled_audio = demo_assets / "audio" / "narration.wav"
    bundled_subs = demo_assets / "subtitles.ass"

    narration_wav = target_dir / "narration.wav"
    subtitles_ass = target_dir / "subtitles.ass"

    if live_tts:
        if not quiet:
            print("[1/3] Synthesizing live narration via configured TTS engine...")
        engine = get_tts_engine()
        full_text = " ".join(s["narration"] for s in proj_data["scenes"])
        engine.generate(full_text, narration_wav)
        shutil.copy2(bundled_subs, subtitles_ass)
    else:
        if not quiet:
            print("[1/3] Loading bundled narration audio & word-synced subtitles...")
        if bundled_audio.is_file():
            shutil.copy2(bundled_audio, narration_wav)
        else:
            _generate_demo_audio(narration_wav)

        if bundled_subs.is_file():
            shutil.copy2(bundled_subs, subtitles_ass)
        else:
            _generate_demo_subtitles(subtitles_ass)

    # 2. Prepare scene assets
    if not quiet:
        print("[2/3] Linking demo scene illustrations and licensed SFX/BGM...")

    audio_mgr = AudioManager()
    timed_scenes = []
    for sc in proj_data["scenes"]:
        idx = sc["scene_index"]
        img_src = demo_assets / "images" / f"scene_{idx:02d}.jpg"
        img_dest = target_dir / f"scene_{idx:02d}.jpg"
        shutil.copy2(img_src, img_dest)

        sfx_cue = sc.get("sfx_cue")
        timed_scenes.append({
            "scene_index": idx,
            "title": sc.get("title", f"Scene {idx}"),
            "narration": sc.get("narration", ""),
            "duration": float(sc.get("duration", 5.0)),
            "image_path": str(img_dest),
            "camera_movement": sc.get("camera_movement", "zoom_in"),
            "lighting_and_atmosphere": sc.get("lighting_and_atmosphere", ""),
            "transition_out": sc.get("transition_out", "crossfade"),
            "sfx_cue": sfx_cue,
        })

    # 3. Assemble complete video
    if not quiet:
        print("[3/3] Assembling complete MP4 video via FFmpeg (Pan/Zoom + SFX + BGM + Subs)...")

    video_engine = VideoEngine(audio_mgr)
    final_mp4 = target_dir / "demo_video.mp4"

    try:
        video_engine.build_full_video(
            scenes=timed_scenes,
            narration_audio=narration_wav,
            subtitles_ass=subtitles_ass,
            output_mp4=final_mp4,
            temp_dir=temp_dir,
            fps=30,
            width=1080,
            height=1920,
            require_video_clips=False,
        )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    # 4. Verify video stream decodability
    verif = verify_video(final_mp4)

    if not quiet:
        print("\n" + "=" * 70)
        print("🎉 DEMO VIDEO CREATION SUCCESSFUL!")
        print("=" * 70)
        print(f"File Path:   {final_mp4.resolve()}")
        print(f"Duration:    {verif['duration']:.2f}s")
        print(f"Resolution:  {verif['width']}x{verif['height']}")
        print(f"Video Codec: {verif['video_codec']}")
        print(f"Audio Codec: {verif['audio_codec']}")
        print("=" * 70)
        print("💡 Next step: Create your own project with:")
        print("   scenecraft init my_first_story")
        print("   scenecraft make my_first_story/project.json")
        print("=" * 70 + "\n")
    else:
        print(str(final_mp4.resolve()))

    return 0


def _generate_demo_audio(wav_path: Path):
    """Fallback generator for demo narration audio if fixture is missing."""
    import math
    import struct
    import wave
    sample_rate = 16000
    duration = 10.0
    num_samples = int(sample_rate * duration)
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(wav_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        samples = []
        for i in range(num_samples):
            t = i / sample_rate
            if 0.5 <= t <= 4.5:
                env = math.sin((t - 0.5) / 4.0 * math.pi) * 0.7
                f0 = 125.0 + 8.0 * math.sin(2 * math.pi * 1.5 * t)
                val = math.sin(2 * math.pi * f0 * t) + 0.5 * math.sin(2 * math.pi * 2 * f0 * t)
            elif 5.5 <= t <= 9.5:
                env = math.sin((t - 5.5) / 4.0 * math.pi) * 0.7
                f0 = 120.0 + 6.0 * math.sin(2 * math.pi * 1.5 * t)
                val = math.sin(2 * math.pi * f0 * t) + 0.5 * math.sin(2 * math.pi * 2 * f0 * t)
            else:
                env = 0.0
                val = 0.0
            sample = int(env * val * 16000)
            samples.append(struct.pack("<h", max(-32768, min(32767, sample))))
        wf.writeframes(b"".join(samples))


def _generate_demo_subtitles(ass_path: Path):
    """Fallback generator for demo subtitle track if fixture is missing."""
    content = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Noto Sans,64,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,2,2,40,40,240,1
Style: Highlight,Noto Sans,66,&H0000FFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,5,3,2,40,40,240,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.60,0:00:02.40,Default,,0,0,0,,When the siren began...
Dialogue: 0,0:00:02.40,0:00:04.60,Highlight,,0,0,0,,the station went dark.
Dialogue: 0,0:00:05.50,0:00:07.40,Default,,0,0,0,,We locked the blast doors...
Dialogue: 0,0:00:07.40,0:00:09.60,Highlight,,0,0,0,,but we were not alone.
"""
    ass_path.parent.mkdir(parents=True, exist_ok=True)
    ass_path.write_text(content, encoding="utf-8")
