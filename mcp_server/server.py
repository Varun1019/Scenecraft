"""Scenecraft MCP Server.

Exposes deterministic pipeline steps as Model Context Protocol (MCP) tools for
AI coding agents (Antigravity, Claude Code, Cursor, etc.).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Optional

try:
    from mcp.server.mcpserver import MCPServer as FastMCP
except ImportError:
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        FastMCP = None

if FastMCP is None:
    raise ImportError("The 'mcp' Python package is required to run the Scenecraft MCP server. Install with `pip install mcp`.")

server = FastMCP("scenecraft")


@server.tool()
def doctor() -> str:
    """Run comprehensive system diagnostics across GPU, FFmpeg, models, TTS, and Flow extension bridge.
    
    Returns:
        Formatted diagnostic report string.
    """
    from scenecraft.doctor import SystemDoctor
    doc = SystemDoctor()
    return doc.format_report()


@server.tool()
def setup(whisper_model: str = "base", force: bool = False) -> str:
    """Download LaMa ONNX and Whisper models with resumable progress.
    
    Args:
        whisper_model: Whisper model size (tiny, base, small, medium, large-v3).
        force: Force re-download of existing models.
    """
    from scenecraft.setup_cmd import run_setup
    success = run_setup(whisper_model=whisper_model, force=force)
    return "Setup completed successfully." if success else "Setup failed. Check logs."


@server.tool()
def visuals(project_json: str, output_dir: str = "", dry_run: bool = False) -> str:
    """Generate AI visual assets for project scenes using Google Flow.
    
    Args:
        project_json: Path to project.json file.
        output_dir: Optional destination directory for images.
        dry_run: Preview prompts without sending generation calls to Flow.
    """
    p = Path(project_json).resolve()
    if not p.is_file():
        return f"Error: Project file not found: {p}"
    
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    scenes = data.get("scenes", [])
    if not scenes:
        return "Error: No scenes found in project.json."

    from scenecraft.flow_client import FlowClient
    from scenecraft.narrator import slugify

    title = data.get("story_title", data.get("title", "project"))
    out_p = Path(output_dir).resolve() if output_dir else Path.cwd() / "output" / slugify(title) / "images"
    out_p.mkdir(parents=True, exist_ok=True)

    client = FlowClient()
    if not dry_run:
        status = client.check_connection()
        if not status.get("connected"):
            return "Error: Google Flow extension bridge is not connected on port 8795."

    results = []
    for idx, sc in enumerate(scenes, 1):
        prompt = sc.get("prompt") or sc.get("image_prompt") or sc.get("visual_prompt")
        if not prompt:
            prompt = sc.get("description") or sc.get("narration") or f"Cinematic scene {idx}"
        target_path = out_p / f"scene_{idx:02d}.jpg"
        if dry_run:
            results.append(f"Scene {idx}: [DRY RUN] Would write to {target_path}")
            continue
        res = client.generate_image(prompt=prompt, output_path=target_path, scene_idx=idx)
        results.append(f"Scene {idx}: Generated {res}")

    return f"Generated {len(results)} visual assets in {out_p}:\n" + "\n".join(results)


@server.tool()
def clean(input_path: str, output_path: str, corner: str = "bottom-right") -> str:
    """Clean visible corner watermarks from an image file or directory using LaMa ONNX.
    
    Args:
        input_path: Path to input image file or directory containing images.
        output_path: Path to output file or output directory.
        corner: Watermark corner location (bottom-right, bottom-left, top-right, top-left).
    """
    from scenecraft.cleaner import clean_directory, clean_image, CleanerOptions
    in_p = Path(input_path).resolve()
    out_p = Path(output_path).resolve()
    opts = CleanerOptions(corner=corner)

    if in_p.is_dir():
        results = clean_directory(in_p, out_p, opts=opts)
        return f"Successfully cleaned {len(results)} images to: {out_p}"
    elif in_p.is_file():
        target = out_p if out_p.suffix else out_p / in_p.name
        res = clean_image(in_p, target, opts=opts)
        return f"Successfully cleaned image saved to: {res}"
    return f"Error: Invalid input path: {in_p}"


@server.tool()
def narrate(project_json: str, output_path: str = "", engine: str = "") -> str:
    """Synthesize voice narration audio from project.json scenes.
    
    Args:
        project_json: Path to project.json file.
        output_path: Destination WAV path. If omitted, saves under output/<slug>/audio/.
        engine: TTS engine name (omnivoice, edge_tts, piper). If omitted, uses config default.
    """
    p = Path(project_json).resolve()
    if not p.is_file():
        return f"Error: Project file not found: {p}"
    
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    scenes = data.get("scenes", [])
    if not scenes:
        return "Error: No scenes found in project.json."

    from scenecraft.narrator import slugify
    from scenecraft.tts import get_tts_engine

    title = data.get("story_title", data.get("title", "narration"))
    slug = slugify(title)
    out_file = Path(output_path).resolve() if output_path else Path.cwd() / "output" / slug / "audio" / "narration.wav"
    out_file.parent.mkdir(parents=True, exist_ok=True)

    text = " ".join(s.get("narration", "") for s in scenes)
    tts = get_tts_engine(engine or None)
    duration = tts.generate(text, out_file)
    return f"Narration synthesized successfully ({duration:.2f}s) at: {out_file}"


@server.tool()
def subtitles(project_json: str, audio_path: str = "", output_path: str = "") -> str:
    """Generate word-synced ASS subtitles from narration audio and project scenes.
    
    Args:
        project_json: Path to project.json file.
        audio_path: Path to narration WAV audio file.
        output_path: Destination .ass subtitle file path.
    """
    from scenecraft.narration import generate_synchronized_subtitles
    from scenecraft.narrator import slugify

    p = Path(project_json).resolve()
    if not p.is_file():
        return f"Error: Project file not found: {p}"
    
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    scenes = data.get("scenes", [])

    audio_p = Path(audio_path).resolve() if audio_path else None
    if not audio_p or not audio_p.is_file():
        title = data.get("story_title", data.get("title", "narration"))
        audio_p = Path.cwd() / "output" / slugify(title) / "audio" / "narration.wav"

    if not audio_p.is_file():
        return f"Error: Audio file missing: {audio_p}"

    out_ass = Path(output_path).resolve() if output_path else audio_p.parent.parent / "subtitles" / "subtitles.ass"
    out_ass.parent.mkdir(parents=True, exist_ok=True)

    res = generate_synchronized_subtitles(scenes, audio_p, out_ass)
    return f"Subtitles generated successfully at: {res}"


@server.tool()
def assemble(bundle_path: str, aspect_ratio: str = "9:16", dry_run: bool = False) -> str:
    """Assemble final vertical or horizontal short from project assets.
    
    Args:
        bundle_path: Path to bundle directory containing storyboard_beats.json and assets.
        aspect_ratio: Target aspect ratio ('9:16' for vertical shorts, '16:9' for horizontal).
        dry_run: Simulate assemble render without invoking full FFmpeg.
    """
    bundle_p = Path(bundle_path).resolve()
    if not bundle_p.is_dir():
        return f"Error: Bundle directory not found: {bundle_p}"

    from scenecraft.pipeline import ScenecraftPipeline
    pipeline = ScenecraftPipeline(workspace_dir=bundle_p.parent.parent, dry_run=dry_run)
    res = pipeline.assemble_from_bundle(bundle_dir=bundle_p, aspect_ratio=aspect_ratio, dry_run=dry_run)
    return f"Assembly complete: {json.dumps(res, indent=2, default=str)}"


@server.tool()
def validate(video_path: str) -> str:
    """Validate video stream integrity, decodability, and audio/video specs.
    
    Args:
        video_path: Path to MP4 video file to inspect.
    """
    vid_p = Path(video_path).resolve()
    if not vid_p.is_file():
        return f"Error: Video file not found: {vid_p}"

    res = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(vid_p), "-f", "null", "-"],
        capture_output=True,
        text=True,
    )
    if res.returncode != 0 or res.stderr.strip():
        return f"Stream validation FAILED:\n{res.stderr.strip()}"
    return f"Stream validation PASSED: Zero decode corruption in {vid_p.name}."


def main():
    server.run()


if __name__ == "__main__":
    main()
