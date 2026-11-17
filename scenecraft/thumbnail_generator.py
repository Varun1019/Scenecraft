"""Dedicated Google Flow AI Thumbnail Generator for Scenecraft.

Analyzes story drama, character identity, and climatic moments to generate
an entirely NEW, independent image via Google Flow Nano Banana image generation.
Never extracts frames or screenshots from rendered video files.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List

from scenecraft.flow_client import FlowClient, FlowQuotaExceededError
from scenecraft.settings import is_auto_thumbnail_enabled, get_setting


class ThumbnailGenerator:
    """Generates dedicated high-impact AI thumbnails independently generated through Google Flow."""

    def __init__(self, flow_client: Optional[FlowClient] = None, workspace_dir: Optional[Path] = None):
        self.flow_client = flow_client or FlowClient()
        self.workspace_dir = Path(workspace_dir or Path.cwd()).resolve()

    def is_auto_enabled(self) -> bool:
        """Check if automatic thumbnail generation is enabled in Scenecraft settings."""
        return is_auto_thumbnail_enabled(self.workspace_dir)

    def analyze_story_for_thumbnail(self, story_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze story structure, title, character identity, and identify the strongest visual hook."""
        title = story_data.get("story_title") or story_data.get("title", "Survival Story")
        genre = story_data.get("genre", "Suspense Thriller")
        summary = story_data.get("summary") or story_data.get("story_summary", "")
        scenes = story_data.get("scenes", [])
        beats = story_data.get("beats", [])

        # Check visual beats if available, else scenes
        candidate_items = beats if beats else scenes

        # 1. Resolve character identity
        chars = story_data.get("characters", [])
        primary_char = chars[0] if chars and isinstance(chars[0], dict) else {}
        char_name = primary_char.get("name") or "The Wanderer"
        char_desc = primary_char.get("visual_description") or primary_char.get("description")

        if not char_desc:
            if "wanderer" in char_name.lower():
                char_desc = (
                    "The Wanderer, stylized stickman survivor with smooth warm ivory head, "
                    "two vertical black pill eyes, brick-red ribbed knit beanie, and striped mustard-gold and rust-maroon scarf"
                )
            elif "ethan" in char_name.lower():
                char_desc = (
                    "Ethan, young adult male stickman with round white head, simple black facial features, "
                    "matte black hoodie, dark trousers, white sneakers"
                )
            else:
                char_desc = f"{char_name}, stylized character with clean bold ink outlines and consistent clothing"

        # 2. Identify strongest visual hook and peak dramatic tension moment
        peak_item = None
        max_tension = -1.0

        for item in candidate_items:
            t_val = 0.0
            raw_t = item.get("tension_level", 0.0)
            try:
                t_val = float(raw_t)
            except (ValueError, TypeError):
                if str(raw_t).upper() in ["HIGH", "MAX", "EXTREME", "CLIMAX"]:
                    t_val = 9.0
                elif str(raw_t).upper() == "MEDIUM":
                    t_val = 5.0

            # Boost if contains dramatic visual hook indicators
            vis_lower = (item.get("visual_description") or item.get("character_action") or item.get("video_prompt") or "").lower()
            act_lower = (item.get("act") or item.get("emotional_purpose") or "").lower()
            if any(k in vis_lower or k in act_lower for k in ["climax", "confrontation", "revelation", "countdown", "discovery", "shock", "horror"]):
                t_val += 3.0

            if t_val > max_tension:
                max_tension = t_val
                peak_item = item

        if not peak_item and candidate_items:
            climax_idx = max(0, int(len(candidate_items) * 0.75) - 1)
            peak_item = candidate_items[climax_idx]

        focal_event = ""
        if peak_item:
            focal_event = (
                peak_item.get("visual_description")
                or peak_item.get("character_action")
                or peak_item.get("video_prompt")
                or peak_item.get("narration_line")
                or peak_item.get("narration", "")
            )

        return {
            "title": title,
            "genre": genre,
            "summary": summary,
            "character_name": char_name,
            "character_description": char_desc,
            "peak_moment": focal_event[:250],
            "peak_scene_index": peak_item.get("scene_index", 1) if peak_item else 1,
            "visual_hook": focal_event[:180] or f"Critical survival confrontation in {title}",
        }

    def build_thumbnail_prompt(
        self,
        analysis: Dict[str, Any],
        aspect_ratio: str = "16:9",
        style_preset: str = "earthy_explainer",
        custom_prompt: Optional[str] = None,
    ) -> str:
        """Create a dedicated, clutter-free AI thumbnail prompt based strictly on story reality."""
        if custom_prompt and custom_prompt.strip():
            clean_user = custom_prompt.strip()
            return (
                f"{clean_user}. "
                f"Art style: clean bold 2D graphic illustration, high-contrast atmospheric lighting, "
                f"cinematic masterwork. No text, no letters, no logos, no borders, no margins."
            )

        char_desc = analysis["character_description"]
        peak = analysis["peak_moment"]
        title = analysis["title"]

        if style_preset in ["earthy_explainer", "earthy"]:
            style_cue = (
                "Cinematic 2D hand-drawn graphic novel illustration, clean bold black outlines, "
                "muted earthy palette with dramatic golden and amber highlights, cel-shaded volumetric depth"
            )
        else:
            style_cue = (
                "Dark cinematic 2D graphic novel illustration, stark rim lighting, deep charcoal shadows, "
                "gritty suspense thriller aesthetic, sharp graphic outlines"
            )

        if aspect_ratio == "16:9":
            # 16:9 Landscape YouTube Master Thumbnail: Rule-of-thirds composition
            prompt = (
                f"16:9 cinematic YouTube master thumbnail for suspense mystery '{title}'. {style_cue}. "
                f"{char_desc} on the right third of the frame, turning with intense shock and urgency, "
                f"looking toward the mystery unfolding on the left. "
                f"Core story dramatic moment: {peak}. "
                f"Extreme atmospheric depth, strong negative space, cinematic rim light, professional composition. "
                f"Pure visual storytelling. No text, no captions, no logos, no margins, no white borders."
            )
        else:
            # 9:16 Vertical Shorts / Reels Cover Thumbnail: Centered focal power
            prompt = (
                f"Vertical 9:16 YouTube Shorts cover thumbnail for '{title}'. {style_cue}. "
                f"{char_desc} centered in the middle safe area (between 30% and 70% frame height). "
                f"Dramatic peak moment: {peak}. "
                f"Strong vertical leading lines, bold high-contrast silhouette against deep background, "
                f"intense directional lighting, extreme visual intrigue. "
                f"No text, no captions, no logos, no margins, no white borders."
            )

        return prompt

    def resolve_character_reference(self, character_name: str = "The Wanderer") -> Optional[Path]:
        """Find the approved visual consistency anchor image for character generation."""
        if "wanderer" in character_name.lower():
            official_ref = self.workspace_dir / "references" / "brand_identity" / "ref_character_full_body.jpg"
            if official_ref.is_file():
                return official_ref.resolve()

        test_shot = self.workspace_dir / "output" / "test_single_shot.jpg"
        if test_shot.is_file():
            return test_shot.resolve()

        return None

    def generate_flow_ai_thumbnail(
        self,
        story_data: Dict[str, Any],
        output_dir: Path,
        aspect_ratio: str = "16:9",
        style_preset: str = "earthy_explainer",
        character_ref: Optional[Path] = None,
        custom_prompt: Optional[str] = None,
        auto_approve: bool = False,
        dry_run: bool = False,
    ) -> Dict[str, Path]:
        """Generate an entirely NEW AI thumbnail via Google Flow image generation.
        
        Strictly satisfies requirements:
        - NEVER extracts a frame from the finished video.
        - NEVER takes a screenshot.
        - Uses native 16:9 for longform or 9:16 for Shorts/Reels covers.
        - Preserves character visual identity via Flow Connector image-to-image.
        - Respects Flow credits and account restrictions.
        """
        output_dir = Path(output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        thumb_png = output_dir / "thumbnail.png"
        thumb_jpg = output_dir / "thumbnail_recommended.jpg"
        prompt_txt = output_dir / "thumbnail_prompt.txt"

        # 1. Analyze story and build dedicated thumbnail prompt
        analysis = self.analyze_story_for_thumbnail(story_data)
        full_prompt = self.build_thumbnail_prompt(
            analysis=analysis,
            aspect_ratio=aspect_ratio,
            style_preset=style_preset,
            custom_prompt=custom_prompt,
        )

        # 2. Resolve character reference
        resolved_ref = character_ref or self.resolve_character_reference(analysis["character_name"])
        if resolved_ref and resolved_ref.is_file():
            print(f"[*] Thumbnail character continuity reference: {resolved_ref.name}")

        # Record prompt to output directory
        prompt_txt.write_text(
            f"=== SCENECRAFT FLOW AI THUMBNAIL PROMPT ===\n"
            f"Story Title:     {analysis['title']}\n"
            f"Visual Hook:     {analysis['visual_hook']}\n"
            f"Aspect Ratio:    {aspect_ratio}\n"
            f"Character:       {analysis['character_name']}\n"
            f"Reference Image: {resolved_ref.name if resolved_ref else 'None'}\n"
            f"Prompt:\n{full_prompt}\n",
            encoding="utf-8"
        )

        print(f"\n[*] Generating dedicated {aspect_ratio} AI Thumbnail via Google Flow...")
        print(f"    Target File: {thumb_png.name}")
        print(f"    Visual Hook: {analysis['visual_hook'][:100]}...")
        print(f"    Prompt:      {full_prompt[:140]}...")

        # 3. Credit Guard & Dry Run Check
        if dry_run:
            print("  [DRY-RUN] Simulating Flow AI thumbnail generation without credit consumption...")
            w, h = (1920, 1080) if aspect_ratio == "16:9" else (1080, 1920)
            from PIL import Image, ImageDraw
            img = Image.new("RGB", (w, h), color=(20, 20, 24))
            draw = ImageDraw.Draw(img)
            draw.rectangle([25, 25, w - 25, h - 25], outline=(223, 160, 40), width=6)
            img.save(thumb_png, format="PNG")
            img.save(thumb_jpg, format="JPEG", quality=95)
            print(f"  [✔] Dry-run thumbnail created: {thumb_png.name}")
            return {"png": thumb_png, "jpg": thumb_jpg}

        # Check budget authorization
        remaining = self.flow_client.get_remaining_quota()
        if remaining <= 0:
            raise FlowQuotaExceededError("Daily Flow credit quota exhausted. Cannot generate thumbnail.")

        # Require authorization if not auto_approved
        has_auth = auto_approve or get_setting("auto_approve_credits", False, self.workspace_dir)
        if not has_auth and sys.stdin.isatty():
            choice = input(f"Flow Thumbnail requires 1 generation credit (Remaining: {remaining}). Proceed? [Y/n]: ").strip().lower()
            if choice in ["n", "no"]:
                print("[*] Flow thumbnail generation skipped by user choice. No credits spent.")
                return {"png": thumb_png, "jpg": thumb_jpg}

        # 4. Generate brand new image via Google Flow image generation
        raw_temp = output_dir / f"raw_thumbnail_{int(os.getpid())}.jpg"
        clean_bin = shutil.which("flow-auto")

        self.flow_client.generate_image(
            prompt=full_prompt,
            output_path=raw_temp,
            scene_idx=99,
            reference_image=resolved_ref,
            folder_name="scenecraft_thumbnail",
            aspect_ratio=aspect_ratio,
            dry_run=False,
        )

        # Clean watermark if available
        if clean_bin:
            try:
                subprocess.run(
                    ["flow-auto", "clean", str(raw_temp), "--mark", "flow", "-o", str(thumb_jpg)],
                    check=True,
                    capture_output=True,
                )
            except Exception:
                shutil.copy2(raw_temp, thumb_jpg)
        else:
            shutil.copy2(raw_temp, thumb_jpg)

        # Convert to PNG for master thumbnail
        from PIL import Image
        with Image.open(thumb_jpg) as im:
            im.save(thumb_png, format="PNG")

        if raw_temp.exists():
            raw_temp.unlink()

        print(f"  [✔] Flow AI Thumbnail generated successfully: {thumb_png.name} & {thumb_jpg.name}")
        return {"png": thumb_png, "jpg": thumb_jpg}

    def generate_thumbnail(
        self,
        prompt: str,
        output_path: Path,
        title_hook: str = "",
        aspect_ratio: str = "16:9",
        style_preset: str = "dark_cinematic",
        use_flow: bool = True,
    ) -> Path:
        """Backward-compatible thumbnail generator.
        
        If use_flow is True and Flow is connected, generates via Flow AI.
        Otherwise falls back to high-contrast procedural graphic rendering.
        """
        output_path = Path(output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        w, h = (1920, 1080) if aspect_ratio == "16:9" else (1080, 1920)

        if use_flow:
            try:
                story_mock = {
                    "story_title": title_hook or "Cinematic Story",
                    "genre": style_preset,
                    "scenes": [{"visual_description": prompt, "tension_level": 9.0}],
                }
                res = self.generate_flow_ai_thumbnail(
                    story_data=story_mock,
                    output_dir=output_path.parent,
                    aspect_ratio=aspect_ratio,
                    style_preset="earthy_explainer" if style_preset == "earthy_explainer" else "dark_cinematic",
                    custom_prompt=prompt,
                    dry_run=False,
                )
                if output_path.suffix.lower() == ".png" and res["png"].is_file():
                    if res["png"] != output_path:
                        shutil.copy2(res["png"], output_path)
                    return output_path
                elif res["jpg"].is_file():
                    if res["jpg"] != output_path:
                        shutil.copy2(res["jpg"], output_path)
                    return output_path
            except Exception as e:
                print(f"  [!] Flow thumbnail generation unavailable ({e}), using high-contrast procedural render...")

        # Procedural fallback render
        from PIL import Image, ImageDraw
        img = Image.new("RGB", (w, h), color=(15, 15, 20))
        draw = ImageDraw.Draw(img)
        draw.rectangle([30, 30, w - 30, h - 30], outline=(220, 160, 40), width=8)
        text = title_hook.upper() if title_hook else "SCENECRAFT"
        draw.text((w // 2, h // 2), text, fill=(255, 255, 255), anchor="mm")
        img.save(output_path)
        return output_path

    def regenerate_thumbnail(
        self,
        output_dir: Path,
        revised_prompt: str,
        story_data: Optional[Dict[str, Any]] = None,
        aspect_ratio: str = "16:9",
        style_preset: str = "earthy_explainer",
        dry_run: bool = False,
    ) -> Dict[str, Path]:
        """Regenerate the video's thumbnail using a revised, user-specified prompt."""
        output_dir = Path(output_dir).resolve()

        if not story_data:
            script_path = output_dir / "story_script.json"
            if script_path.is_file():
                with open(script_path, "r", encoding="utf-8") as f:
                    story_data = json.load(f)
            else:
                story_data = {
                    "story_title": output_dir.name,
                    "scenes": [],
                }

        print(f"\n[*] Regenerating Flow AI Thumbnail with revised prompt...")
        print(f"    Revised Prompt: {revised_prompt}")

        return self.generate_flow_ai_thumbnail(
            story_data=story_data,
            output_dir=output_dir,
            aspect_ratio=aspect_ratio,
            style_preset=style_preset,
            custom_prompt=revised_prompt,
            dry_run=dry_run,
        )
