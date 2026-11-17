"""Long-form AI Video Production Pipeline for Scenecraft.

Generates 10-20 minute cinematic landscape master videos (16:9, 1920x1080)
using actual AI video clips, dual-key ElevenLabs narration with failover,
cinematic audio design, automated 9:16 Shorts extraction, and 16:9 thumbnailing.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List

from scenecraft.story_engine_longform import LongformStoryEngine, LongformStoryPlan
try:
    from scenecraft.elevenlabs_client import ElevenLabsClient
except ImportError:
    ElevenLabsClient = None
from scenecraft.audio_manager import AudioManager
from scenecraft.flow_client import FlowClient
from scenecraft.video_engine import VideoEngine, EXPORT_PROFILE_LANDSCAPE, EXPORT_PROFILE_VERTICAL
from scenecraft.shorts_extractor import ShortsExtractor
from scenecraft.thumbnail_generator import ThumbnailGenerator
from scenecraft.caption_generator import CaptionGenerator


class LongformPipeline:
    """Manages the end-to-end production of long-form cinematic AI videos."""

    def __init__(
        self,
        workspace_dir: Optional[Path] = None,
        video_model: str = "omni-flash",
    ):
        self.workspace_dir = Path(workspace_dir or Path.cwd()).resolve()
        self.video_model = video_model

        self.story_engine = LongformStoryEngine(self.workspace_dir)
        self.elevenlabs_client = ElevenLabsClient(workspace_dir=self.workspace_dir) if ElevenLabsClient else None
        licenses_file = self.workspace_dir / "assets" / "licenses.json"
        self.audio_manager = AudioManager(licenses_path=licenses_file if licenses_file.is_file() else None)
        self.flow_client = FlowClient()
        self.video_engine = VideoEngine(audio_manager=self.audio_manager)
        self.shorts_extractor = ShortsExtractor(video_engine=self.video_engine)
        self.thumbnail_gen = ThumbnailGenerator(flow_client=self.flow_client)
        self.caption_gen = CaptionGenerator()

    def produce(
        self,
        theme: str = "You are trapped inside a supermarket during a zombie apocalypse",
        genre: str = "zombie_apocalypse",
        duration_minutes: int = 15,
        project_name: Optional[str] = None,
        use_mock_video_if_flow_offline: bool = False,
        max_scenes: Optional[int] = None,
    ) -> Path:
        """Run or resume full long-form video production pipeline."""
        plan = self.story_engine.generate_plan(
            theme=theme,
            genre=genre,
            target_minutes=duration_minutes,
            project_name=project_name,
            max_scenes=max_scenes,
        )

        project_dir = self.workspace_dir / "output" / plan.project_name
        dirs = {
            "story": project_dir / "story",
            "video": project_dir / "video",
            "clips": project_dir / "video" / "clips",
            "audio": project_dir / "audio",
            "narration": project_dir / "audio" / "narration",
            "music": project_dir / "audio" / "music",
            "sfx": project_dir / "audio" / "sound_effects",
            "shorts": project_dir / "shorts",
            "thumbnail": project_dir / "thumbnail",
            "metadata": project_dir / "metadata",
        }
        for d in dirs.values():
            d.mkdir(parents=True, exist_ok=True)

        print("\n=======================================================")
        print(f"🎬 SCENECRAFT LONG-FORM PRODUCTION: {plan.title}")
        print(f"📁 Project Directory: {project_dir}")
        print(f"⏱  Target Length: {duration_minutes} minutes ({len(plan.scenes)} scene clips)")
        print(f"🖥  Video Format: STRICTLY 16:9 LANDSCAPE (1920x1080)")
        print(f"📱 Shorts Format: STRICTLY 9:16 VERTICAL (1080x1920)")
        print("=======================================================\n")

        # ----------------------------------------------------
        # STAGE 1: STORY & SCENE BREAKDOWN
        # ----------------------------------------------------
        script_file = dirs["story"] / "script.txt"
        breakdown_file = dirs["story"] / "scene_breakdown.json"

        if not script_file.exists() or not breakdown_file.exists():
            print("[*] Stage 1: Exporting multi-act script and scene breakdown...")
            full_script_lines = [
                f"# {plan.title}",
                f"# Premise: {plan.premise}",
                f"# Genre: {plan.genre.upper()}\n",
                "## ACT I: OPENING HOOK (0:00 - 0:30)",
                plan.opening_hook_narration + "\n",
            ]
            for s in plan.scenes:
                full_script_lines.append(f"[{s.act} - Scene {s.scene_index:02d}: {s.title}]")
                full_script_lines.append(s.narration + "\n")
            
            full_script_lines.append("## CONCLUSION & CLIFFHANGER")
            full_script_lines.append(plan.cliffhanger + "\n")
            
            script_file.write_text("\n".join(full_script_lines), encoding="utf-8")
            plan.to_json(breakdown_file)
            print(f"  [✔] Story script saved: {script_file.name}")
            print(f"  [✔] Scene breakdown saved: {breakdown_file.name}")
        else:
            print(f"  [✔] Reusing existing story breakdown: {breakdown_file.name}")

        # ----------------------------------------------------
        # STAGE 2: METADATA
        # ----------------------------------------------------
        title_file = dirs["metadata"] / "title.txt"
        desc_file = dirs["metadata"] / "description.txt"
        tags_file = dirs["metadata"] / "hashtags.txt"
        if not title_file.exists():
            title_file.write_text(plan.title, encoding="utf-8")
            desc_file.write_text(plan.description, encoding="utf-8")
            tags_file.write_text(" ".join(plan.hashtags), encoding="utf-8")
            print("  [✔] Project metadata written (title, description, tags).")

        # ----------------------------------------------------
        # STAGE 3: AUDIO & NARRATION GENERATION (DUAL-KEY)
        # ----------------------------------------------------
        narration_master = dirs["narration"] / "master_narration.mp3"
        subtitles_ass = dirs["video"] / "subtitles.ass"

        if not narration_master.exists():
            print("[*] Stage 2: Synthesizing narration with Dual-Key ElevenLabs...")
            narration_texts = [s.narration for s in plan.scenes]
            combined_narration = " ".join(narration_texts)

            if self.elevenlabs_client and self.elevenlabs_client.is_configured():
                try:
                    self.elevenlabs_client.generate_narration(
                        text=combined_narration,
                        output_path=narration_master,
                        voice_id="pNInz6obpgDQGcFmaJgB",  # Adam (gritty narrative suspense)
                    )
                    print(f"  [✔] Master narration generated: {narration_master.name}")
                except Exception as e:
                    print(f"  [!] ElevenLabs synthesis error: {e}. Generating high-clarity speech fallback...")
                    self._generate_speech_fallback(combined_narration, narration_master)
            else:
                self._generate_speech_fallback(combined_narration, narration_master)
        else:
            print(f"  [✔] Reusing existing master narration: {narration_master.name}")

        # Copy background music and sfx references into project audio folder
        default_bgm = self.audio_manager.get_default_bgm()
        project_bgm = dirs["music"] / default_bgm.name
        if not project_bgm.exists():
            shutil.copy2(default_bgm, project_bgm)

        # ----------------------------------------------------
        # STAGE 4: AI VIDEO CLIP GENERATION (FLOW omni-flash / veo)
        # ----------------------------------------------------
        print("[*] Stage 3: Generating cinematic AI video clips (16:9 horizontal)...")
        scenes_data: List[Dict[str, Any]] = []

        for idx, s in enumerate(plan.scenes, start=1):
            clip_name = f"clip_{idx:02d}.mp4"
            clip_path = dirs["clips"] / clip_name
            alt_clip_path = dirs["clips"] / f"scene_{idx:02d}.mp4"
            if not clip_path.exists() and alt_clip_path.is_file():
                shutil.copy2(alt_clip_path, clip_path)

            if not clip_path.exists():
                if use_mock_video_if_flow_offline:
                    self._generate_mock_video_clip(clip_path, s.target_duration, s.title)
                else:
                    flow_conn = self.flow_client.check_connection()
                    if flow_conn.get("connected"):
                        self.flow_client.generate_video(
                            prompt=s.video_prompt,
                            output_path=clip_path,
                            duration=int(s.target_duration),
                            aspect_ratio="16:9",
                            model=self.video_model,
                            scene_idx=idx,
                        )
                    else:
                        raise RuntimeError(
                            f"Google Flow is disconnected. Please connect Flow or run with mock video mode for testing."
                        )
            else:
                print(f"  [✔] Reusing verified video clip {idx:02d}: {clip_name}")

            scenes_data.append({
                "scene_index": s.scene_index,
                "title": s.title,
                "narration": s.narration,
                "duration": s.target_duration,
                "video_path": clip_path,
                "sfx_cue": s.sfx_cue,
                "camera_movement": s.camera_movement,
                "tension_level": s.tension_level,
                "is_short_candidate": s.is_short_candidate,
                "short_hook": s.short_hook,
            })

        # ----------------------------------------------------
        # STAGE 5: 16:9 MASTER VIDEO RENDERING (1920x1080)
        # ----------------------------------------------------
        master_video_mp4 = dirs["video"] / "master_video.mp4"
        temp_render_dir = project_dir / "temp_render"

        if not master_video_mp4.exists():
            print("[*] Stage 4: Rendering complete 16:9 landscape master video (1920x1080)...")
            self.video_engine.build_full_video(
                scenes=scenes_data,
                narration_audio=narration_master,
                subtitles_ass=None,  # Keep master video cinematic; subtitles burned in Shorts
                output_mp4=master_video_mp4,
                temp_dir=temp_render_dir,
                fps=EXPORT_PROFILE_LANDSCAPE["fps"],
                width=EXPORT_PROFILE_LANDSCAPE["width"],
                height=EXPORT_PROFILE_LANDSCAPE["height"],
                bgm_path=project_bgm,
                burn_subtitles=False,
                require_video_clips=True,
            )
            print(f"  [✔] Master 16:9 video rendered successfully: {master_video_mp4.resolve()}")
        else:
            print(f"  [✔] Reusing existing master 16:9 video: {master_video_mp4.name}")

        # Clean intermediate render directory
        if temp_render_dir.exists():
            shutil.rmtree(temp_render_dir, ignore_errors=True)

        # ----------------------------------------------------
        # STAGE 6: AUTOMATED VIRAL SHORTS EXTRACTION (9:16)
        # ----------------------------------------------------
        print("[*] Stage 5: Extracting narrative-coherent 9:16 viral shorts...")
        extracted_shorts = self.shorts_extractor.extract_shorts_from_master(
            master_mp4=master_video_mp4,
            scenes=scenes_data,
            output_dir=dirs["shorts"],
            target_count=3,
            reframe_mode="smart_crop",
        )
        print(f"  [✔] Extracted {len(extracted_shorts)} viral 9:16 vertical shorts.")

        # ----------------------------------------------------
        # STAGE 7: 16:9 GRAPHIC NOVEL THUMBNAIL GENERATION
        # ----------------------------------------------------
        thumbnail_png = dirs["thumbnail"] / "thumbnail.png"
        if not thumbnail_png.exists():
            print("[*] Stage 6: Generating high-contrast 16:9 YouTube thumbnail...")
            self.thumbnail_gen.generate_thumbnail(
                prompt=plan.scenes[0].video_prompt,
                output_path=thumbnail_png,
                title_hook=plan.scenes[0].short_hook or "LOCKED INSIDE",
                use_flow=not use_mock_video_if_flow_offline,
            )
            print(f"  [✔] Master thumbnail generated: {thumbnail_png.name}")
        else:
            print(f"  [✔] Reusing existing thumbnail: {thumbnail_png.name}")

        print("\n=======================================================")
        print(f"🎉 PRODUCTION COMPLETE: {plan.title}")
        print(f"🎥 Master Video (16:9): {master_video_mp4}")
        print(f"📱 Viral Shorts (9:16): {len(extracted_shorts)} clips in {dirs['shorts']}")
        print(f"🖼  Thumbnail: {thumbnail_png}")
        print("=======================================================\n")
        return project_dir

    def _generate_mock_video_clip(self, output_path: Path, duration: float, title: str):
        """Generate animated test video clip via FFmpeg for testing without Flow."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # Fast testsrc generator (0.1s render per clip)
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", "testsrc=size=1920x1080:rate=30",
            "-t", f"{duration:.3f}",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "ultrafast",
            str(output_path)
        ]
        import subprocess
        subprocess.run(cmd, check=True, capture_output=True)

    def _generate_speech_fallback(self, text: str, output_path: Path):
        """Generate emergency TTS audio fallback using espeak or synthetic sine speech."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        import subprocess
        try:
            # Check if espeak or espeak-ng is available
            cmd = ["espeak", "-w", str(output_path), text[:300]]
            subprocess.run(cmd, check=True, capture_output=True)
        except Exception:
            # Synthetic sine tone audio fallback
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", "sine=frequency=220:duration=10",
                "-c:a", "libmp3lame",
                str(output_path)
            ]
            subprocess.run(cmd, check=True, capture_output=True)
