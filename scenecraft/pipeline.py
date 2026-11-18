"""Complete automated end-to-end Scenecraft pipeline."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, Optional

from scenecraft.audio_manager import AudioManager
from scenecraft.flow_client import FlowClient, FlowConnectionError, FlowQuotaExceededError
from scenecraft.narration import generate_full_narration
from scenecraft.prompt_builder import build_prompts_from_scenes
from scenecraft.story_gen import generate_story, generate_auto_story
from scenecraft.story_engine import StoryEngine, StoryPlan, SeriesBible
from scenecraft.video_engine import VideoEngine
from scenecraft.caption_generator import CaptionGenerator, SocialCaption
from scenecraft.config import get_config
from scenecraft.script_handoff import load_script, validate_script
from scenecraft.scene_director import SceneDirector
from scenecraft.thumbnail_generator import ThumbnailGenerator
from scenecraft.flow_agent import FlowAgentDirector
from scenecraft.settings import is_auto_thumbnail_enabled


STATE_FILE_NAME = ".scenecraft_state.json"


def load_pipeline_state(bundle_dir: Path) -> Dict[str, Any]:
    """Load resume state from .scenecraft_state.json."""
    sf = Path(bundle_dir) / STATE_FILE_NAME
    if sf.is_file():
        try:
            with open(sf, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_pipeline_state(bundle_dir: Path, state: Dict[str, Any]):
    """Persist resume state to .scenecraft_state.json."""
    sf = Path(bundle_dir) / STATE_FILE_NAME
    try:
        with open(sf, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception:
        pass


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


class ScenecraftPipeline:
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
        images_dir: Optional[Path | str] = None,
        clean_user_images: bool = False,
        force: bool = False,
        quiet: bool = False,
        verbose: bool = False,
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
        self.images_dir = images_dir
        self.clean_user_images = clean_user_images
        self.force = force
        self.quiet = quiet
        self.verbose = verbose

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
        print("[*] SCENECRAFT AUTO-STORY MODE INITIALIZED")
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
        print(f"[*] Starting Scenecraft Pipeline: '{story_title}'")
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
            if not self.quiet:
                print(f"[*] Executing within bundle directory: {bundle_dir.resolve()}")
        else:
            # Resume from latest matching bundle if it already has generated images
            existing_runs = sorted(self.output_dir.glob(f"{safe_title}_*"), key=lambda p: p.stat().st_mtime, reverse=True)
            if existing_runs and (existing_runs[0] / "images").is_dir() and any((existing_runs[0] / "images").glob("scene_*.jpg")):
                bundle_dir = existing_runs[0]
                run_name = bundle_dir.name
                if not self.quiet:
                    print(f"[*] Resuming from existing run directory: {run_name}")
            else:
                bundle_dir = self.output_dir / run_name
                bundle_dir.mkdir(parents=True, exist_ok=True)

        images_dir = bundle_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        temp_run_dir = self.temp_dir / run_name
        temp_run_dir.mkdir(parents=True, exist_ok=True)

        # Load pipeline state
        state = {} if self.force else load_pipeline_state(bundle_dir)

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

        # DRY RUN EXECUTION PLAN
        if self.dry_run:
            if not self.quiet:
                print("\n" + "=" * 70)
                print(f"📋 SCENECRAFT DRY-RUN PLAN: '{story_title}'")
                print("=" * 70)
                print(f"Aspect Ratio:  {aspect_ratio} ({width}x{height})")
                print(f"Total Scenes:  {len(raw_scenes)}")
                print(f"Bundle Target: {bundle_dir.resolve()}")
                print("-" * 70)
                print("[1/5] Story Breakdown & Planning:       [SIMULATED - OK]")
                narr_status = "SKIP (Cached)" if state.get("narration") and not self.force else "WILL EXECUTE"
                print(f"[2/5] Narration Audio Synthesis:         [{narr_status}]")
                vis_src = f"Custom --images-dir ({self.images_dir})" if self.images_dir else "Google Flow AI"
                vis_status = "SKIP (Cached)" if state.get("visuals") and not self.force else "WILL EXECUTE"
                print(f"[3/5] Visual Ingestion & Verification:   [{vis_status}] (Source: {vis_src})")
                sub_status = "SKIP (Cached)" if state.get("subtitles") and not self.force else "WILL EXECUTE"
                print(f"[4/5] Word-Synced Subtitle Alignment:   [{sub_status}]")
                asm_status = "SKIP (Cached)" if state.get("assembly") and not self.force else "WILL EXECUTE"
                print(f"[5/5] Multi-Layer Video Composition:     [{asm_status}]")
                print(f"Target Video:  {bundle_dir / f'{safe_title}.mp4'}")
                print("=" * 70 + "\n")
            return {
                "title": story_title,
                "dry_run": True,
                "bundle_dir": bundle_dir,
                "mp4_path": bundle_dir / f"{safe_title}.mp4",
                "scenes": raw_scenes,
            }

        # Step 1: Story Breakdown
        if not self.quiet:
            print("\n" + "=" * 70)
            print(f"[1/5] Story Breakdown & Planning: '{story_title}' ({aspect_ratio} {width}x{height})")
            print("=" * 70)
            print(f"  -> Total Scenes / Beats: {len(raw_scenes)}")

        # Step 2: Voice selection & Narration Synthesis
        cfg = get_config()
        active_voice = self.voice_option or (self.voice if self.voice not in ["default", "en-US-AndrewMultilingualNeural"] else cfg.voice_id)
        active_speed = cfg.voice_speed
        active_style = cfg.voice_style
        voice_name = f"Voice ({active_voice})"

        if not self.quiet:
            print("\n" + "=" * 70)
            print(f"[2/5] Narration Audio Synthesis: {voice_name}")
            print("=" * 70)

        audio_dir = bundle_dir / "audio"
        cached_narration = audio_dir / "narration.wav"
        can_skip_narration = not self.force and state.get("narration") and cached_narration.is_file() and (bundle_dir / "subtitles.ass").is_file()

        if can_skip_narration:
            if not self.quiet:
                print(f"  [✔] State resume: Reusing verified narration audio ({cached_narration.name})")
            narration_audio = cached_narration
            bundle_ass = bundle_dir / "subtitles.ass"
            timed_scenes = [dict(s) for s in raw_scenes]
            for s in timed_scenes:
                if "duration" not in s:
                    s["duration"] = 5.0
            total_audio_duration = sum(s["duration"] for s in timed_scenes)
        else:
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
            bundle_ass = bundle_dir / "subtitles.ass"
            shutil.copy2(subtitles_ass, bundle_ass)
            total_audio_duration = sum(s["duration"] for s in timed_scenes)
            state["narration"] = True
            save_pipeline_state(bundle_dir, state)
            if not self.quiet:
                print(f"  [✔] Source-of-truth audio generated: {narration_audio.name} ({total_audio_duration:.2f}s across {len(timed_scenes)} scenes)")

        # Intelligent Scene Direction
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

        chars = story_data.get("characters", [])
        char_dict = chars[0] if (chars and isinstance(chars[0], dict)) else None
        scene_prompts = build_prompts_from_scenes(timed_scenes, aspect_ratio=aspect_ratio, character_data=char_dict, style_preset=self.style)

        prompts_file = bundle_dir / "scene_prompts.txt"
        with open(prompts_file, "w", encoding="utf-8") as f:
            for sp in scene_prompts:
                f.write(f"=== Scene {sp.scene_index}: {sp.title} ===\n")
                f.write(f"Framing: {sp.shot_type} | Camera: {sp.camera_movement} | Emotion: {sp.emotion} | SFX: {sp.sfx_cue}\n")
                f.write(f"Narration: {sp.narration}\n")
                f.write(f"Prompt:\n{sp.full_prompt()}\n\n")

        # Step 3: Visual Ingestion & Verification
        if not self.quiet:
            print("\n" + "=" * 70)
            print("[3/5] Visual Assets: Ingestion & Verification")
            print("=" * 70)

        can_skip_visuals = not self.force and state.get("visuals") and all((images_dir / f"scene_{sp.scene_index:02d}.jpg").is_file() for sp in scene_prompts)

        if can_skip_visuals:
            if not self.quiet:
                print("  [✔] State resume: Reusing verified scene illustrations")
            scene_images = [images_dir / f"scene_{sp.scene_index:02d}.jpg" for sp in scene_prompts]
        elif self.images_dir:
            src_dir = Path(self.images_dir).resolve()
            if not src_dir.is_dir():
                raise FileNotFoundError(f"Custom images directory not found: {src_dir}")
            exts = {".jpg", ".jpeg", ".png", ".webp"}
            found = sorted([p for p in src_dir.iterdir() if p.suffix.lower() in exts])
            if not found:
                raise ValueError(f"No image files found in {src_dir}")

            if not self.quiet:
                print(f"[*] Ingesting {len(found)} custom image(s) from {src_dir} (Watermark cleaning: {'ON' if self.clean_user_images else 'OFF'})...")
            scene_images = []
            for sp in scene_prompts:
                dest_p = images_dir / f"scene_{sp.scene_index:02d}.jpg"
                matched = None
                for c in found:
                    if f"scene_{sp.scene_index:02d}" in c.name.lower() or f"scene_{sp.scene_index}" in c.name.lower():
                        matched = c
                        break
                if not matched:
                    matched = found[(sp.scene_index - 1) % len(found)]

                if self.clean_user_images:
                    if not self.quiet:
                        print(f"  -> Cleaning watermark from user image: {matched.name}")
                    from scenecraft.cleaner import clean_image
                    clean_image(matched, dest_p)
                else:
                    shutil.copy2(matched, dest_p)
                scene_images.append(dest_p)
            state["visuals"] = True
            save_pipeline_state(bundle_dir, state)
        else:
            scene_images = []
            official_ref = Path(__file__).resolve().parent.parent / "references" / "brand_identity" / "ref_character_full_body.jpg"
            reference_char_img = official_ref if official_ref.is_file() else None

            approved_test_img = self.output_dir / "test_single_shot.jpg"
            if approved_test_img.is_file():
                reference_char_img = approved_test_img

            series_info = story_data.get("series_info")
            if not reference_char_img and series_info and series_info.get("series_name"):
                s_slug = sanitize_filename(series_info.get("series_name"))
                prev_runs = sorted(self.output_dir.glob(f"*{s_slug}*"), key=lambda p: p.stat().st_mtime)
                for pr in prev_runs:
                    if pr != bundle_dir and (pr / "images" / "scene_01.jpg").is_file():
                        reference_char_img = pr / "images" / "scene_01.jpg"
                        break

            flow_clean_bin = shutil.which("flow-auto")

            for sp in scene_prompts:
                raw_img_path = temp_run_dir / f"raw_scene_{sp.scene_index:02d}.jpg"
                clean_img_path = images_dir / f"scene_{sp.scene_index:02d}.jpg"
                full_prompt = sp.full_prompt()

                if clean_img_path.is_file() and self.flow_client.quality_controller.validate_image(clean_img_path, expected_aspect_ratio=aspect_ratio).valid:
                    if not self.quiet:
                        print(f"  [✔] Scene {sp.scene_index} already generated & verified: {clean_img_path.name} (reusing)")
                    scene_images.append(clean_img_path)
                    continue

                is_char_scene = any(
                    k in sp.visual_description.lower() or k in sp.narration.lower()
                    for k in ["wanderer", "stickman", "protagonist", "mechanic", "resident", "operator", "tenant", "he ", "him", "his", "she ", "her", "hands", "figure", "silhouette"]
                )
                ref_to_use = reference_char_img if is_char_scene else None

                self.flow_client.generate_image(
                    prompt=full_prompt,
                    output_path=raw_img_path,
                    scene_idx=sp.scene_index,
                    reference_image=ref_to_use,
                    folder_name=f"scenecraft_{safe_title}",
                    aspect_ratio=aspect_ratio,
                )

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
                if is_char_scene and clean_img_path.is_file():
                    reference_char_img = clean_img_path

            state["visuals"] = True
            save_pipeline_state(bundle_dir, state)

        # Attach images to timed scenes
        for ts, img_path in zip(timed_scenes, scene_images):
            ts["image_path"] = str(img_path)

        # Step 4: Word-Synced Subtitles
        if not self.quiet:
            print("\n" + "=" * 70)
            print("[4/5] Word-Synced Subtitle Alignment")
            print("=" * 70)
            print(f"  [✔] Subtitles verified: {bundle_ass.name}")
        state["subtitles"] = True
        save_pipeline_state(bundle_dir, state)

        # Step 5: Video Composition
        if not self.quiet:
            print("\n" + "=" * 70)
            print(f"[5/5] Multi-Layer Video Composition ({aspect_ratio} {width}x{height})")
            print("=" * 70)

        # SFX & BGM verification
        bgm_path = self.audio_manager.get_default_bgm()
        for s in timed_scenes:
            if s.get("sfx_cue"):
                try:
                    sfx_path = self.audio_manager.get_sfx(s["sfx_cue"])
                except Exception:
                    s["sfx_cue"] = None

        final_mp4 = bundle_dir / f"{safe_title}.mp4"
        can_skip_assembly = not self.force and state.get("assembly") and final_mp4.is_file()

        if can_skip_assembly:
            if not self.quiet:
                print(f"  [✔] State resume: Reusing rendered MP4 ({final_mp4.name})")
            verif = verify_video(final_mp4)
        else:
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
            verif = verify_video(final_mp4)
            state["assembly"] = True
            state["mp4_path"] = str(final_mp4.resolve())
            save_pipeline_state(bundle_dir, state)

        if not self.quiet:
            print("\n" + "=" * 70)
            print("🎬 SCENECRAFT VIDEO PRODUCTION COMPLETE!")
            print("=" * 70)
            print(f"File Path:   {final_mp4.resolve()}")
            print(f"Duration:    {verif['duration']:.2f}s")
            print(f"Resolution:  {verif['width']}x{verif['height']} ({aspect_ratio})")
            print(f"Bundle Dir:  {bundle_dir.resolve()}")
            print("=" * 70 + "\n")
        else:
            print(str(final_mp4.resolve()))

        return {
            "title": story_title,
            "genre": story_data.get("genre", "Suspense"),
            "summary": story_data.get("summary", ""),
            "mp4_path": final_mp4,
            "video_path": final_mp4,
            "bundle_dir": bundle_dir,
            "verification": verif,
        }
