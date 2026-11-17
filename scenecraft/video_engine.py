"""FFmpeg video composition engine for Scenecraft."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional

from scenecraft.audio_manager import AudioManager

EXPORT_PROFILE_LANDSCAPE = {
    "name": "16:9 Landscape Master",
    "width": 1920,
    "height": 1080,
    "aspect_ratio": "16:9",
    "fps": 30,
    "vcodec": "libx264",
    "pix_fmt": "yuv420p",
}

EXPORT_PROFILE_VERTICAL = {
    "name": "9:16 Vertical Short/Reel",
    "width": 1080,
    "height": 1920,
    "aspect_ratio": "9:16",
    "fps": 30,
    "vcodec": "libx264",
    "pix_fmt": "yuv420p",
}



def escape_ffmpeg_filter_path(path: Path | str) -> str:
    """Escape a path for FFmpeg filtergraph strings (e.g. ass=filename='...':fontsdir='...').

    Normalizes backslashes to forward slashes, escapes colons (for Windows drive letters
    and FFmpeg option separators), and escapes single quotes.
    Does NOT backslash-escape spaces because paths in FFmpeg filter parameters are single-quoted.
    """
    path_str = str(path)
    normalized = path_str.replace("\\", "/")
    escaped = normalized.replace(":", "\\:").replace("'", "\\'")
    return escaped


def get_bundled_fonts_dir() -> Optional[Path]:
    """Return path to bundled fonts directory if present."""
    base = Path(__file__).resolve().parent.parent / "assets" / "fonts"
    if base.is_dir():
        return base
    return None


class VideoEngine:
    """Composes scenes, Ken Burns camera movements, audio tracks, and subtitles into MP4."""

    def __init__(self, audio_manager: Optional[AudioManager] = None):
        self.audio_manager = audio_manager or AudioManager()
        self.nvenc_available = self._detect_nvenc()

    def _detect_nvenc(self) -> bool:
        """Detect whether FFmpeg can actually encode using h264_nvenc via a real test encode."""
        test_cmd = [
            "ffmpeg", "-y", "-v", "error",
            "-f", "lavfi", "-i", "nullsrc=s=64x64:d=0.1",
            "-c:v", "h264_nvenc",
            "-f", "null", "-"
        ]
        try:
            res = subprocess.run(test_cmd, capture_output=True, timeout=3)
            return res.returncode == 0
        except Exception:
            return False

    def reframe_to_vertical(
        self,
        input_video: Path,
        output_video: Path,
        mode: str = "smart_crop",
        start_time: Optional[float] = None,
        duration: Optional[float] = None,
        fps: int = 30,
    ) -> Path:
        """Reframe landscape 16:9 video into vertical 9:16 (1080x1920) without stretching."""
        output_video.parent.mkdir(parents=True, exist_ok=True)
        time_args = []
        if start_time is not None:
            time_args.extend(["-ss", f"{start_time:.3f}"])
        if duration is not None:
            time_args.extend(["-t", f"{duration:.3f}"])

        if mode == "blur_backdrop":
            # Ambient blurred background + centered crisp 16:9 foreground
            filter_complex = (
                "[0:v]split=2[bg_src][fg_src];"
                "[bg_src]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=luma_radius=25:luma_power=2[bg];"
                "[fg_src]scale=1080:-1[fg];"
                "[bg][fg]overlay=(W-w)/2:(H-h)/2[outv]"
            )
            cmd = [
                "ffmpeg", "-y",
                *time_args,
                "-i", str(input_video),
                "-filter_complex", filter_complex,
                "-map", "[outv]",
                "-map", "0:a?",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-preset", "fast",
                "-c:a", "aac",
                "-b:a", "192k",
                "-r", str(fps),
                str(output_video)
            ]
        else:
            # Default "smart_crop": Scale height to 1920 and center crop 1080 width (safe-area centered)
            vf = "scale=-1:1920:force_original_aspect_ratio=increase,crop=1080:1920:(in_w-1080)/2:0,fps=" + str(fps)
            cmd = [
                "ffmpeg", "-y",
                *time_args,
                "-i", str(input_video),
                "-vf", vf,
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-preset", "fast",
                "-c:a", "aac",
                "-b:a", "192k",
                str(output_video)
            ]

        subprocess.run(cmd, check=True, capture_output=True)
        return output_video

    def render_scene_clip(
        self,
        image_path: Path,
        duration: float,
        out_clip: Path,
        movement: str = "zoom_in",
        fps: int = 30,
        width: int = 1920,
        height: int = 1080,
        emotion: Optional[str] = None,
        shot_type: Optional[str] = None,
        subject_position: Optional[str] = None,
        transition_in: Optional[str] = None,
        transition_out: Optional[str] = None,
        apply_effects: bool = True,
        use_nvenc: bool = False,
    ) -> Path:
        """Render a single still image or video clip into a standardized video clip with jitter-free pre-upscaling."""
        out_clip.parent.mkdir(parents=True, exist_ok=True)
        total_frames = max(1, int(round(duration * fps)))

        # If image_path is already a video clip (e.g. from Flow video generation), format/loop it
        if image_path.suffix.lower() in [".mp4", ".mov", ".webm", ".mkv"]:
            filter_chain = (
                f"scale={width}:{height}:force_original_aspect_ratio=increase,"
                f"crop={width}:{height},"
                f"fps={fps}"
            )
            cmd = [
                "ffmpeg", "-y",
                "-stream_loop", "-1",
                "-i", str(image_path),
                "-t", f"{duration:.3f}",
                "-vf", filter_chain,
                "-an",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-preset", "fast",
                "-r", str(fps),
                str(out_clip)
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            return out_clip

        # Directorial focus-aware coordinate anchoring
        pos = (subject_position or "").lower()
        if "left" in pos:
            cx = 0.35
        elif "right" in pos:
            cx = 0.65
        else:
            cx = 0.50

        st = (shot_type or "").upper()
        if "background_isolated" in pos or st == "LOW_ANGLE_HEROIC":
            cy = 0.65
        elif st == "HIGH_ANGLE_VULNERABLE":
            cy = 0.35
        else:
            cy = 0.50

        # Emotion & directorial movement selection
        emo = (emotion or "").upper()
        mov = movement.lower().strip()

        if mov == "fast_push_in" or emo in ["PANIC", "ACTION", "CHASE"]:
            zoom_expr = "min(zoom+0.0022, 1.25)"
            x_expr = f"{cx:.2f}*(iw-iw/zoom)"
            y_expr = f"{cy:.2f}*(ih-ih/zoom)"
        elif mov in ["pull_back", "zoom_out"] or st == "HIGH_ANGLE_VULNERABLE":
            zoom_expr = "if(lte(zoom,1.02),1.18,max(1.02,zoom-0.0014))"
            x_expr = f"{cx:.2f}*(iw-iw/zoom)"
            y_expr = f"{cy:.2f}*(ih-ih/zoom)"
        elif mov == "pan_left":
            zoom_expr = "1.12"
            x_expr = f"(1-on/{total_frames})*(iw-iw/zoom)"
            y_expr = f"{cy:.2f}*(ih-ih/zoom)"
        elif mov == "pan_right" or (emo in ["DISCOVERY", "EXPLORATION"] and mov == "zoom_in"):
            zoom_expr = "1.12"
            x_expr = f"(on/{total_frames})*(iw-iw/zoom)"
            y_expr = f"{cy:.2f}*(ih-ih/zoom)"
        elif mov == "pan_up":
            zoom_expr = "1.12"
            x_expr = f"{cx:.2f}*(iw-iw/zoom)"
            y_expr = f"(1-on/{total_frames})*(ih-ih/zoom)"
        elif mov == "pan_down":
            zoom_expr = "1.12"
            x_expr = f"{cx:.2f}*(iw-iw/zoom)"
            y_expr = f"(on/{total_frames})*(ih-ih/zoom)"
        elif mov == "subtle_drift":
            zoom_expr = "min(zoom+0.0004, 1.08)"
            x_expr = f"(0.30+0.40*(on/{total_frames}))*(iw-iw/zoom)"
            y_expr = f"(0.30+0.40*(on/{total_frames}))*(ih-ih/zoom)"
        elif mov in ["static", "static_hold"] or st in ["CLOSE_UP_INTENSE", "OVER_THE_SHOULDER"]:
            zoom_expr = "1.04"
            x_expr = f"{cx:.2f}*(iw-iw/zoom)"
            y_expr = f"{cy:.2f}*(ih-ih/zoom)"
        else:
            # Default slow push-in for cinematic tension
            zoom_expr = "min(zoom+0.0008, 1.15)"
            x_expr = f"{cx:.2f}*(iw-iw/zoom)"
            y_expr = f"{cy:.2f}*(ih-ih/zoom)"

        # Pre-upscale 2x before zoompan to eliminate subpixel truncation jitter
        pre_w = width * 2
        pre_h = height * 2

        filter_steps = [
            f"scale={pre_w}:{pre_h}:force_original_aspect_ratio=increase",
            f"crop={pre_w}:{pre_h}",
            f"zoompan=z='{zoom_expr}':x='{x_expr}':y='{y_expr}':d={total_frames}:s={pre_w}x{pre_h}:fps={fps}",
            f"scale={width}:{height}",
        ]

        # Subtle cinematic effects: delicate vignette and fine organic grain
        if apply_effects:
            if emo in ["DREAD", "SUSPENSE", "SHOCK"]:
                filter_steps.append("vignette=PI/5")
            filter_steps.append("noise=c1s=5:c0f=u")

        # Head / tail transition fades
        fade_d = min(0.35, max(0.1, duration / 4))
        if transition_in in ["dip_to_black", "crossfade"]:
            filter_steps.append(f"fade=t=in:st=0:d={fade_d:.2f}")
        if transition_out in ["dip_to_black", "crossfade"]:
            start_fade = max(0.0, duration - fade_d)
            filter_steps.append(f"fade=t=out:st={start_fade:.2f}:d={fade_d:.2f}")

        filter_chain = ",".join(filter_steps)

        v_codec_args = ["-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p"]
        if use_nvenc and self.nvenc_available:
            v_codec_args = ["-c:v", "h264_nvenc", "-preset", "p4", "-cq", "20", "-pix_fmt", "yuv420p"]

        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", str(image_path),
            "-t", f"{duration:.3f}",
            "-vf", filter_chain,
            *v_codec_args,
            "-r", str(fps),
            str(out_clip)
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except subprocess.CalledProcessError:
            # Graceful CPU fallback if NVENC fails
            if use_nvenc and self.nvenc_available:
                cmd_cpu = [
                    "ffmpeg", "-y",
                    "-loop", "1",
                    "-i", str(image_path),
                    "-t", f"{duration:.3f}",
                    "-vf", filter_chain,
                    "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
                    "-r", str(fps),
                    str(out_clip)
                ]
                subprocess.run(cmd_cpu, check=True, capture_output=True)
            else:
                raise
        return out_clip

    def render_scene_video_clip(
        self,
        video_path: Path,
        duration: float,
        out_clip: Path,
        fps: int = 30,
        width: int = 1920,
        height: int = 1080,
    ) -> Path:
        """Scale, pad, and time-stretch/loop video clip to match exact scene duration."""
        # Scale to fit vertical or horizontal without distortion, pad to target resolution, loop/trim to duration
        vf = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},fps={fps}"
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "-1",
            "-i", str(video_path),
            "-t", f"{duration:.3f}",
            "-vf", vf,
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "fast",
            "-an",
            str(out_clip)
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return out_clip

    def build_full_video(
        self,
        scenes: List[Dict[str, Any]],
        narration_audio: Path,
        subtitles_ass: Optional[Path],
        output_mp4: Path,
        temp_dir: Path,
        fps: int = 30,
        width: int = 1920,
        height: int = 1080,
        bgm_path: Optional[Path] = None,
        burn_subtitles: bool = True,
        require_video_clips: bool = False,
        use_nvenc: bool = False,
        quality_preset: str = "master",
    ) -> Path:
        """Combine all rendered scene clips, sound effects, BGM, and subtitles into final MP4."""
        temp_dir.mkdir(parents=True, exist_ok=True)
        output_mp4.parent.mkdir(parents=True, exist_ok=True)

        # 1. Render all scene visual clips
        clip_paths = []
        for idx, scene in enumerate(scenes, start=1):
            clip_path = temp_dir / f"clip_{idx:02d}.mp4"
            duration = scene["duration"]
            is_valid = False
            if clip_path.is_file() and clip_path.stat().st_size > 1000:
                try:
                    res = subprocess.run(
                        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(clip_path)],
                        capture_output=True,
                        check=True
                    )
                    if float(res.stdout.decode().strip()) > 0:
                        is_valid = True
                except Exception:
                    is_valid = False

            if is_valid:
                clip_paths.append(clip_path)
                continue
            if scene.get("video_path") and Path(scene["video_path"]).is_file():
                self.render_scene_video_clip(Path(scene["video_path"]), duration, clip_path, fps=fps, width=width, height=height)
            elif require_video_clips:
                raise ValueError(
                    f"Scene {idx} missing required AI video clip: '{scene.get('video_path')}'. "
                    "Per production requirements, long-form videos must use actual video clips."
                )
            else:
                image_path = Path(scene["image_path"])
                movement = scene.get("camera_movement", "zoom_in")
                emotion = scene.get("emotion")
                shot_type = scene.get("shot_type")
                subject_pos = scene.get("subject_position")
                trans_in = scene.get("transition_in")
                trans_out = scene.get("transition_out")
                self.render_scene_clip(
                    image_path,
                    duration,
                    clip_path,
                    movement=movement,
                    fps=fps,
                    width=width,
                    height=height,
                    emotion=emotion,
                    shot_type=shot_type,
                    subject_position=subject_pos,
                    transition_in=trans_in,
                    transition_out=trans_out,
                    use_nvenc=use_nvenc,
                )
            clip_paths.append(clip_path)

        # 2. Concat video clips
        concat_list = temp_dir / "concat_list.txt"
        with open(concat_list, "w", encoding="utf-8") as f:
            for cp in clip_paths:
                f.write(f"file '{cp.resolve()}'\n")

        raw_video = temp_dir / "concatenated_visual.mp4"
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_list),
            "-c", "copy",
            str(raw_video)
        ], check=True, capture_output=True)

        total_duration = sum(s["duration"] for s in scenes)
        current_time = 0.0
        for scene in scenes:
            scene["start_time"] = current_time
            current_time += scene["duration"]

        # 3. Audio assembly: BGM + Narration + SFX
        resolved_bgm = Path(bgm_path) if bgm_path and Path(bgm_path).is_file() else self.audio_manager.get_default_bgm()
        
        # Build complex audio filter:
        # Stream 0: raw_video (visuals only, no audio)
        # Stream 1: narration_audio
        # Stream 2: bgm_audio
        # Stream 3+: sound effects
        audio_inputs = ["-i", str(narration_audio), "-i", str(resolved_bgm)]
        sfx_nodes = []
        sfx_idx = 3

        # Improved SFX gain table: audible but not overwhelming (-22 dB to -16 dB relative to narration)
        SFX_GAIN_TABLE = {
            "sfx_whoosh_cinematic": 0.10,
            "sfx_whoosh_fast": 0.09,
            "sfx_swoosh": 0.09,
            "sfx_sub_rumble": 0.12,
            "sfx_emergency_alert": 0.15,
            "sfx_alarm": 0.14,
            "sfx_door_lock": 0.13,
            "sfx_water_faucet": 0.11,
            "sfx_water": 0.11,
            "sfx_knock_door": 0.16,
            "sfx_knock_heavy": 0.16,
            "sfx_knock": 0.14,
            "sfx_door_slam": 0.16,
            "sfx_door_creak": 0.12,
            "sfx_footsteps_creepy": 0.11,
            "sfx_tension_riser": 0.12,
            "sfx_phone_vibrate": 0.12,
            "sfx_phone_ring": 0.14,
            "sfx_clock_tick": 0.09,
        }

        for scene in scenes:
            scene_sfx_list = []
            if scene.get("sfx_cue"):
                scene_sfx_list.append((scene["sfx_cue"], 0.0))
            if scene.get("sfx_cues"):
                scene_sfx_list.extend(scene["sfx_cues"])

            for sfx_name, rel_offset in scene_sfx_list:
                try:
                    sfx_file = self.audio_manager.get_sfx(sfx_name)
                    audio_inputs.extend(["-i", str(sfx_file)])
                    delay_ms = int((scene["start_time"] + rel_offset) * 1000)
                    gain = SFX_GAIN_TABLE.get(sfx_name.replace(".wav", ""), 0.08)
                    sfx_nodes.append((sfx_idx, delay_ms, gain))
                    sfx_idx += 1
                except Exception as e:
                    print(f"Skipping sfx cue {sfx_name}: {e}")

        filter_parts = [
            # Stream 1: Broadcast Narration Chain (EQ + De-ess + Light Compression + Peak Limiting)
            "[1:a]highpass=f=85,equalizer=f=400:t=q:w=1.5:g=-2.5,equalizer=f=3400:t=q:w=1.2:g=2.2,equalizer=f=6500:t=q:w=2.0:g=-2.8,acompressor=threshold=0.18:ratio=3:attack=15:release=120,asplit=2[vox_mix][vox_sc]",
            # Stream 2: BGM with sidechain ducking (~10dB duck under words, smooth recovery)
            f"[2:a]aloop=loop=-1:size=2e+09,atrim=0:{total_duration:.2f},highpass=f=45,volume=0.30,afade=t=out:st={max(0, total_duration - 1.5):.2f}:d=1.5[raw_bgm]",
            "[raw_bgm][vox_sc]sidechaincompress=threshold=0.12:ratio=3.5:attack=50:release=350[ducked_bgm]",
        ]

        mix_inputs = ["[vox_mix]", "[ducked_bgm]"]
        for node_idx, delay, gain in sfx_nodes:
            filter_parts.append(f"[{node_idx}:a]adelay={delay}|{delay},volume={gain:.2f}[sfx{node_idx}]")
            mix_inputs.append(f"[sfx{node_idx}]")

        filter_parts.append(
            f"{''.join(mix_inputs)}amix=inputs={len(mix_inputs)}:duration=first:dropout_transition=0,"
            f"alimiter=limit=0.98,"
            f"loudnorm=I=-14:TP=-1.5:LRA=9[out_audio]"
        )
        audio_filter_str = ";".join(filter_parts)

        # 4. Final render: merge video + mixed audio + optional ASS subtitles
        should_burn = burn_subtitles and subtitles_ass and Path(subtitles_ass).is_file()
        if should_burn:
            sub_escaped = escape_ffmpeg_filter_path(subtitles_ass)
            fonts_dir = get_bundled_fonts_dir()
            if fonts_dir and fonts_dir.is_dir():
                fonts_escaped = escape_ffmpeg_filter_path(fonts_dir)
                video_filter_str = f";[0:v]ass=filename='{sub_escaped}':fontsdir='{fonts_escaped}'[out_video]"
            else:
                video_filter_str = f";[0:v]ass=filename='{sub_escaped}'[out_video]"
            video_map = "[out_video]"
        else:
            video_filter_str = ""
            video_map = "0:v"

        # Determine encoding profile
        if use_nvenc and self.nvenc_available:
            v_codec_args = ["-c:v", "h264_nvenc", "-preset", "p4", "-rc", "vbr", "-cq", "22", "-b:v", "12M"]
            a_bitrate = "192k"
        elif quality_preset == "master":
            # Broadcast master: CRF 17 slow preset for maximum visual fidelity without artifacting
            v_codec_args = ["-c:v", "libx264", "-preset", "slow", "-crf", "17", "-tune", "animation"]
            a_bitrate = "256k"
        else:
            v_codec_args = ["-c:v", "libx264", "-preset", "fast", "-crf", "22"]
            a_bitrate = "192k"

        final_cmd = [
            "ffmpeg", "-y",
            "-i", str(raw_video),
            *audio_inputs,
            "-filter_complex", f"{audio_filter_str}{video_filter_str}",
            "-map", video_map,
            "-map", "[out_audio]",
            *v_codec_args,
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", a_bitrate,
            "-shortest",
            str(output_mp4)
        ]

        try:
            subprocess.run(final_cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as err:
            if use_nvenc and self.nvenc_available:
                v_codec_args = ["-c:v", "libx264", "-preset", "fast", "-crf", "22"]
                fallback_cmd = [
                    "ffmpeg", "-y",
                    "-i", str(raw_video),
                    *audio_inputs,
                    "-filter_complex", f"{audio_filter_str}{video_filter_str}",
                    "-map", video_map,
                    "-map", "[out_audio]",
                    *v_codec_args,
                    "-pix_fmt", "yuv420p",
                    "-c:a", "aac",
                    "-b:a", a_bitrate,
                    "-shortest",
                    str(output_mp4)
                ]
                subprocess.run(fallback_cmd, check=True, capture_output=True, text=True)
            else:
                print("FFmpeg STDERR:\n", err.stderr)
                raise
        return output_mp4
