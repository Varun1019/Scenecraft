"""Complete automated end-to-end StoryForge pipeline."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, Optional

from storyforge.audio_manager import AudioManager
from storyforge.flow_client import FlowClient, FlowConnectionError, FlowQuotaExceededError
from storyforge.narration import generate_full_narration
from storyforge.prompt_builder import build_prompts_from_scenes
from storyforge.story_gen import generate_story, generate_auto_story
from storyforge.story_engine import StoryEngine, StoryPlan, SeriesBible
from storyforge.video_engine import VideoEngine
from storyforge.caption_generator import CaptionGenerator, SocialCaption
from storyforge.voice_audition import extract_audition_excerpt, generate_auditions, select_voice_option
from storyforge.script_handoff import load_script, validate_script
from storyforge.scene_director import SceneDirector
from storyforge.thumbnail_generator import ThumbnailGenerator
from storyforge.flow_agent import FlowAgentDirector
from storyforge.settings import is_auto_thumbnail_enabled


def sanitize_filename(name: str) -> str:
    """Sanitize title for safe directory and file names."""
    return re.sub(r"[^\w\-_\. ]", "_", name).strip().replace(" ", "_")


def verify_video(mp4_path: Path) -> Dict[str, Any]:
    """Verify final video with FFprobe to ensure valid streams, duration, and decodability."""
    probe_cmd = [
        "ffprobe", "-v", "error",
        "-show_format", "-show_streams",
        "-print_format", "json",
        str(mp4_path)
    ]
    res = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
    data = json.loads(res.stdout)
    
    # Check for decode errors
    decode_cmd = ["ffmpeg", "-v", "error", "-i", str(mp4_path), "-f", "null", "-"]
    decode_res = subprocess.run(decode_cmd, capture_output=True, text=True)
    if decode_res.returncode != 0 or decode_res.stderr:
        raise RuntimeError(f"FFmpeg decode verification failed:\n{decode_res.stderr}")

    duration = float(data["format"]["duration"])
    vstream = next(s for s in data["streams"] if s["codec_type"] == "video")
    astream = next(s for s in data["streams"] if s["codec_type"] == "audio")
    
    return {
        "duration": duration,
        "width": vstream["width"],
        "height": vstream["height"],
        "fps": vstream.get("r_frame_rate", "30/1"),
        "video_codec": vstream["codec_name"],
        "audio_codec": astream["codec_name"],
    }


class StoryForgePipeline:
    """Automates the complete story-to-finished-MP4 pipeline."""

    def __init__(
        self,
        workspace_dir: Optional[Path] = None,
        voice: str = "default",
        rate: str = "+0%",
        pitch: str = "-2Hz",
        style: str = "dark_cinematic",
        voice_option: Optional[str] = None,
        auto_approve: bool = False,
        story_fallback: str = "local",
        allow_local_on_gemini_fail: bool = False,
        flow_video: bool = False,
        flow_video_model: str = "omni-flash",
        auto_thumbnail: Optional[bool] = None,
        dry_run: bool = False,
    ):
        self.workspace_dir = Path(workspace_dir or Path.cwd()).resolve()
        self.output_dir = self.workspace_dir / "output"
        self.temp_dir = self.workspace_dir / "temp"

        self.audio_manager = AudioManager()
        self.flow_client = FlowClient()
        self.video_engine = VideoEngine(self.audio_manager)
        self.story_engine = StoryEngine(self.workspace_dir)
        self.voice = voice
        self.rate = rate
        self.pitch = pitch
        self.style = style
        self.voice_option = voice_option
        self.auto_approve = auto_approve
        self.story_fallback = story_fallback
        self.allow_local_on_gemini_fail = allow_local_on_gemini_fail
        self.flow_video = flow_video
        self.flow_video_model = flow_video_model
        self.auto_thumbnail = auto_thumbnail if auto_thumbnail is not None else is_auto_thumbnail_enabled(self.workspace_dir)
        self.dry_run = dry_run

    def plan_story(self, concept: Optional[str] = None, genre: Optional[str] = None) -> StoryPlan:
        """Create a standalone retention-focused StoryPlan for user approval."""
        return self.story_engine.plan_standalone_story(concept=concept, genre=genre, fallback_mode=self.story_fallback)

    def adapt_script(
        self,
        script_input: str,
        mode: str = "faithful",
        title: Optional[str] = None,
        genre: Optional[str] = None,
    ) -> StoryPlan:
        """Adapt a script text or file into an approved StoryPlan."""
        return self.story_engine.adapt_script(
            script_input=script_input, mode=mode, title=title, genre=genre, fallback_mode=self.story_fallback
        )

    def run_script(self, script_path: Union[str, Path], aspect_ratio: Optional[str] = None) -> Dict[str, Any]:
        """Produce finished MP4 from a pre-authored script file (JSON or Markdown).
        
        Runs strict pre-flight script validation before any resource consumption.
        Never calls Gemini API (the provided script is the primary source of truth).
        """
        p = Path(script_path).resolve()
        if not p.is_file():
            raise FileNotFoundError(f"Script file not found: {p}")

        print(f"\n==========================================")
        print(f"[*] Validating Story Script: '{p.name}'")
        print(f"==========================================")
        val = validate_script(p)
        print(val.format_report())
        if not val.valid:
            raise ValueError(f"Script validation failed with {len(val.errors)} error(s). Production halted.")

        story_data = load_script(p)
        if aspect_ratio:
            story_data["aspect_ratio"] = aspect_ratio
        if story_data.get("style") and self.style == "dark_cinematic":
            self.style = story_data["style"]

        return self._execute_pipeline(story_data["story_title"], story_data)

    def run_plan(self, plan: StoryPlan | Path | str, aspect_ratio: Optional[str] = None) -> Dict[str, Any]:
        """Produce finished MP4 from an approved StoryPlan."""
        if isinstance(plan, (str, Path)):
            p = Path(plan)
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            plan_obj = StoryPlan.from_dict(data)
            vs = data.get("voice_settings")
            if vs and isinstance(vs, dict):
                if vs.get("voice"):
                    self.voice = vs["voice"]
                if vs.get("rate"):
                    self.rate = vs["rate"]
                if vs.get("pitch"):
                    self.pitch = vs["pitch"]
        else:
            plan_obj = plan

        print(f"\n==========================================")
        print(f"[*] Executing Approved Plan: '{plan_obj.title}'")
        print(f"==========================================")
        story_data = plan_obj.to_storyboard_dict()
        if aspect_ratio:
            story_data["aspect_ratio"] = aspect_ratio
        return self._execute_pipeline(plan_obj.title, story_data)

    def run_auto(self, genre: Optional[str] = None, aspect_ratio: str = "9:16") -> Dict[str, Any]:
        """Auto-Story mode: generates original story and produces finished video."""
        print("\n==========================================")
        print("[*] STORYFORGE AUTO-STORY MODE INITIALIZED")
        print("==========================================")
        story_data = generate_auto_story(
            genre=genre,
            fallback_mode=self.story_fallback,
            allow_local_on_gemini_fail=self.allow_local_on_gemini_fail,
        )
        story_data["aspect_ratio"] = aspect_ratio
        title = story_data.get("story_title", "Midnight Protocol")
        print(f"Generated Story Concept: '{title}'")
        print(f"Genre: {story_data.get('genre', 'Suspense')}")
        print(f"Summary: {story_data.get('summary', '')}")
        return self._execute_pipeline(title, story_data)

    def run(self, story_title: str, aspect_ratio: str = "9:16") -> Dict[str, Any]:
        """Manual run mode: takes explicit story title and produces finished video."""
        print(f"\n==========================================")
        print(f"[*] Starting StoryForge Pipeline: '{story_title}'")
        print(f"==========================================")
        story_data = generate_story(
            story_title,
            fallback_mode=self.story_fallback,
            allow_local_on_gemini_fail=self.allow_local_on_gemini_fail,
        )
        story_data["aspect_ratio"] = aspect_ratio
        return self._execute_pipeline(story_title, story_data)

    def _execute_pipeline(self, story_title: str, story_data: Dict[str, Any], bundle_dir: Optional[Path] = None) -> Dict[str, Any]:
        safe_title = sanitize_filename(story_title)
        timestamp = int(time.time())
        run_name = f"{safe_title}_{timestamp}"
        aspect_ratio = story_data.get("aspect_ratio", "9:16")
        width, height = (1920, 1080) if aspect_ratio == "16:9" else (1080, 1920)

        if bundle_dir:
            bundle_dir = Path(bundle_dir).resolve()
            run_name = bundle_dir.name
            bundle_dir.mkdir(parents=True, exist_ok=True)
            print(f"[*] Executing within bundle directory: {bundle_dir.resolve()}")
        else:
            # Resume from latest matching bundle if it already has generated images
            existing_runs = sorted(self.output_dir.glob(f"{safe_title}_*"), key=lambda p: p.stat().st_mtime, reverse=True)
            if existing_runs and (existing_runs[0] / "images").is_dir() and any((existing_runs[0] / "images").glob("scene_*.jpg")):
                bundle_dir = existing_runs[0]
                run_name = bundle_dir.name
                print(f"[*] Resuming from existing run directory: {run_name}")
            else:
                bundle_dir = self.output_dir / run_name
                bundle_dir.mkdir(parents=True, exist_ok=True)

        images_dir = bundle_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        temp_run_dir = self.temp_dir / run_name
        temp_run_dir.mkdir(parents=True, exist_ok=True)

        # Check for fine-grained Flow Agent storyboard beats
        beats_json = bundle_dir / "storyboard_beats.json"
        if beats_json.is_file() and not story_data.get("override_scenes_with_coarse"):
            try:
                with open(beats_json, "r", encoding="utf-8") as f:
                    b_data = json.load(f)
                    b_list = b_data.get("beats", [])
                    if b_list:
                        story_data["scenes"] = [
                            {
                                "scene_index": b.get("beat_index", i),
                                "title": b.get("title", f"Beat {i}"),
                                "narration": b.get("narration_line") or b.get("narration", ""),
                                "visual_description": b.get("character_action") or b.get("compiled_prompt") or b.get("visual_description", ""),
                                "shot_type": b.get("shot_type"),
                                "camera_movement": b.get("camera_movement", "subtle_drift"),
                                "emotion": b.get("emotional_purpose", "SUSPENSE"),
                                "subject_position": b.get("subject_position", "center_mobile_safe_zone"),
                                "duration": b.get("duration_sec", 3.0),
                            }
                            for i, b in enumerate(b_list, start=1)
                        ]
            except Exception:
                pass

        raw_scenes = story_data.get("scenes", [])
        if not raw_scenes:
            raise ValueError("No scenes found in story data.")

        print(f"  -> Total Scenes / Beats: {len(raw_scenes)} ({aspect_ratio} {width}x{height})")

        # 2.5 PER-VIDEO VOICE AUDITION & SELECTION
        print(f"\n[Step 2.5] Extracting 15-25s script excerpt & checking voice auditions...")
        auditions_dir = bundle_dir / "auditions"
        excerpt = extract_audition_excerpt(raw_scenes)
        auditions_meta = generate_auditions(excerpt, auditions_dir)
        selected_voice = select_voice_option(
            bundle_dir=bundle_dir,
            choice=self.voice_option or (self.voice if self.voice not in ["default", "en-US-AndrewMultilingualNeural"] else None),
            auto_approve=self.auto_approve,
            interactive=not self.auto_approve,
        )
        active_voice = selected_voice["profile_id"]
        active_speed = selected_voice["speed"]
        active_style = selected_voice["style"]

        # 3. VOICE-FIRST TIMING: Synthesize complete narration first to get real audio duration
        print(f"\n[Step 3] VOICE-FIRST TIMING: Synthesizing narration with selected voice ({selected_voice['name']} - {active_voice})...")
        audio_dir = bundle_dir / "audio"
        timed_scenes, narration_audio, subtitles_ass = generate_full_narration(
            scenes=raw_scenes,
            output_dir=audio_dir,
            voice=active_voice,
            rate=self.rate,
            pitch=self.pitch,
            aspect_ratio=aspect_ratio,
            base_speed=active_speed,
            delivery_style=active_style,
        )
        total_audio_duration = sum(s["duration"] for s in timed_scenes)
        print(f"  [✔] Source-of-truth audio generated: {narration_audio.name} ({total_audio_duration:.2f}s across {len(timed_scenes)} scenes)")
        for ts in timed_scenes:
            print(f"      Scene {ts.get('scene_index', '?')}: {ts.get('duration', 0):.2f}s (Audio: {Path(ts.get('audio_path', '')).name})")

        # Copy subtitles directly to bundle root
        bundle_ass = bundle_dir / "subtitles.ass"
        shutil.copy2(subtitles_ass, bundle_ass)

        # 3.5 INTELLIGENT SCENE DIRECTION
        print(f"\n[Step 3.5] Directing cinematic sequence & motion variation...")
        director = SceneDirector(style_preset=self.style)
        beats = director.plan_sequence(timed_scenes, aspect_ratio=aspect_ratio)
        for idx, (ts, beat) in enumerate(zip(timed_scenes, beats)):
            ts["shot_type"] = beat.shot_type
            ts["camera_movement"] = beat.camera_movement
            ts["subject_position"] = beat.subject_position
            ts["background_motion"] = beat.background_motion
            ts["lighting_and_atmosphere"] = beat.lighting_and_atmosphere
            ts["transition_out"] = beat.transition_to_next
            ts["transition_in"] = beats[idx - 1].transition_to_next if idx > 0 else "crossfade"
            ts["emotion"] = beat.emotional_purpose
            if beat.sfx_cue and not ts.get("sfx_cue"):
                ts["sfx_cue"] = beat.sfx_cue

        # 4. Construct cinematic visual prompts with character consistency
        print(f"\n[Step 4] Constructing cinematic visual prompts with character consistency...")
        chars = story_data.get("characters", [])
        char_dict = chars[0] if (chars and isinstance(chars[0], dict)) else None
        scene_prompts = build_prompts_from_scenes(timed_scenes, aspect_ratio=aspect_ratio, character_data=char_dict, style_preset=self.style)
        
        # Save scene prompts to bundle
        prompts_file = bundle_dir / "scene_prompts.txt"
        with open(prompts_file, "w", encoding="utf-8") as f:
            for sp in scene_prompts:
                f.write(f"=== Scene {sp.scene_index}: {sp.title} ===\n")
                f.write(f"Framing: {sp.shot_type} | Camera: {sp.camera_movement} | Emotion: {sp.emotion} | SFX: {sp.sfx_cue}\n")
                f.write(f"Narration: {sp.narration}\n")
                f.write(f"Prompt:\n{sp.full_prompt()}\n\n")

        # 5 & 6. Generate, clean, download, and organize still images from Google Flow
        print(f"\n[Step 5 & 6] Generating consistent cinematic illustrations via Google Flow...")
        scene_images = []
        # Load official brand identity reference image as baseline anchor
        official_ref = Path(__file__).resolve().parent.parent / "references" / "brand_identity" / "ref_character_full_body.jpg"
        reference_char_img = official_ref if official_ref.is_file() else None

        # Check for approved reference character image in output directory
        approved_test_img = self.output_dir / "test_single_shot.jpg"
        if approved_test_img.is_file():
            reference_char_img = approved_test_img
            print(f"[*] Loaded approved character consistency reference: {approved_test_img.name}")

        # Reuse series character anchor from earlier parts if this is an episodic series
        series_info = story_data.get("series_info")
        if not reference_char_img and series_info and series_info.get("series_name"):
            s_slug = sanitize_filename(series_info.get("series_name"))
            prev_runs = sorted(self.output_dir.glob(f"*{s_slug}*"), key=lambda p: p.stat().st_mtime)
            for pr in prev_runs:
                if pr != bundle_dir and (pr / "images" / "scene_01.jpg").is_file():
                    reference_char_img = pr / "images" / "scene_01.jpg"
                    print(f"[*] Reusing series character anchor from {pr.name} ({reference_char_img.name})")
                    break

        flow_clean_bin = shutil.which("flow-auto")

        for sp in scene_prompts:
            raw_img_path = temp_run_dir / f"raw_scene_{sp.scene_index:02d}.jpg"
            clean_img_path = images_dir / f"scene_{sp.scene_index:02d}.jpg"
            full_prompt = sp.full_prompt()

            # Skip generation if already successfully generated and verified
            if clean_img_path.is_file() and self.flow_client.quality_controller.validate_image(clean_img_path, expected_aspect_ratio=aspect_ratio).valid:
                print(f"  [✔] Scene {sp.scene_index} already generated & verified: {clean_img_path.name} (reusing)")
                scene_images.append(clean_img_path)
                if any(k in sp.visual_description.lower() or k in sp.narration.lower() for k in ["wanderer", "stickman", "protagonist", "mechanic", "resident", "operator", "tenant", "he ", "him", "his", "she ", "her", "hands", "figure", "silhouette"]):
                    reference_char_img = clean_img_path
                continue

            # Pass character reference if character appears in the shot to preserve visual consistency
            is_char_scene = any(
                k in sp.visual_description.lower() or k in sp.narration.lower()
                for k in ["wanderer", "stickman", "protagonist", "mechanic", "resident", "operator", "tenant", "he ", "him", "his", "she ", "her", "hands", "figure", "silhouette"]
            )
            ref_to_use = reference_char_img if is_char_scene else None

            # Generate via Google Flow
            self.flow_client.generate_image(
                prompt=full_prompt,
                output_path=raw_img_path,
                scene_idx=sp.scene_index,
                reference_image=ref_to_use,
                folder_name=f"storyforge_{safe_title}",
                aspect_ratio=aspect_ratio,
            )

            # Safely delogo / clean watermark
            if flow_clean_bin:
                try:
                    subprocess.run(
                        ["flow-auto", "clean", str(raw_img_path), "--mark", "flow", "-o", str(clean_img_path)],
                        check=True,
                        capture_output=True
                    )
                except Exception:
                    shutil.copy2(raw_img_path, clean_img_path)
            else:
                shutil.copy2(raw_img_path, clean_img_path)

            scene_images.append(clean_img_path)
            # Chain the latest verified character shot as reference for visual continuity
            if is_char_scene and clean_img_path.is_file():
                reference_char_img = clean_img_path

        # Attach verified images to timed scenes and run Vision QC inspection
        flagged_qc_reports = []
        for ts, img_path, sp in zip(timed_scenes, scene_images, scene_prompts):
            ts["image_path"] = str(img_path)
            is_char = getattr(sp, "reference_angle_path", None) is not None
            qc = self.flow_client.quality_controller.inspect_vision_quality(
                image_path=img_path,
                scene_idx=ts.get("scene_index", 1),
                narration=ts.get("narration", ""),
                prompt=sp.full_prompt(),
                expected_aspect_ratio=aspect_ratio,
                is_character_scene=is_char,
            )
            if qc.needs_manual_review:
                flagged_qc_reports.append(qc)

        # Gate 2: Production Preview
        print("\n" + "=" * 60)
        print("GATE 2 — PRODUCTION PREVIEW")
        print("=" * 60)
        print(f"Total Narration: {total_audio_duration:.2f}s (Real Voice-First Duration)")
        print(f"Generated Images: {len(scene_images)} verified scene illustrations")
        if flagged_qc_reports:
            print("\nVision Quality Flags for Review (Hold for user decision — no blind auto-regeneration):")
            for rep in flagged_qc_reports:
                print(f"  [!] {rep.summary_line()}")
        else:
            print("Vision QC Status: All scenes passed Wanderer identity, anatomy, and framing checks.")
        print("=" * 60 + "\n")

        # Optional Flow Agent Video Generation (Full scene clips)
        if self.flow_video:
            print("\n" + "=" * 60)
            print("[Step 6.5] GOOGLE FLOW AGENT VIDEO GENERATION ACTIVATED")
            print("=" * 60)
            agent_director = FlowAgentDirector(self.workspace_dir, self.flow_client)
            char_name = char_dict.get("name", "The Wanderer") if char_dict else "The Wanderer"
            timed_scenes = agent_director.generate_scenes(
                scenes=timed_scenes,
                output_dir=bundle_dir,
                story_title=story_title,
                character_name=char_name,
                reference_image=reference_char_img,
                aspect_ratio=aspect_ratio,
                model=self.flow_video_model,
                auto_approve=self.auto_approve,
                dry_run=self.dry_run,
            )

        # 8. Select and verify audio assets
        print(f"\n[Step 8] Verifying licenses for sound effects and background music...")
        bgm_path = self.audio_manager.get_default_bgm()
        print(f"  -> BGM Verified: {bgm_path.name}")
        for s in timed_scenes:
            if s.get("sfx_cue"):
                try:
                    sfx_path = self.audio_manager.get_sfx(s["sfx_cue"])
                    print(f"  -> SFX Verified: {sfx_path.name} for Scene {s['scene_index']}")
                except Exception as e:
                    print(f"  [!] SFX '{s['sfx_cue']}' in Scene {s['scene_index']} not verified, skipping cue: {e}")
                    s["sfx_cue"] = None

        # 9 & 10. FFmpeg composition and export
        final_mp4 = bundle_dir / f"{safe_title}.mp4"
        print(f"\n[Step 9 & 10] Rendering cinematic {aspect_ratio} ({width}x{height}) video via FFmpeg...")
        self.video_engine.build_full_video(
            scenes=timed_scenes,
            narration_audio=narration_audio,
            subtitles_ass=bundle_ass,
            output_mp4=final_mp4,
            temp_dir=temp_run_dir / "render",
            fps=30,
            width=width,
            height=height,
            require_video_clips=self.flow_video,
        )

        # Verify final MP4
        print("[*] Verifying output file integrity with FFprobe...")
        verif = verify_video(final_mp4)

        # Dedicated Google Flow AI Thumbnail Generator (independent Flow image generation, never frame extraction)
        thumb_gen = ThumbnailGenerator(self.flow_client, self.workspace_dir)
        thumb_res = None
        should_gen_thumb = self.auto_thumbnail if self.auto_thumbnail is not None else thumb_gen.is_auto_enabled()
        if should_gen_thumb:
            try:
                thumb_res = thumb_gen.generate_flow_ai_thumbnail(
                    story_data=story_data,
                    output_dir=bundle_dir,
                    aspect_ratio=aspect_ratio,
                    style_preset=self.style,
                    character_ref=reference_char_img,
                    auto_approve=self.auto_approve,
                    dry_run=self.dry_run,
                )
            except Exception as e:
                print(f"[!] Flow AI Thumbnail generation note: {e}")

        # Save metadata and script
        summary_file = bundle_dir / "story_summary.txt"
        summary_content = (
            f"Title: {story_title}\n"
            f"Genre: {story_data.get('genre', 'Suspense')}\n"
            f"Summary: {story_data.get('summary', '')}\n"
            f"Duration: {verif['duration']:.2f}s\n"
            f"Resolution: {verif['width']}x{verif['height']} ({aspect_ratio})\n"
            f"Voice: {self.voice}\n"
            f"Video Path: {final_mp4.resolve()}\n"
        )
        summary_file.write_text(summary_content, encoding="utf-8")

        script_file = bundle_dir / "story_script.json"
        with open(script_file, "w", encoding="utf-8") as f:
            json.dump({
                "title": story_title,
                "genre": story_data.get("genre", "Suspense"),
                "summary": story_data.get("summary", ""),
                "scenes": timed_scenes,
                "verification": verif,
            }, f, indent=2, default=str)

        # Automatic Social Media Video Caption Generator & Publishing Metadata
        from storyforge.metadata_generator import MetadataGenerator
        meta_gen = MetadataGenerator()
        ai_thumb_path = thumb_res.get("jpg") if (thumb_res and isinstance(thumb_res, dict)) else None
        pub_meta = meta_gen.generate_metadata(
            story_title=story_title,
            story_summary=story_data.get("summary", ""),
            scenes=timed_scenes,
            hook_text=story_data.get("on_screen_hook_text") or (timed_scenes[0].get("narration", "") if timed_scenes else ""),
            video_path=final_mp4,
            output_dir=bundle_dir,
            thumbnail_path=ai_thumb_path,
            extract_frame=False,  # Strictly NEVER extract frame from video
        )
        pub_file = bundle_dir / "publishing_metadata.txt"
        pub_file.write_text(pub_meta.format_summary(), encoding="utf-8")

        caption_gen = CaptionGenerator(self.workspace_dir)
        caption = caption_gen.generate_caption(story_data)
        saved_captions = caption_gen.save_caption_bundle(caption, bundle_dir)

        # Convenient root copy for numbered series if configured
        part_num = (series_info.get("part_num") or series_info.get("episode_num")) if series_info else None
        if part_num:
            numbered_copy = self.output_dir / f"FINAL_STORY_{part_num:03d}.mp4"
            if not numbered_copy.exists():
                shutil.copy2(final_mp4, numbered_copy)
                print(f"[✔] Saved easy-to-find series copy: {numbered_copy.name}")

        print("\n" + "=" * 60)
        print("GATE 3 — FINAL APPROVAL & PUBLISHING METADATA")
        print("=" * 60)
        print(pub_meta.format_summary())
        print("=" * 60 + "\n")

        print(f"==========================================")
        print(f"[✔] StoryForge Complete!")
        print(f"Finished MP4: {final_mp4.resolve()}")
        print(f"Bundle Folder: {bundle_dir.resolve()}")
        print(f"Duration: {verif['duration']:.2f}s ({verif['width']}x{verif['height']})")
        print(f"==========================================\n")

        return {
            "title": story_title,
            "genre": story_data.get("genre", "Suspense"),
            "summary": story_data.get("summary", ""),
            "mp4_path": final_mp4,
            "bundle_dir": bundle_dir,
            "verification": verif,
            "caption": caption.to_dict(),
            "caption_files": saved_captions,
        }
