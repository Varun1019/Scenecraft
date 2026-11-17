# Authoritative Scenecraft Production Workflow

This document defines the mandatory, persistent production workflow for all Scenecraft video tasks.
Antigravity MUST strictly execute the production steps in the exact order specified below in every new session or conversation.

---

## The 20-Step Production Order

1. **Inspect Project & Existing Settings**:
   - Verify workspace virtual environment (`.venv/bin/python`).
   - Check available audio engines (VoiceStudio daemon on port 3900 for Option A `6f7af622`, ElevenLabs keys in `.env`).
   - Verify Google Flow Connector status (`flow-auto status --site flow`).

2. **Read Permanent Production Workflow**:
   - Read this document (`.agents/rules/scenecraft_production_workflow.md`) and adhere to its constraints.

3. **Identify Requested Video Format**:
   - Determine target aspect ratio: 9:16 vertical (1080x1920) for Shorts/Reels/TikTok or 16:9 horizontal (1920x1080) for long-form YouTube.
   - Establish target framerate (30 fps progressive) and runtime target.

4. **Inspect Original Story or User-Provided Script**:
   - Check narrative continuity with prior parts or lore (character names, settings, past cliffhangers).
   - Reconcile any discrepancies before modifying or expanding text.

5. **Finalize Narration**:
   - Polish script to match target timing (~130-150 words per minute).
   - Format into clean sequential narrative sentences suitable for speech synthesis.

6. **Create Complete Scene Breakdown**:
   - Divide script into sequential visual beats.
   - Map exact spoken lines, target duration, shot type, and camera motion intent to each beat.

7. **Generate Detailed Flow Agent Master Prompts**:
   - Create comprehensive master prompts for Google Flow Agent.
   - For every beat, define all 10 required attributes:
     1. Exact character appearance.
     2. Character position and pose.
     3. Facial expression and gaze.
     4. Exact environment and background.
     5. Foreground objects and important details.
     6. Camera angle and shot size.
     7. Lighting, shadows, and atmosphere.
     8. Composition and focal point.
     9. What happened in the previous image.
     10. How this image leads into the next image.
   - Strictly prohibit text, subtitles, split panels, or decorative borders inside generated frames.

8. **Establish Character & Style Consistency**:
   - Anchor character visual descriptors to permanent reference files (e.g., `references/brand_identity/ref_character_full_body.jpg`).
   - Enforce uniform art style (e.g., 2D graphic novel dark comic, clean ink lines, cel shading, borderless canvas).

9. **Prepare Sound Effects & Music Cues**:
   - Select certified CC0-1.0 / Public Domain background music and Foley impacts registered in `assets/licenses.json`.
   - Map precise SFX trigger timestamps to narrative events and cuts.

10. **Prepare Thumbnail Prompt**:
    - By default, automatically design a dedicated, independent 9:16 or 16:9 thumbnail prompt matching the target format.
    - Never extract a frame from the video as the thumbnail.

11. **Show Production Plan & Generation Requirements**:
    - Present the complete scene plan, script breakdown, audio plan, and estimated credit/render costs to the user.

12. **Obtain Approval for Credit-Consuming Operations**:
    - Always wait for explicit user approval before submitting batches to Flow or consuming billable credits.

13. **Generate & Organize Visual Assets**:
    - Ingest or generate images/clips via Flow Connector or Flow Agent.
    - Organize assets inside `output/<project_slug>/images/` or `output/<project_slug>/video/`.

14. **Generate Narration Using Permanent Voice Option A ("6f7af622")**:
    - Use permanent narrator Option A (`6f7af622`, Rooftop Survivor) via VoiceStudio on port 3900.
    - Preserve natural cadence and pitch settings. Never silently switch voice providers.

15. **Generate Subtitles**:
    - Extract word-level timestamps using Faster-Whisper.
    - Format into non-overlapping ASS subtitles styled with high-contrast outline and drop shadow.
    - Enforce vertical/horizontal mobile safe zones. Ensure previous cues disappear before subsequent cues appear.

16. **Assemble & Render Video**:
    - Apply 2.5D Ken Burns camera motion or normalize video clips to 30 fps.
    - Mix multi-layer audio (dialogue, sidechain-ducked BGM, positioned SFX) to -14 LUFS standard.
    - Mux audio, video, and burned ASS subtitles using hardware NVENC (`h264_nvenc`) with CPU libx264 fallback.

17. **Generate Independent Thumbnail Through Flow**:
    - Automatically submit or provide the dedicated thumbnail prompt.
    - Save the generated image as `thumbnail.png` in the project directory.

18. **Verify Final Video, Audio, Subtitles, and Thumbnail**:
    - Run `ffmpeg -v error -i <video> -f null -` to verify zero stream corruption.
    - Check subtitle timing for overlaps.
    - Probe resolution, aspect ratio, audio bitrate, and duration.

19. **Save All Outputs in Correct Project Folder**:
    - Store all deliverables in `output/<project_slug>/`:
      - `output/<project_slug>/<project_slug>.mp4` (Master video)
      - `output/<project_slug>/thumbnail.png` (Master thumbnail)
      - `output/<project_slug>/images/` (Scene assets)
      - `output/<project_slug>/audio/` (Master audio & narration stems)
      - `output/<project_slug>/subtitles/` (ASS subtitle file)
      - `output/<project_slug>/metadata/` (Manifest, description, timestamps, tags)

20. **Produce Final Production Report**:
    - Deliver verified paths, runtimes, specs, and complete copy-pasteable YouTube/Reels metadata package.

---

## Critical Production Guardrails

- **Automatic Thumbnail**: Never require the user to ask for a thumbnail separately. Generate dedicated thumbnail prompts automatically for every project.
- **Subtitles**: Subtitles must never overlap. Subtitle events must strictly terminate before the next cue begins. Keep text inside the 9:16 or 16:9 safe zone.
- **Watermark Policy**: Do not alter or bypass existing watermark handling or attempt to circumvent Google Flow / provider watermark policies. Keep existing watermark implementations intact.
- **Audio Licensing**: Strictly use CC0-1.0 or Public Domain licensed tracks verified in `assets/licenses.json`.
