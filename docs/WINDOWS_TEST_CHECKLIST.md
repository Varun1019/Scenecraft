# Windows Verification Test Checklist

This checklist guides testing Scenecraft on a fresh Windows 10/11 machine without VoiceStudio, paid API keys, or GPU hardware. Follow these exact steps to verify clone-to-video functionality.

---

## 📋 Pre-Flight Checklist

| # | Check Item | Command / Action | Expected Result | Pass? |
|---|---|---|---|---|
| 1 | **PowerShell Policy** | `Get-ExecutionPolicy` | `RemoteSigned` or `Unrestricted` | [ ] |
| 2 | **Python 3.10+** | `python --version` | `Python 3.10.x` - `3.12.x` | [ ] |
| 3 | **FFmpeg in PATH** | `ffmpeg -version` | Output starts with `ffmpeg version` | [ ] |
| 4 | **Git in PATH** | `git --version` | Output starts with `git version` | [ ] |

If any tool is missing, install via Windows Package Manager (`winget`):
```powershell
winget install Python.Python.3.12
winget install Gyan.FFmpeg
winget install Git.Git
```
*Note: Restart PowerShell after running `winget` so PATH environment variables refresh.*

If script execution is disabled:
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

---

## 🚀 Step 1: Clone & Setup Virtual Environment

Run in PowerShell:
```powershell
git clone https://github.com/Varun1019/Scenecraft.git
cd Scenecraft

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```
- [ ] Editable package installs cleanly without wheel build errors.
- [ ] Command `scenecraft --help` displays all subcommands (`demo`, `init`, `make`, `setup`, `voices`, etc.).

---

## 🩺 Step 2: System Health Self-Test

Run:
```powershell
scenecraft doctor
```
- [ ] Operating System reports `Windows 10` or `Windows 11`.
- [ ] Python Environment reports `[✔ OK]`.
- [ ] FFmpeg Installation reports `[✔ OK]`.
- [ ] Windows System Configuration reports `[✔ OK]`.

---

## 🎬 Step 3: Run 100% Offline Demo (Zero Setup / Zero Network)

Run:
```powershell
scenecraft demo
```
- [ ] Runs all 3 stages without downloading any external files.
- [ ] Output prints: `🎉 DEMO VIDEO CREATION SUCCESSFUL!`
- [ ] Finished video saved to `output\demo\demo_video.mp4`.
- [ ] Open in Windows Media Player: 10-second vertical 9:16 short plays with ambient music, sound effects, pan/zoom motion, and styled subtitles.

---

## 🎙 Step 4: Local Neural TTS with Kokoro (Zero Paid APIs)

Install local offline Kokoro engine and model weights:
```powershell
pip install "scenecraft[kokoro]"
scenecraft setup --tts kokoro
```
- [ ] Model downloads with resumable progress (~108 MB int8 ONNX + 26 MB voice pack).
- [ ] Run voices inspection:
```powershell
scenecraft voices
```
- [ ] Kokoro-82M reports `[✔ READY] (Local ONNX, Apache 2.0 - 100% Offline)`.
- [ ] Synthesize a test audio preview:
```powershell
scenecraft voices --preview kokoro --voice af_heart
```
- [ ] Audio preview generated at `output\previews\preview_kokoro_af_heart.wav`. Play file to confirm clean natural speech.

---

## 📁 Step 5: Project Scaffolding & Custom Images Pipeline

1. Scaffold a fresh project:
```powershell
scenecraft init my_story
```
- [ ] Folder `my_story` created containing `project.json`, `images\`, `scripts\`, and `README.md`.

2. Test dry-run:
```powershell
scenecraft make my_story\project.json --dry-run
```
- [ ] Displays ASCII execution plan without rendering video.

3. Produce video using custom images (offline):
Place any 3 image files into `my_story\images\scene_01.jpg`, `scene_02.jpg`, `scene_03.jpg`, then run:
```powershell
scenecraft make my_story\project.json --images-dir my_story\images
```
- [ ] Ingests custom illustrations without applying watermark cleaning.
- [ ] Synthesizes narration, builds subtitles, and outputs finished MP4 in `output\`.
- [ ] Second run resumes and skips finished steps using `.scenecraft_state.json`.

---

## 🌐 Step 6: Google Flow Extension (Optional Free Generation)

1. Open Google Chrome and navigate to `chrome://extensions`.
2. Toggle **Developer mode** (top right) ON.
3. Click **Load unpacked** and select the `extension\` directory inside `Scenecraft`.
4. Open [flow.google.com](https://flow.google.com) and log in with your Google account.
5. In PowerShell:
```powershell
scenecraft status
```
- [ ] Flow Connector reports `CONNECTED`.

---

## 📋 What to Paste Back

If any step fails, run:
```powershell
scenecraft report
```
Copy and paste the entire Markdown block into a GitHub Issue at:
https://github.com/Varun1019/Scenecraft/issues/new/choose
