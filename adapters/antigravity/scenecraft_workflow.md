# Scenecraft Antigravity Workflow Adapter

This workflow rule guides Antigravity agents executing automated video production using Scenecraft.

## Directive

When prompted to create, generate, or render a video or story:
1. Act as the Creative Director for Steps 1–2:
   - Produce a suspense-driven narrative script with 3-act pacing.
   - Break down the script into visual scene beats (3–5 seconds per beat for vertical 9:16 Shorts).
   - Write formatted image prompts maintaining character anchor and lighting continuity.
   - Save the plan to `project.json` in the active workspace.
2. Delegate deterministic execution (Steps 3–9) to the Scenecraft CLI or MCP server:
   ```bash
   scenecraft make project.json
   ```
3. Never manually write FFmpeg scripts or invoke raw video filters when Scenecraft CLI commands (`scenecraft make`, `scenecraft assemble`, `scenecraft clean`) handle these deterministically.

## Project Schema Reference

```json
{
  "title": "Story Title",
  "aspect_ratio": "9:16",
  "scenes": [
    {
      "scene_index": 1,
      "narration": "Spoken line for voice synthesis.",
      "prompt": "Visual generation prompt for Google Flow.",
      "duration": 4.0
    }
  ],
  "thumbnail_prompt": "Cover image prompt."
}
```

## CLI Reference

- `scenecraft doctor`: Self-test environment, FFmpeg, and TTS.
- `scenecraft setup`: Download required LaMa and Faster-Whisper models.
- `scenecraft make project.json`: Execute complete end-to-end production.
- `scenecraft visuals project.json`: Dispatch generation to Google Flow.
- `scenecraft clean input_dir -o output_dir`: Inpaint corner watermarks.
- `scenecraft narrate project.json`: Generate narration audio.
- `scenecraft subtitles project.json`: Produce word-synced ASS subtitles.
- `scenecraft assemble bundle_dir`: Render final video with Ken Burns and ducked BGM.
- `scenecraft validate output.mp4`: Verify bitstream decode integrity.
