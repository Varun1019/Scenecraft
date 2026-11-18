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
        # Use bundled subtitles template for timing
        shutil.copy2(bundled_subs, subtitles_ass)
    else:
        if not quiet:
            print("[1/3] Loading bundled narration audio & word-synced subtitles...")
        shutil.copy2(bundled_audio, narration_wav)
        shutil.copy2(bundled_subs, subtitles_ass)

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
        # Clean up intermediate render directory
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
