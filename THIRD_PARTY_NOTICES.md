# Third-Party Notices & Licenses

Scenecraft bundles or integrates with several open-source libraries, models, and creative assets.

---

## Bundled Assets

### 1. Noto Sans Font
- **File:** `assets/fonts/NotoSans-Bold.ttf`
- **License:** SIL Open Font License, Version 1.1 (OFL-1.1)
- **Copyright:** (c) 2012 Google Inc.
- **License Text:** See `assets/fonts/LICENSE.txt`

### 2. Audio SFX & Background Music
- **Files:** `assets/*.mp3`
- **License:** Creative Commons Zero v1.0 Universal (CC0 1.0) / Public Domain
- **Attribution & Metadata:** See `assets/licenses.json`

---

## External Dependencies & Models

### 3. LaMa Inpainting ONNX Model
- **Repository:** [advimman/lama](https://github.com/advimman/lama)
- **License:** Apache License 2.0
- **Usage:** Downloaded on demand via `scenecraft setup`. Not committed to git.

### 4. Faster-Whisper
- **Repository:** [SYSTRAN/faster-whisper](https://github.com/SYSTRAN/faster-whisper)
- **License:** MIT License
- **Usage:** Downloaded on demand via `scenecraft setup`. Not committed to git.

### 5. FFmpeg
- **Website:** [ffmpeg.org](https://ffmpeg.org/)
- **License:** LGPL v2.1+ / GPL v2+ (depending on build flags)
- **Usage:** External system binary invoked via subprocess.

### 6. ONNX Runtime
- **Repository:** [microsoft/onnxruntime](https://github.com/microsoft/onnxruntime)
- **License:** MIT License

### 7. Kokoro-82M TTS & kokoro-onnx
- **Model:** [hexgrad/Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M)
- **ONNX Implementation:** [thewh1teagle/kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx)
- **License:** Apache License 2.0
- **Usage:** Downloaded on demand via `scenecraft setup --tts kokoro`. Not committed to git.

### 8. Piper TTS
- **Repository:** [rhasspy/piper](https://github.com/rhasspy/piper)
- **License:** MIT License / Apache License 2.0 (voices)
- **Usage:** Optional local TTS engine. Downloaded on demand via `scenecraft setup --tts piper`. Not committed to git.
