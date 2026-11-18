"""Model setup and download manager for Scenecraft (`scenecraft setup`).

Downloads LaMa ONNX neural inpainting weights and Whisper speech models with resumable
chunked HTTP downloads, progress indication, and SHA256 integrity verification.
"""

from __future__ import annotations

import hashlib
import os
import sys
import time
import urllib.request
from pathlib import Path
from typing import Optional

from scenecraft.config import get_config

LAMA_ONNX_URL = "https://huggingface.co/Carve/LaMa-ONNX/resolve/main/lama_fp32.onnx"
LAMA_EXPECTED_SIZE = 208577317  # ~198.9 MB

KOKORO_RELEASE_BASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1"
KOKORO_INT8_SIZE = 114119327   # ~108.8 MB
KOKORO_FP32_SIZE = 325505369   # ~310.4 MB
KOKORO_VOICES_SIZE = 28214398  # ~26.9 MB


def download_file_resumable(
    url: str,
    dest_path: Path,
    expected_size: Optional[int] = None,
    expected_sha256: Optional[str] = None,
    chunk_size: int = 1024 * 1024,  # 1 MB chunks
) -> bool:
    """Download a file with HTTP Range resume support and progress output."""
    dest_path = Path(dest_path).resolve()
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    part_path = dest_path.with_suffix(".part")

    existing_bytes = part_path.stat().st_size if part_path.is_file() else 0

    headers = {"User-Agent": "Scenecraft-Setup/0.1.0"}
    if existing_bytes > 0:
        headers["Range"] = f"bytes={existing_bytes}-"
        print(f"[*] Resuming download from byte {existing_bytes:,}...")

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            status = getattr(resp, "status", 200)
            content_length = resp.headers.get("Content-Length")
            total_size = int(content_length) if content_length else expected_size

            if status == 206:  # Partial Content
                mode = "ab"
                downloaded = existing_bytes
                if total_size:
                    total_expected = existing_bytes + total_size
                else:
                    total_expected = expected_size
            else:
                mode = "wb"
                downloaded = 0
                total_expected = total_size or expected_size

            start_t = time.time()
            with open(part_path, mode) as f:
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)

                    el = max(time.time() - start_t, 0.001)
                    speed_mb = (downloaded - existing_bytes) / (1024 * 1024) / el
                    if total_expected:
                        pct = (downloaded / total_expected) * 100.0
                        mb_done = downloaded / (1024 * 1024)
                        mb_total = total_expected / (1024 * 1024)
                        print(
                            f"\r  [Progress] {mb_done:.1f} MB / {mb_total:.1f} MB ({pct:.1f}%) @ {speed_mb:.2f} MB/s",
                            end="",
                            flush=True,
                        )
                    else:
                        mb_done = downloaded / (1024 * 1024)
                        print(f"\r  [Progress] {mb_done:.1f} MB downloaded @ {speed_mb:.2f} MB/s", end="", flush=True)

        print()  # newline
    except Exception as e:
        print(f"\n[!] Download connection interrupted: {e}")
        print("    Run 'scenecraft setup' again to resume.")
        return False

    # Checksum verification if provided
    if expected_sha256:
        print("[*] Verifying file checksum (SHA-256)...")
        hasher = hashlib.sha256()
        with open(part_path, "rb") as f:
            while chunk := f.read(1024 * 1024):
                hasher.update(chunk)
        digest = hasher.hexdigest().lower()
        if digest != expected_sha256.lower():
            print(f"[!] Checksum mismatch: expected {expected_sha256}, got {digest}")
            part_path.unlink()
            return False
        print("[✔] SHA-256 verification passed.")

    # Move .part to final destination
    if dest_path.exists():
        dest_path.unlink()
    part_path.rename(dest_path)
    print(f"[✔] Saved to {dest_path}")
    return True


def run_setup(
    whisper_model: str = "base",
    force: bool = False,
    tts: str = "kokoro",
    models_only: bool = False,
    quantized: bool = True,
) -> int:
    """Download LaMa inpainting model, Whisper speech model, and selected TTS models."""
    cfg = get_config()
    models_dir = cfg.models_dir
    models_dir.mkdir(parents=True, exist_ok=True)

    tts_choice = (tts or "kokoro").lower().strip()

    print("=" * 65)
    print("🛠  SCENECRAFT FIRST-TIME SETUP & MODEL PRE-CACHING")
    print(f"📁 Target Model Directory: {models_dir}")
    print(f"🎙  Selected TTS Engine:    {tts_choice.upper()}")
    print("=" * 65)

    # 1. LaMa Inpainting ONNX Model
    lama_path = models_dir / cfg.cleaner_model_name
    if lama_path.is_file() and not force:
        size_mb = lama_path.stat().st_size / (1024 * 1024)
        print(f"[✔] LaMa ONNX model already installed ({size_mb:.1f} MB): {lama_path.name}")
    else:
        print(f"\n[*] Target File: {lama_path.name}")
        print(f"[*] Size: ~{LAMA_EXPECTED_SIZE / (1024 * 1024):.1f} MB | License: Apache 2.0")
        print("[*] Downloading LaMa neural inpainting model...")
        ok = download_file_resumable(
            url=LAMA_ONNX_URL,
            dest_path=lama_path,
            expected_size=LAMA_EXPECTED_SIZE,
        )
        if not ok:
            print("[!] Failed to complete LaMa model download.")
            return 1

    # 2. Faster-Whisper Speech Recognition Model
    if not models_only:
        print(f"\n[*] Pre-caching faster-whisper model ('{whisper_model}')...")
        try:
            from faster_whisper import WhisperModel
            whisper_dir = models_dir / "whisper"
            whisper_dir.mkdir(parents=True, exist_ok=True)
            _ = WhisperModel(whisper_model, device="cpu", compute_type="int8", download_root=str(whisper_dir))
            print(f"[✔] Faster-Whisper '{whisper_model}' model cached successfully.")
        except Exception as e:
            print(f"[!] Note: faster-whisper cache failed or offline: {e}")
            print("    Faster-Whisper will download automatically on first run if internet is available.")

    # 3. TTS Model Downloads
    if tts_choice in ("kokoro", "kokoro-onnx"):
        kokoro_dir = models_dir / "kokoro"
        kokoro_dir.mkdir(parents=True, exist_ok=True)

        model_filename = "kokoro-v1.0.int8.onnx" if quantized else "kokoro-v1.0.onnx"
        model_size = KOKORO_INT8_SIZE if quantized else KOKORO_FP32_SIZE
        model_url = f"{KOKORO_RELEASE_BASE}/{model_filename}"
        model_dest = kokoro_dir / model_filename

        voices_filename = "voices-v1.0.bin"
        voices_size = KOKORO_VOICES_SIZE
        voices_url = f"{KOKORO_RELEASE_BASE}/{voices_filename}"
        voices_dest = kokoro_dir / voices_filename

        print(f"\n[*] Downloading Kokoro-82M ONNX model ({'quantized int8' if quantized else 'fp32'})...")
        print(f"    Model File: {model_filename} ({model_size / (1024 * 1024):.1f} MB) | License: Apache 2.0")
        print(f"    Voices File: {voices_filename} ({voices_size / (1024 * 1024):.1f} MB)")

        if model_dest.is_file() and not force:
            print(f"[✔] Kokoro ONNX model already installed: {model_dest.name}")
        else:
            ok = download_file_resumable(url=model_url, dest_path=model_dest, expected_size=model_size)
            if not ok:
                print("[!] Failed to download Kokoro ONNX model.")
                return 1

        if voices_dest.is_file() and not force:
            print(f"[✔] Kokoro voices file already installed: {voices_dest.name}")
        else:
            ok = download_file_resumable(url=voices_url, dest_path=voices_dest, expected_size=voices_size)
            if not ok:
                print("[!] Failed to download Kokoro voices file.")
                return 1

        # Check Python package
        from scenecraft.tts.kokoro import KokoroTTS
        k_tts = KokoroTTS()
        if not k_tts.is_package_installed() and not models_only:
            print("\n[*] Note: Python package 'kokoro-onnx' not yet installed.")
            print("    Install it to enable Kokoro synthesis: pip install \"scenecraft[kokoro]\"")

    elif tts_choice == "piper":
        print("\n[*] Piper TTS selected. Piper binaries can be installed via package manager or:")
        print("    https://github.com/rhasspy/piper/releases")
        print("    Download voice onnx + json and point to them in config.yaml.")
    elif tts_choice == "none":
        print("\n[*] Skipping TTS model pre-caching (--tts none).")

    print("\n" + "=" * 65)
    print("🎉 Scenecraft setup complete! Run 'scenecraft doctor' to verify environment.")
    print("=" * 65)
    return 0
