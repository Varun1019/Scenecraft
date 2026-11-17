---
name: scenecraft
description: >-
  Create complete viral short-form (9:16) or cinematic (16:9) videos from any topic or script using the Scenecraft automated video production engine.
---

# Scenecraft Production Skill

Use this skill when the user asks to create, produce, or render a video, short, reel, or story using Scenecraft.

## Architecture

The pipeline divides responsibility cleanly:
1. **Agent (Steps 1-2):** Creative writing, scene pacing, and visual prompting. The agent writes `project.json`.
2. **Deterministic CLI (Steps 3-9):** Visuals generation, LaMa watermark cleaning, voice narration synthesis, word-synced subtitles, audio mixing, and FFmpeg video assembly.

---

## Workflow Instructions

### Step 1: Creative Script & Scene Breakdown
Break the user's concept into visual scene beats (3–5 seconds per beat for vertical Shorts, 5–10s for 16:9).
For each scene, craft:
- `narration`: Tight, suspenseful, retention-engineered spoken voiceover text.
- `prompt`: Highly descriptive cinematic prompt formatted for Google Flow (Nano Banana Pro / Veo).

### Step 2: Write `project.json`
Write the scene plan directly to a `project.json` file in the project folder:

```json
{
  "title": "Story Title",
  "aspect_ratio": "9:16",
  "scenes": [
    {
      "scene_index": 1,
      "narration": "First spoken line...",
      "prompt": "Cinematic visual prompt, 2D graphic novel style, rim lighting, 8k...",
      "duration": 4.0
    }
  ],
  "thumbnail_prompt": "Cinematic high-contrast YouTube Shorts thumbnail..."
}
```

### Step 3: Run Deterministic Pipeline
Execute the deterministic CLI:

```bash
scenecraft make project.json
```

Or execute individual stages if debugging or customizing:
- `scenecraft doctor`: Verify environment and dependencies.
- `scenecraft visuals project.json`: Generate AI visuals via Google Flow.
- `scenecraft clean input_dir -o output_dir`: Remove corner watermarks with LaMa ONNX.
- `scenecraft narrate project.json`: Synthesize voice narration.
- `scenecraft subtitles project.json`: Generate word-synced ASS subtitles.
- `scenecraft assemble bundle_dir`: Render the final video.
- `scenecraft validate output.mp4`: Verify bitstream decode integrity.
