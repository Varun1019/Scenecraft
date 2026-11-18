# Scenecraft Troubleshooting Guide

This guide covers common errors encountered when running Scenecraft across Linux, Windows, and macOS, along with immediate fixes.

---

## 1. `ffmpeg` or `ffprobe` Executable Not Found

### Symptoms
- `scenecraft doctor` reports `[✘ FAIL] FFmpeg Installation`
- Error: `FileNotFoundError: [Errno 2] No such file or directory: 'ffmpeg'`

### Fix by OS
- **Windows:**
  Install FFmpeg via winget or Chocolatey:
  ```powershell
  winget install Gyan.FFmpeg
  # or
  choco install ffmpeg
  ```
  Restart your PowerShell terminal so `PATH` updates. Verify with `ffmpeg -version`.
- **Arch Linux / CachyOS / Manjaro:**
  ```bash
  sudo pacman -S ffmpeg
  ```
- **Ubuntu / Debian / Mint:**
  ```bash
  sudo apt update && sudo apt install ffmpeg
  ```
- **Fedora / RHEL:**
  ```bash
  sudo dnf install ffmpeg
  ```
- **macOS:**
  ```bash
  brew install ffmpeg
  ```

---

## 2. NVENC Hardware Acceleration Unavailable

### Symptoms
- `scenecraft doctor` reports `NVENC unavailable or CPU fallback active`
- Video rendering uses CPU instead of GPU

### Cause & Fix
- **Cause:** No NVIDIA GPU present, outdated graphics drivers, or running in a headless VM/cloud container without GPU passthrough.
- **Fix:**
  - This is **non-fatal**. Scenecraft automatically falls back to CPU encoding via `libx264` with optimized presets (`crf: 19`, `preset: fast`).
  - To enable NVENC on NVIDIA systems, update your NVIDIA display driver to version 525+ and verify with `nvidia-smi`.

---

## 3. Subtitles Missing or FFmpeg Filter Error on Windows

### Symptoms
- Video renders, but on-screen ASS subtitles do not appear
- FFmpeg error: `Cannot load font` or syntax error near drive letter (e.g., `C:\...`)

### Cause & Fix
- **Cause:** Windows drive letters (colons `:`) and backslashes `\` require special escaping inside FFmpeg filter graphs (`subtitles='C\:/path/to/sub.ass'`).
- **Fix:**
  - Scenecraft handles drive letter escaping automatically. If you authored a manual filter, ensure paths use forward slashes (`/`) and escaped colons (`C\:/...`).
  - Verify the bundled font (`Montserrat-Black.ttf`) exists in `assets/fonts/Montserrat-Black.ttf`.

---

## 4. Google Flow Browser Extension Not Connecting

### Symptoms
- `scenecraft status` reports `Google Flow: NOT CONNECTED`
- `scenecraft flow-video` or image generation times out

### Fix
1. Open Google Chrome, Brave, or Edge.
2. Navigate to `chrome://extensions`.
3. Enable **Developer mode** (top-right toggle).
4. Click **Load unpacked** and select the `extension/` folder inside your Scenecraft clone (or the unzipped release asset).
5. Open [flow.google.com](https://flow.google.com) in a browser tab and sign in.
6. Verify the Scenecraft bridge icon in your browser toolbar turns active and shows connected on `http://127.0.0.1:8795`.

---

## 5. PEP 668: `error: externally-managed-environment`

### Symptoms
- Running `pip install -e .` on Arch, Debian 12, or Ubuntu 24.04 fails with:
  `error: externally-managed-environment`

### Cause & Fix
- Modern Linux distributions prevent installing packages directly into the system Python environment.
- **Fix:** Always create and activate a virtual environment first:
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -e ".[dev]"
  ```

---

## 6. Slow Model Download or Interrupted Setup

### Symptoms
- `scenecraft setup` downloads slowly or terminates prematurely on weak connections

### Cause & Fix
- `scenecraft setup` uses streaming chunk downloads with hash validation. If interrupted, simply re-run:
  ```bash
  scenecraft setup
  ```
- Alternatively, you can manually place `lama_fp32.onnx` into your Scenecraft models directory:
  - Linux: `~/.local/share/scenecraft/models/lama_fp32.onnx`
  - Windows: `%LOCALAPPDATA%\scenecraft\models\lama_fp32.onnx`
  - macOS: `~/Library/Application Support/scenecraft/models/lama_fp32.onnx`

---

## 7. Windows PowerShell: `Activate.ps1 cannot be loaded because running scripts is disabled`

### Symptoms
- Running `.\.venv\Scripts\Activate.ps1` produces:
  `File ...\Activate.ps1 cannot be loaded because running scripts is disabled on this system.`

### Fix
In PowerShell, change the execution policy for your current user:
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```
Then reactivate your virtual environment:
```powershell
.\.venv\Scripts\Activate.ps1
```

---

## 8. Kokoro-82M TTS: Model Missing or `espeakng-loader` Notice

### Symptoms
- `scenecraft voices` reports `[⚠ MISSING MODELS]` or `[✘ NOT INSTALLED]`
- Error: `kokoro_onnx not found` or `voices-v1.0.bin missing`

### Fix
1. Install the Kokoro ONNX optional package:
   ```bash
   pip install "scenecraft[kokoro]"
   ```
   *(On Windows and Linux, `kokoro-onnx>=0.3.0` bundles precompiled `libespeak-ng` binaries via `espeakng-loader`; you do NOT need to install espeak-ng separately via apt or winget.)*
2. Download model weights (~108 MB quantized int8 + 26 MB voice pack):
   ```bash
   scenecraft setup --tts kokoro
   ```
3. Test audio synthesis:
   ```bash
   scenecraft voices --preview kokoro --voice af_heart
   ```

---

## 9. Windows 260-Character Path Limit (MAX_PATH)

### Symptoms
- Long paths error when downloading Whisper models or pip wheels:
  `FileNotFoundError: [Errno 2] No such file or directory: '...'`

### Fix
Enable Long Paths in the Windows Registry (Administrator PowerShell):
```powershell
Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' -Name 'LongPathsEnabled' -Value 1
```

---

## Still Stuck?

Run `scenecraft report` in your workspace terminal, then paste the sanitized report into:
👉 [New GitHub Issue](https://github.com/Varun1019/Scenecraft/issues/new/choose)
or ask the community in:
👉 [GitHub Discussions](https://github.com/Varun1019/Scenecraft/discussions)
