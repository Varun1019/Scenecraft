# StoryForge

Local CLI automation tool that generates vertical (9:16) stickman story shorts from a story title.

## Features
- **Style Match**: 2D stickman character (round white head, dot eyes, mustard yellow beanie, grey scarf) with moody atmospheric backgrounds.
- **Google Flow / Nano Banana Integration**: Integrates directly with Flow Connector extension via `flow-auto` CLI.
- **Quota & Limit Safe**: Strictly enforces daily 30-image budget to protect Google accounts. Falls back to local rendering if disconnected or limit reached.
- **Narration & Subtitles**: Neural voice narration (`edge-tts`) with synchronized, burn-in ASS subtitles.
- **Verified Audio**: CC0/Public Domain procedural SFX and dark ambient drone BGM tracked in `assets/licenses.json`. Unverified audio rejected.
- **FFmpeg Engine**: Ken Burns zooms (zoom in/out, pan left/right), transitions, and background music ducking.

## Usage

### Check Status & Quota
```bash
storyforge status
```

### Generate a Video
```bash
storyforge run "The 30th Floor"
```
Or directly:
```bash
storyforge "The 30th Floor"
```

Finished video is exported to `output/<Title>.mp4`.
