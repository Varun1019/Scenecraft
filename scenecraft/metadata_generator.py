"""Publishing & Metadata Engine for Scenecraft.

Generates YouTube-ready viral title, high-CTR description, targeted hashtags,
short social caption, and extracts optimal high-contrast thumbnail frames.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Optional


@dataclass
class PublishingMetadata:
    youtube_title: str
    description: str
    hashtags: List[str]
    social_caption: str
    recommended_thumbnail_path: Optional[Path] = None
    character_focus: str = "The Wanderer"

    def format_summary(self) -> str:
        tag_str = " ".join(self.hashtags)
        lines = [
            "=== YOUTUBE / SOCIAL PUBLISHING METADATA ===",
            f"Title: {self.youtube_title}",
            "",
            "Description:",
            self.description,
            "",
            f"Hashtags: {tag_str}",
            "",
            f"Social Caption: {self.social_caption}",
        ]
        if self.recommended_thumbnail_path:
            lines.append(f"Recommended Thumbnail Frame: {self.recommended_thumbnail_path.name}")
        return "\n".join(lines)


class MetadataGenerator:
    """Produces optimized YouTube Shorts & TikTok metadata and extracts thumbnail frames."""

    def generate_metadata(
        self,
        story_title: str,
        story_summary: str,
        scenes: List[Dict[str, Any]],
        hook_text: str = "",
        video_path: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        thumbnail_path: Optional[Path] = None,
        extract_frame: bool = False,
    ) -> PublishingMetadata:
        # 1. Clean Title: High intrigue, under 60 chars for mobile shorts
        clean_title = story_title.strip()
        if not clean_title.endswith("?"):
            yt_title = f"{clean_title} | Psychological Thriller"
        else:
            yt_title = clean_title

        # 2. Description: 2-line hook + story premise + credit + channel tags
        desc_lines = [
            f"'{hook_text or scenes[0].get('narration', '')}'",
            "",
            f"{story_summary}",
            "",
            "Starring The Wanderer.",
            "Created with Scenecraft — dark comic animated suspense.",
            "",
            "#Shorts #Suspense #Mystery #Horror #AnimatedShorts #TheWanderer #Scenecraft",
        ]
        description = "\n".join(desc_lines)

        # 3. Targeted Hashtags
        hashtags = [
            "#Shorts",
            "#Suspense",
            "#Mystery",
            "#Thriller",
            "#HorrorShorts",
            "#AnimatedShorts",
            "#TheWanderer",
            "#CreepyStories",
        ]

        # 4. Social Caption (Punchy 1-liner for TikTok / IG Reels)
        social_caption = f"Whatever you do, do NOT look behind you. ⚠️ {clean_title} #shorts #mystery #suspense"

        # 5. Dedicated AI Thumbnail resolution
        # Preference: Explicit thumbnail_path > Existing Flow AI thumbnail in output_dir > extract_frame (if allowed)
        thumb_path = None
        if thumbnail_path and Path(thumbnail_path).is_file():
            thumb_path = Path(thumbnail_path)
        elif output_dir:
            existing_ai_thumb = Path(output_dir) / "thumbnail.png"
            existing_ai_jpg = Path(output_dir) / "thumbnail_recommended.jpg"
            if existing_ai_thumb.is_file():
                thumb_path = existing_ai_thumb
            elif existing_ai_jpg.is_file():
                thumb_path = existing_ai_jpg

        # Fallback to frame extraction ONLY if explicitly requested and no AI thumbnail exists
        if thumb_path is None and extract_frame and video_path and Path(video_path).is_file() and output_dir:
            thumb_path = self.extract_best_thumbnail_frame(Path(video_path), Path(output_dir))

        return PublishingMetadata(
            youtube_title=yt_title[:100],
            description=description,
            hashtags=hashtags,
            social_caption=social_caption,
            recommended_thumbnail_path=thumb_path,
        )

    def extract_best_thumbnail_frame(self, video_path: Path, output_dir: Path) -> Optional[Path]:
        """Extract optimal high-contrast representative frame using FFmpeg thumbnail filter."""
        output_dir.mkdir(parents=True, exist_ok=True)
        thumb_out = output_dir / "thumbnail_recommended.jpg"

        # Use FFmpeg thumbnail filter to select the most visually representative frame
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-vf", "thumbnail=30",
            "-frames:v", "1",
            str(thumb_out)
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if res.returncode == 0 and thumb_out.is_file() and thumb_out.stat().st_size > 10000:
                return thumb_out
        except Exception:
            pass

        # Fallback: grab frame at 2.0s mark
        fallback_cmd = [
            "ffmpeg", "-y",
            "-ss", "00:00:02.000",
            "-i", str(video_path),
            "-vframes", "1",
            "-q:v", "2",
            str(thumb_out)
        ]
        try:
            res = subprocess.run(fallback_cmd, capture_output=True, text=True, timeout=10)
            if res.returncode == 0 and thumb_out.is_file():
                return thumb_out
        except Exception:
            pass

        return None
