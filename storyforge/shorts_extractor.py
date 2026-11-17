"""Automated Viral Shorts & Reels Extractor for StoryForge.

Extracts 2-4 coherent narrative vertical clips (9:16, 1080x1920) from
the 16:9 master video or scene sequence. Each Short features its own
opening hook, rising tension, standalone narrative integrity,
dynamic subtitles, and a suspenseful cliffhanger.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Any, Optional

from storyforge.video_engine import VideoEngine, EXPORT_PROFILE_VERTICAL
from storyforge.caption_generator import CaptionGenerator


@dataclass
class ViralShortMetadata:
    short_index: int
    title: str
    opening_hook: str
    cliffhanger: str
    duration_seconds: float
    output_mp4: str
    subtitles_srt: str
    hashtags: List[str]


class ShortsExtractor:
    """Extracts narrative-coherent 9:16 viral vertical shorts from long-form production."""

    def __init__(self, video_engine: Optional[VideoEngine] = None):
        self.video_engine = video_engine or VideoEngine()
        self.caption_gen = CaptionGenerator()

    def select_short_candidates(
        self,
        scenes: List[Dict[str, Any]],
        target_count: int = 3,
        min_duration: float = 30.0,
        max_duration: float = 60.0,
    ) -> List[Dict[str, Any]]:
        """Identify coherent narrative scene clusters suitable for standalone Shorts."""
        candidates = []
        n = len(scenes)

        # Look for scenes marked as short_candidate or peak tension points
        anchor_indices = [
            i for i, s in enumerate(scenes)
            if s.get("is_short_candidate") or s.get("tension_level", 0) >= 8
        ]

        if not anchor_indices:
            # Fallback evenly spaced anchor points
            anchor_indices = [0, n // 3, (2 * n) // 3]

        used_scenes = set()

        for anchor in anchor_indices:
            if len(candidates) >= target_count:
                break
            if anchor in used_scenes:
                continue

            # Expand scene window around anchor to reach ~35-50s
            cluster = [scenes[anchor]]
            dur = scenes[anchor].get("duration", 6.0)
            fwd = anchor + 1
            bwd = anchor - 1

            while dur < min_duration and (fwd < n or bwd >= 0):
                if fwd < n:
                    if fwd not in used_scenes:
                        cluster.append(scenes[fwd])
                        dur += scenes[fwd].get("duration", 6.0)
                    fwd += 1
                if dur >= min_duration:
                    break
                if bwd >= 0:
                    if bwd not in used_scenes:
                        cluster.insert(0, scenes[bwd])
                        dur += scenes[bwd].get("duration", 6.0)
                    bwd -= 1

            if min_duration <= dur <= max_duration + 10:
                for sc in cluster:
                    used_scenes.add(sc.get("scene_index", 0))

                hook_text = (
                    cluster[0].get("short_hook")
                    or f"Wait until you see what happens in scene {cluster[0].get('scene_index', 1)}..."
                )
                cliffhanger_text = (
                    cluster[-1].get("narration", "")[-80:]
                    or "What would you do in this situation?"
                )

                candidates.append({
                    "cluster_scenes": cluster,
                    "start_time": cluster[0].get("start_time", 0.0),
                    "duration": dur,
                    "hook": hook_text,
                    "cliffhanger": cliffhanger_text,
                    "title": f"Viral Short #{len(candidates)+1}: {cluster[0].get('title', 'Survivor Moment')}",
                })

        if not candidates and scenes:
            # Fallback: bundle all available scenes into 1 short
            dur = sum(s.get("duration", 6.0) for s in scenes)
            hook_text = scenes[0].get("short_hook") or "You won't believe what happens next..."
            cliffhanger_text = scenes[-1].get("narration", "")[-80:] or "To be continued..."
            candidates.append({
                "cluster_scenes": scenes,
                "start_time": 0.0,
                "duration": dur,
                "hook": hook_text,
                "cliffhanger": cliffhanger_text,
                "title": f"Viral Short #1: {scenes[0].get('title', 'Survivor Moment')}",
            })

        return candidates[:target_count]

    def extract_shorts_from_master(
        self,
        master_mp4: Path,
        scenes: List[Dict[str, Any]],
        output_dir: Path,
        target_count: int = 3,
        reframe_mode: str = "smart_crop",
    ) -> List[ViralShortMetadata]:
        """Produce vertical 9:16 Shorts from the master 16:9 video file."""
        output_dir = Path(output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        candidates = self.select_short_candidates(scenes, target_count=target_count)
        extracted: List[ViralShortMetadata] = []

        for idx, cand in enumerate(candidates, start=1):
            short_name = f"short_{idx:02d}"
            out_mp4 = output_dir / f"{short_name}.mp4"
            out_srt = output_dir / f"{short_name}.srt"
            meta_json = output_dir / f"{short_name}_metadata.json"

            # Check cache: reuse existing valid short
            if out_mp4.is_file() and out_mp4.stat().st_size > 100 * 1024:
                print(f"  [✔] Reusing existing vertical Short #{idx}: {out_mp4.name}")
            else:
                print(f"[*] Reframing and rendering Vertical Short #{idx} ({cand['duration']:.1f}s)...")
                self.video_engine.reframe_to_vertical(
                    input_video=master_mp4,
                    output_video=out_mp4,
                    mode=reframe_mode,
                    start_time=cand["start_time"],
                    duration=cand["duration"],
                    fps=EXPORT_PROFILE_VERTICAL["fps"],
                )

            # Generate standalone SRT captions for the short
            full_script = " ".join(s.get("narration", "") for s in cand["cluster_scenes"])
            self.generate_standalone_srt(cand["cluster_scenes"], out_srt)

            meta = ViralShortMetadata(
                short_index=idx,
                title=cand["title"],
                opening_hook=cand["hook"],
                cliffhanger=cand["cliffhanger"],
                duration_seconds=cand["duration"],
                output_mp4=str(out_mp4),
                subtitles_srt=str(out_srt),
                hashtags=["#Shorts", "#ZombieApocalypse", "#SurvivalHorror", "#ViralVideo", "#StoryForge"],
            )

            with open(meta_json, "w", encoding="utf-8") as f:
                json.dump(asdict(meta), f, indent=2)

            extracted.append(meta)

        return extracted

    def generate_standalone_srt(self, cluster_scenes: List[Dict[str, Any]], out_srt: Path):
        """Generate time-aligned SRT subtitles relative to the start of the Short."""
        lines = []
        current_time = 0.0

        for idx, scene in enumerate(cluster_scenes, start=1):
            dur = scene.get("duration", 6.0)
            text = scene.get("narration", "").strip()
            
            # Format times for SRT (HH:MM:SS,mmm)
            start_str = self._format_srt_timestamp(current_time)
            end_str = self._format_srt_timestamp(current_time + dur)

            lines.append(f"{idx}\n{start_str} --> {end_str}\n{text}\n")
            current_time += dur

        out_srt.write_text("\n".join(lines), encoding="utf-8")

    @staticmethod
    def _format_srt_timestamp(seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int(round((seconds - int(seconds)) * 1000))
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
