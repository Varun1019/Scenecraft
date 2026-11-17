# Scenecraft: Development Baseline & Architectural Audit

**Date**: 2026-11-02  
**Status**: Production Cleanup Complete / Ready for Development Phase  
**Test Suite**: 14/14 tests passing (`python3 -m unittest discover tests`)

---

## 1. Executive Summary

Scenecraft has successfully concluded its initial multi-format production phase, delivering four vertical short-form narrative videos across deep sea sci-fi horror, desert archaeology mystery, zombie apocalypse survival, and psychological arctic suspense. 

All temporary production renders, intermediate clips, old output bundles, and transient run state have been safely purged. The codebase, unit tests, CLI, licensed audio assets, and project configurations remain intact and fully operational.

---

## 2. Current Features & Capabilities

### 2.1 Narrative & Planning Engine (`scenecraft/story_engine.py`, `scenecraft/prompt_builder.py`)
- **Retention-Optimized Story Plans**: 3-act vertical narrative structures with a mandatory 3-second hook, visual variety across 8–10 scenes, and cliffhanger endings.
- **Script Adaptation**: Converts raw text or script files into visual Story Plans (`raw`, `smart_split`, `expanded`).
- **Episodic Series Management**: Persistent JSON story bibles with character visual anchors, established lore, and multi-episode continuity.

### 2.2 Voice & Subtitle Engine (`scenecraft/narration.py`, `scenecraft/elevenlabs_client.py`)
- **Dual Narration Architecture**:
  - Free high-speed TTS via `edge-playback` with configurable speech rate and pitch.
  - Studio-grade cinematic narration via ElevenLabs API (`ElevenLabsClient`) supporting character voices (e.g., George, Charlie).
- **Karaoke Subtitle Generation**: Generates word-synced ASS subtitles with highlighted text, custom font margins, and mobile-optimized vertical positioning.

### 2.3 Audio Management & Licensing (`scenecraft/audio_manager.py`)
- **Strict YouTube Monetization Verification**: Enforces `assets/licenses.json` v2.0 schema (CC0-1.0 and Public Domain assets only). Unverified audio files trigger a `LicenseError`.
- **Broadcast-Grade Audio Mixing**:
  - Dynamic sidechain ducking: BGM is automatically ducked by 12–14 dB during vocal speech.
  - Vocal Clarity EQ: 85 Hz highpass, 400 Hz boxiness cut, 3.4 kHz presence boost.
  - SFX Gain Matrix: Attenuated to -28 dB to -20 dB relative to voice (integrated loudness target: -14 to -16 LUFS).

### 2.4 Video Rendering Engine (`scenecraft/video_engine.py`)
- **Hybrid Input Support**: Standardizes both still images (via 2.5D Ken Burns zoom and pan) and generative video clips into vertical (1080x1920) or horizontal (1920x1080) formats at 30 fps.
- **Complex Audio/Visual Muxing**: Combines video streams, narration, ducked BGM, and timestamped sound effect cues in a single FFmpeg execution.

### 2.5 Visual Generation Client (`scenecraft/flow_client.py`, `flow-auto`)
- **Google Flow Integration**: Bridges to Google Flow via local HTTP daemon (port 8791) and the Chrome extension.
- **Daily Quota Enforcement**: Tracks image and video limits (40 images/day, 30 videos/day) in `~/.scenecraft/usage.json`.

### 2.6 Social Distribution (`scenecraft/caption_generator.py`)
- Formats viral copy for YouTube Shorts and Instagram Reels with high-converting hooks, curiosity gaps, and targeted hashtag groups.

---

## 3. Existing Architecture

```
Scenecraft/
├── assets/
│   ├── audio/
│   │   ├── bgm/            # Verified CC0 ambient music
│   │   └── sfx/            # 19 verified CC0/PD sound effects
│   ├── imported/           # Reference art & style sheets
│   └── licenses.json       # Audio licensing manifest (v2.0)
├── scenecraft/
│   ├── __init__.py
│   ├── audio_manager.py    # Audio verification, ducking, and SFX mapping
│   ├── caption_generator.py# Social media metadata and caption formatting
│   ├── chatgpt_bridge.py   # AI collaboration & automated architectural review
│   ├── cli.py              # Main CLI entrypoint
│   ├── elevenlabs_client.py# ElevenLabs narration client
│   ├── flow_client.py      # Google Flow generation client & quota tracker
│   ├── narration.py        # Narration generation & ASS word-level subtitles
│   ├── pipeline.py         # End-to-end automated orchestration pipeline
│   ├── prompt_builder.py   # Scene-to-prompt visual translation
│   ├── story_engine.py     # Story planning, script adaptation & series bibles
│   ├── story_gen.py        # High-retention narrative generator
│   └── video_engine.py     # FFmpeg composition & Ken Burns rendering
├── tests/
│   ├── test_caption_generator.py
│   ├── test_chatgpt_bridge.py
│   └── test_scenecraft.py
├── output/                 # Clean workspace for finished productions
├── temp/                   # Clean scratchpad for intermediate renders
├── generated_images/       # Clean directory for raw image outputs
├── series/                 # Clean directory for episodic series bibles
└── DEVELOPMENT_BASELINE.md # Architectural report
```

---

## 4. Known Bugs & Edge Cases

1. **Incomplete Downloads Missing `moov` Atom**:
   - Video clips downloaded over high-latency connections or during CDN throttling can result in truncated MP4 files without a `moov` atom, causing FFmpeg concatenation to fail with exit status 183.
2. **Google Flow Content Policy False Positives**:
   - Descriptive thriller prompts (e.g., "bloody hands", "violent impact") trigger Google Flow safety filters without a graceful prompt mitigation fallback, leading to job stalls or anti-bot cooldowns (~9.5 minutes).
3. **Video Model Watermark Disparity**:
   - Google Flow video models (`omni-flash`) hardcode the Gemini star icon and SynthID server-side, whereas image models (`nano-banana-pro`) produce clean, watermark-free stills. The pipeline needs explicit rendering profile selection.
4. **Test Runner Dependency**:
   - The test suite requires `python3 -m unittest discover tests` because `pytest` is not installed in the global system environment.

---

## 5. Technical Limitations

1. **Browser State Dependency**:
   - Flow generation requires an active, focused Google Chrome session and an active bridge daemon (port 8791). Narrow or tiled window states can trigger mobile UI modes in Flow that restrict prompt options.
2. **FFmpeg Command-Line Filtergraph Size**:
   - Chaining 15+ sound effects in a single filtergraph command can push parameter limits and complicates localized audio debugging.
3. **Daily Generation Caps**:
   - 30 video generations / 40 image generations daily on the free Flow tier, necessitating conservative test runs and prompt pre-validation.

---

## 6. Recommended Next Steps for Development

1. **Pre-flight Media Verification**:
   - Add automated `ffprobe` stream validation to `flow_client.py` and `pipeline.py` immediately after clip download to detect corrupt or partial files before rendering starts.
2. **Automated Prompt Safety Sanitizer**:
   - Implement an automated prompt sanitizer that replaces flagged vocabulary (e.g., gore, injury terms) with evocative cinematic lighting and suspense alternatives prior to job submission.
3. **Modular Dual-Pass Audio Pipeline**:
   - Separate audio mix into an explicit intermediate step: mix vocal, sidechained BGM, and SFX into a single master WAV, then mux with visual video in one clean step.
4. **CLI Rendering Flag (`--render-mode`)**:
   - Add an explicit `--render-mode` flag (`image_kenburns` vs `generative_video`) to allow users to choose between guaranteed watermark-free output and full generative motion.
