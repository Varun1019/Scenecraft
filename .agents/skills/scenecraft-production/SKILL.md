---
name: scenecraft-production
description: >-
  Use this skill when developing, testing, rendering videos, debugging FFmpeg pipelines, or managing audio licenses in Scenecraft.
---

# Scenecraft Production & Engineering Runbook

> **MANDATORY PRODUCTION DIRECTIVE**:
> All video production tasks must strictly follow the permanent 20-step order defined in:
> [Scenecraft Production Workflow](.agents/rules/scenecraft_production_workflow.md).

This skill provides step-by-step procedures for developing, testing, and running the Scenecraft automated story video generation engine.

## Codebase Architecture Overview

- **Pipeline Orchestration**: `scenecraft/pipeline.py` (Short-form 9:16 vertical) and `scenecraft/pipeline_longform.py` (16:9 horizontal + reframed shorts).
- **Narrative Engine**: `scenecraft/story_engine.py` (3-act retention structure, script adaptation) and `scenecraft/story_gen.py`.
- **Narration & Subtitles**: `scenecraft/narration.py` (Edge-TTS and word-level ASS subtitles) and `scenecraft/elevenlabs_client.py` (Dual-key API with quota failover).
- **Video Rendering**: `scenecraft/video_engine.py` (FFmpeg-based 2.5D Ken Burns zoom/pan, clip normalization to 30 fps).
- **Audio Verification & Mixing**: `scenecraft/audio_manager.py` (Strict CC0/Public Domain licensing enforcement via `assets/licenses.json`, dynamic vocal sidechain ducking).
- **Visual Client**: `scenecraft/flow_client.py` (Google Flow / Nano Banana via `flow-auto` on port 8791 with daily budget tracking).

---

## 1. Running the Test Suite

Always run the full test suite before committing changes or after refactoring:

```bash
python3 -m unittest discover tests
```

> **Note**: Always use `python3 -m unittest discover tests` rather than `pytest`, as standard environment dependencies rely on unittest discovery.

---

## 2. CLI Execution & Status

### Check Daily Generation Allowance and Quotas
```bash
python3 -m scenecraft.cli status
```
Quota tracking is stored locally in `~/.scenecraft/usage.json`.

### Run Short-Form Video Generation
```bash
python3 -m scenecraft.cli run "The 30th Floor"
```
Outputs are written to `output/<sanitized_title>/`.

---

## 3. Audio Licensing Guardrails

YouTube monetization safety requires all background music (BGM) and sound effects (SFX) to be registered in `assets/licenses.json` (v2.0 schema).
- Audio files missing from `licenses.json` or lacking CC0-1.0 / Public Domain certification trigger a fatal `LicenseError`.
- When adding new SFX or BGM, update `assets/licenses.json` with source URL and CC0 licensing terms.

---

## 4. Video Engine Verification

All produced videos should be validated using `verify_video` or FFprobe:
```bash
ffprobe -v error -show_format -show_streams -print_format json output/<video_file>.mp4
ffmpeg -v error -i output/<video_file>.mp4 -f null -
```
Ensure video streams conform to:
- Vertical: `1080x1920` @ 30 fps (h264 / aac)
- Landscape: `1920x1080` @ 30 fps (h264 / aac)
