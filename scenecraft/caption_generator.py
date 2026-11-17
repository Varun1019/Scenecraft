"""Social Media Video Caption Generator for Scenecraft / Tales Nova.

Generates ready-to-post captions for YouTube Shorts and Instagram Reels
based on the actual story, with:
1. Episode Header (standalone vs series aware)
2. Suspenseful Story Description (2-3 short, engaging staccato sentences)
3. Episode Information (strictly verified, no invented schedules)
4. Engagement Question (provocative call-to-comment)
5. 4-6 targeted, genre-specific Hashtags
6. Platform support (YouTube Shorts & Instagram Reels)
7. Clipboard copy & Interactive HTML preview/edit widget
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple


GENRE_HASHTAGS = {
    "psychological horror": ["#horror", "#analoghorror", "#suspense", "#storytime", "#thriller", "#shorts"],
    "horror": ["#horror", "#scary", "#suspense", "#storytime", "#thriller", "#shorts"],
    "psychological suspense": ["#suspense", "#mystery", "#psychological", "#storytime", "#whatif", "#shorts"],
    "suspense": ["#suspense", "#thriller", "#mystery", "#storytime", "#whatif", "#shorts"],
    "survival": ["#survival", "#apocalypse", "#escaperoom", "#storytime", "#whatif", "#shorts"],
    "mystery": ["#mystery", "#unsolved", "#darkmystery", "#storytime", "#creepypasta", "#shorts"],
    "sci-fi": ["#scifi", "#timeloop", "#paralleluniverse", "#storytime", "#whatif", "#shorts"],
    "zombie": ["#zombie", "#survival", "#apocalypse", "#storytime", "#whatif", "#shorts"],
}


def copy_to_clipboard(text: str) -> bool:
    """Copy text to system clipboard across Wayland, X11, macOS, and Windows."""
    # 1. Wayland (wl-copy)
    if shutil.which("wl-copy"):
        try:
            p = subprocess.Popen(["wl-copy"], stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
            p.communicate(text.encode("utf-8"))
            if p.returncode == 0:
                return True
        except Exception:
            pass

    # 2. X11 (xclip)
    if shutil.which("xclip"):
        try:
            p = subprocess.Popen(["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
            p.communicate(text.encode("utf-8"))
            if p.returncode == 0:
                return True
        except Exception:
            pass

    # 3. macOS (pbcopy)
    if shutil.which("pbcopy"):
        try:
            p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
            p.communicate(text.encode("utf-8"))
            if p.returncode == 0:
                return True
        except Exception:
            pass

    # 4. python pyperclip fallback if installed
    try:
        import pyperclip
        pyperclip.copy(text)
        return True
    except Exception:
        pass

    return False


@dataclass
class SocialCaption:
    title: str
    header: str
    description: str
    episode_info: Optional[str]
    engagement_question: str
    hashtags: List[str]
    platform: str = "youtube_shorts"
    genre: str = "Suspense"

    def format_text(self, platform: Optional[str] = None) -> str:
        """Render plain text caption formatted for specific platform."""
        plat = (platform or self.platform).lower()
        tags = list(self.hashtags)

        # Platform-specific hashtag adaptation
        if "instagram" in plat or "reels" in plat:
            tags = [t.replace("#shorts", "#reels") for t in tags]
            if "#reels" not in tags:
                tags.append("#reels")
            if "#shortfilm" not in tags and len(tags) < 6:
                tags.append("#shortfilm")

        lines = [self.header, "", self.description]

        if self.episode_info and self.episode_info.strip():
            lines.extend(["", self.episode_info.strip()])

        lines.extend(["", self.engagement_question, ""])

        if "instagram" in plat or "reels" in plat:
            lines.append(".\n.\n" + " ".join(tags))
        else:
            lines.append(" ".join(tags))

        return "\n".join(lines).strip()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "genre": self.genre,
            "header": self.header,
            "description": self.description,
            "episode_info": self.episode_info,
            "engagement_question": self.engagement_question,
            "hashtags": self.hashtags,
            "formatted_youtube": self.format_text("youtube_shorts"),
            "formatted_instagram": self.format_text("instagram_reels"),
        }


class CaptionGenerator:
    """Generates viral, suspenseful social captions tailored to video metadata."""

    def __init__(self, workspace: Optional[Path] = None):
        self.workspace = workspace or Path.cwd()

    def generate_caption(
        self,
        story_data: Dict[str, Any],
        platform: str = "youtube_shorts",
    ) -> SocialCaption:
        """Create a complete SocialCaption object from story data."""
        title = story_data.get("story_title") or story_data.get("title") or "Untitled Story"
        genre = story_data.get("genre") or "Psychological Suspense"
        series_info = story_data.get("series_info")

        # 1. Header
        header = self._build_header(title, series_info)

        # 2. Suspenseful Story Description
        description = self._build_description(story_data)

        # 3. Episode Information
        episode_info = self._build_episode_info(series_info)

        # 4. Engagement Question
        question = self._build_engagement_question(story_data)

        # 5. Hashtags
        hashtags = self._select_hashtags(genre)

        return SocialCaption(
            title=title,
            header=header,
            description=description,
            episode_info=episode_info,
            engagement_question=question,
            hashtags=hashtags,
            platform=platform,
            genre=genre,
        )

    def _build_header(self, title: str, series_info: Optional[Dict[str, Any]]) -> str:
        """Construct EPISODE HEADER without inventing numbers for standalone stories."""
        clean_title = title.upper().strip()

        if series_info and isinstance(series_info, dict):
            s_name = (series_info.get("series_name") or title).upper().strip()
            ep_num = series_info.get("episode_num")
            part_num = series_info.get("part_num") or series_info.get("episode_num")
            total_parts = series_info.get("total_parts") or series_info.get("total_episodes")

            if ep_num and total_parts:
                return f"{s_name} - EPISODE {ep_num} (PART {part_num}/{total_parts})"
            elif ep_num:
                return f"{s_name} - EPISODE {ep_num}"

        # Standalone: title only
        return clean_title

    def _build_description(self, story_data: Dict[str, Any]) -> str:
        """Synthesize 2-3 staccato, suspenseful sentences that set up premise without spoiling ending."""
        # Try LLM if available
        llm_desc = self._try_llm_description(story_data)
        if llm_desc:
            return llm_desc

        # High-retention rule-based synthesis from story beats
        summary = story_data.get("summary", "")
        scenes = story_data.get("scenes", [])
        hook = story_data.get("opening_hook", "")

        first_scene_narration = scenes[0].get("narration", "") if scenes else ""
        second_scene_narration = scenes[1].get("narration", "") if len(scenes) > 1 else ""

        # Analyze story keywords to formulate staccato suspense beats
        full_context = f"{summary} {hook} {first_scene_narration} {second_scene_narration}".lower()

        if "phone" in full_context and ("countdown" in full_context or "die" in full_context or "sixty" in full_context):
            return "A phone screen glowing in the dark. Zero signal bars, yet the countdown keeps ticking. It warns you not to turn around."

        if "floor" in full_context and "knock" in full_context:
            return "Thirty floors up. The emergency siren wails across the city. The knocks on your locked door are rhythmic, heavy, and not human."

        if "outbreak" in full_context or "zombie" in full_context or "bitten" in full_context:
            return "Three survivors. A single bolted steel door. Your partner takes the midnight watch, but there is something they have not told you."

        if "doppelganger" in full_context or "twin" in full_context or "mirror" in full_context:
            return "An empty room. A reflection that moves half a second too slow. Now you hear footsteps directly behind your shoulder."

        # General staccato beat extractor from premise/first scenes
        sentences = []
        if hook:
            sentences.append(hook.rstrip(".!?") + ".")
        elif summary:
            # Shorten summary into first premise sentence
            first_clause = summary.split(",")[0].strip()
            sentences.append(first_clause.rstrip(".!?") + ".")

        if first_scene_narration:
            first_s = first_scene_narration.split(".")[0].strip()
            if len(first_s.split()) <= 15:
                sentences.append(first_s + ".")

        sentences.append("Whatever happens next, there is no way out.")
        return " ".join(sentences[:3])

    def _try_llm_description(self, story_data: Dict[str, Any]) -> Optional[str]:
        """Optionally generate via GenAI if configured."""
        try:
            from google import genai
            from google.genai import types

            client = genai.Client()
            title = story_data.get("title") or story_data.get("story_title")
            scenes = [s.get("narration") for s in story_data.get("scenes", [])[:3]]
            prompt = (
                "Write an ultra-suspenseful, viral social media description for a 9:16 short.\n"
                f"Title: {title}\n"
                f"Opening scenes: {' '.join(scenes)}\n"
                "Requirements:\n"
                "- Exactly 2 to 3 short, punchy sentences.\n"
                "- Hook the viewer immediately without revealing the twist or ending.\n"
                "- Use natural, gripping storytelling rhythm.\n"
                "- Example style: 'Three people. A bolted door. Your friend takes the middle watch. There is something she has not told you.'\n"
                "Output ONLY the 2-3 sentences as raw text."
            )
            resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.7),
            )
            if resp.text:
                return resp.text.strip().replace('"', '')
        except Exception:
            pass
        return None

    def _build_episode_info(self, series_info: Optional[Dict[str, Any]]) -> Optional[str]:
        """Construct EPISODE INFORMATION only when actually configured in a series."""
        if not series_info or not isinstance(series_info, dict):
            return None

        ep_num = series_info.get("episode_num")
        part_num = series_info.get("part_num") or ep_num
        total_parts = series_info.get("total_parts") or series_info.get("total_episodes")

        if not ep_num or not total_parts:
            return None

        info_line = f"Part {part_num} - Episode {ep_num} ({part_num}/{total_parts})."

        # Mention upcoming parts ONLY if configured/scheduled
        if part_num < total_parts:
            info_line += f" Part {part_num + 1} coming soon."
        elif series_info.get("next_release"):
            info_line += f" Next episode: {series_info['next_release']}."

        return info_line

    def _build_engagement_question(self, story_data: Dict[str, Any]) -> str:
        """Provide a provocative question compelling viewers to comment."""
        custom_q = story_data.get("engagement_question")
        if custom_q and custom_q.strip():
            q = custom_q.strip()
            return q if q.endswith("?") else f"{q}?"

        title = (story_data.get("title") or story_data.get("story_title") or "").lower()
        summary = (story_data.get("summary") or "").lower()
        context = f"{title} {summary}"

        if "phone" in context or "call" in context:
            return "Would you answer that call?"
        if "knock" in context or "door" in context:
            return "Would you open that door?"
        if "look" in context or "behind" in context:
            return "Would you turn around?"
        if "run" in context or "escape" in context:
            return "Where would you hide?"
        if "trust" in context or "friend" in context or "doppelganger" in context:
            return "Who would you trust?"

        return "What would you do in their place?"

    def _select_hashtags(self, genre: str) -> List[str]:
        """Pick 4-6 targeted, non-spammy hashtags based on genre."""
        g_lower = genre.lower().strip()
        for key, tags in GENRE_HASHTAGS.items():
            if key in g_lower:
                return tags[:6]
        return ["#suspense", "#mystery", "#storytime", "#whatif", "#animation", "#shorts"]

    def save_caption_bundle(
        self,
        caption: SocialCaption,
        bundle_dir: Path,
    ) -> Dict[str, Path]:
        """Save caption artifacts alongside finished video in bundle directory."""
        bundle_dir.mkdir(parents=True, exist_ok=True)

        # 1. Plain text file (YouTube Shorts ready)
        txt_path = bundle_dir / "social_caption.txt"
        txt_content = (
            "=== YOUTUBE SHORTS CAPTION ===\n\n"
            f"{caption.format_text('youtube_shorts')}\n\n"
            "===============================\n\n"
            "=== INSTAGRAM REELS CAPTION ===\n\n"
            f"{caption.format_text('instagram_reels')}\n"
        )
        txt_path.write_text(txt_content, encoding="utf-8")

        # 2. JSON structured data
        json_path = bundle_dir / "social_caption.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(caption.to_dict(), f, indent=2)

        # 3. Interactive HTML card with live preview, editable box, and copy buttons
        html_path = bundle_dir / "caption_card.html"
        html_content = self.render_html_widget(caption)
        html_path.write_text(html_content, encoding="utf-8")

        return {
            "txt": txt_path,
            "json": json_path,
            "html": html_path,
        }

    def render_html_widget(self, caption: SocialCaption) -> str:
        """Render a clean, responsive HTML card with tabs, editable text, and instant copy."""
        yt_text = caption.format_text("youtube_shorts").replace("\\", "\\\\").replace("`", "\\`")
        ig_text = caption.format_text("instagram_reels").replace("\\", "\\\\").replace("`", "\\`")

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Social Media Caption - {caption.title}</title>
<style>
  :root {{
    --bg: #0f1117;
    --card: #1a1d27;
    --border: #2a2e3f;
    --accent: #f59e0b;
    --text: #f3f4f6;
    --subtext: #9ca3af;
    --btn-hover: #d97706;
    --success: #10b981;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
  body {{ background: var(--bg); color: var(--text); padding: 24px; display: flex; justify-content: center; }}
  .container {{ width: 100%; max-width: 680px; background: var(--card); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.4); }}
  .header {{ padding: 18px 24px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; background: #131620; }}
  .header h2 {{ font-size: 1.15rem; font-weight: 700; color: #fff; }}
  .badge {{ background: rgba(245, 158, 11, 0.15); color: var(--accent); font-size: 0.75rem; padding: 4px 10px; border-radius: 9999px; font-weight: 600; text-transform: uppercase; }}
  .tabs {{ display: flex; border-bottom: 1px solid var(--border); background: #161922; }}
  .tab {{ flex: 1; padding: 12px; text-align: center; cursor: pointer; color: var(--subtext); font-weight: 600; font-size: 0.9rem; transition: all 0.2s; }}
  .tab.active {{ color: var(--accent); border-bottom: 2px solid var(--accent); background: var(--card); }}
  .body {{ padding: 20px 24px; }}
  .preview-area {{ position: relative; }}
  textarea {{ width: 100%; height: 210px; background: #12141c; color: #fff; border: 1px solid var(--border); border-radius: 8px; padding: 14px; font-size: 0.95rem; line-height: 1.55; resize: vertical; outline: none; }}
  textarea:focus {{ border-color: var(--accent); }}
  .stats {{ display: flex; justify-content: space-between; color: var(--subtext); font-size: 0.8rem; margin: 8px 0 16px; }}
  .actions {{ display: flex; gap: 12px; justify-content: flex-end; }}
  .btn {{ padding: 10px 20px; border-radius: 6px; font-size: 0.9rem; font-weight: 600; cursor: pointer; border: none; transition: 0.2s; display: inline-flex; align-items: center; gap: 8px; }}
  .btn-primary {{ background: var(--accent); color: #000; }}
  .btn-primary:hover {{ background: var(--btn-hover); }}
  .btn-secondary {{ background: #262b3d; color: var(--text); border: 1px solid var(--border); }}
  .btn-secondary:hover {{ background: #32384e; }}
  .copied-toast {{ display: none; color: var(--success); font-weight: 600; font-size: 0.85rem; align-items: center; }}
</style>
</head>
<body>

<div class="container">
  <div class="header">
    <h2>Social Caption Generator</h2>
    <span class="badge">{caption.genre}</span>
  </div>

  <div class="tabs">
    <div class="tab active" id="tab-yt" onclick="switchPlatform('youtube')">YouTube Shorts</div>
    <div class="tab" id="tab-ig" onclick="switchPlatform('instagram')">Instagram Reels</div>
  </div>

  <div class="body">
    <div class="preview-area">
      <textarea id="captionText" oninput="updateStats()"></textarea>
    </div>

    <div class="stats">
      <span id="charCount">0 characters</span>
      <span id="wordCount">0 words</span>
    </div>

    <div class="actions">
      <span class="copied-toast" id="toast">✔ Copied to clipboard!</span>
      <button class="btn btn-secondary" onclick="resetDefault()">Reset</button>
      <button class="btn btn-primary" onclick="copyCaption()">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
        Copy Caption
      </button>
    </div>
  </div>
</div>

<script>
  const ytData = `{yt_text}`;
  const igData = `{ig_text}`;
  let currentPlatform = 'youtube';

  const textarea = document.getElementById('captionText');
  const toast = document.getElementById('toast');

  function setContent(text) {{
    textarea.value = text;
    updateStats();
  }}

  function switchPlatform(p) {{
    currentPlatform = p;
    document.getElementById('tab-yt').classList.toggle('active', p === 'youtube');
    document.getElementById('tab-ig').classList.toggle('active', p === 'instagram');
    setContent(p === 'youtube' ? ytData : igData);
  }}

  function resetDefault() {{
    setContent(currentPlatform === 'youtube' ? ytData : igData);
  }}

  function updateStats() {{
    const val = textarea.value;
    document.getElementById('charCount').textContent = val.length + ' characters';
    const words = val.trim() ? val.trim().split(/\\s+/).length : 0;
    document.getElementById('wordCount').textContent = words + ' words';
  }}

  async function copyCaption() {{
    try {{
      await navigator.clipboard.writeText(textarea.value);
      toast.style.display = 'inline-flex';
      setTimeout(() => {{ toast.style.display = 'none'; }}, 2500);
    }} catch (err) {{
      textarea.select();
      document.execCommand('copy');
      toast.style.display = 'inline-flex';
      setTimeout(() => {{ toast.style.display = 'none'; }}, 2500);
    }}
  }}

  // Init
  switchPlatform('youtube');
</script>
</body>
</html>
"""
