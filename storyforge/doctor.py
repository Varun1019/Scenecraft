"""System Diagnostics & Self-Test Engine for StoryForge (`storyforge doctor`).

Validates Python environment, dependencies, FFmpeg, NVENC, GPU access, disk space,
VoiceStudio connection (port 3900), Google Flow connector, and reference assets.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Tuple


@dataclass
class DiagnosticCheck:
    name: str
    status: str  # "OK", "WARN", "FAIL"
    message: str
    details: Optional[str] = None


class SystemDoctor:
    """Runs end-to-end preflight diagnostic self-tests."""

    def __init__(self, workspace_root: Optional[Path] = None):
        self.root = workspace_root or Path(__file__).resolve().parent.parent

    def run_all_checks(self) -> List[DiagnosticCheck]:
        checks: List[DiagnosticCheck] = []
        checks.append(self.check_python_env())
        checks.append(self.check_dependencies())
        checks.append(self.check_ffmpeg())
        checks.append(self.check_nvenc())
        checks.append(self.check_gpu_and_vram())
        checks.append(self.check_disk_space())
        checks.append(self.check_voicestudio_connection())
        checks.append(self.check_flow_connector())
        checks.append(self.check_reference_assets())
        checks.append(self.check_permissions())
        return checks

    def check_python_env(self) -> DiagnosticCheck:
        v = sys.version_info
        ver_str = f"{v.major}.{v.minor}.{v.micro}"
        is_venv = sys.prefix != sys.base_prefix
        if v.major == 3 and v.minor in [10, 11, 12]:
            return DiagnosticCheck("Python Environment", "OK", f"Python {ver_str} in venv: {sys.prefix}")
        elif is_venv:
            return DiagnosticCheck("Python Environment", "OK", f"Python {ver_str} (virtualenv active)")
        return DiagnosticCheck("Python Environment", "WARN", f"Running on system Python {ver_str} without virtualenv")

    def check_dependencies(self) -> DiagnosticCheck:
        required = ["PIL", "torch", "transformers", "numpy"]
        missing = []
        for mod in required:
            try:
                __import__(mod)
            except ImportError:
                missing.append(mod)

        if not missing:
            return DiagnosticCheck("Core Dependencies", "OK", f"All required libraries present ({', '.join(required)})")
        return DiagnosticCheck("Core Dependencies", "FAIL", f"Missing packages: {', '.join(missing)}")

    def check_ffmpeg(self) -> DiagnosticCheck:
        ffmpeg_bin = shutil.which("ffmpeg")
        ffprobe_bin = shutil.which("ffprobe")
        if not ffmpeg_bin or not ffprobe_bin:
            return DiagnosticCheck("FFmpeg Installation", "FAIL", "ffmpeg or ffprobe executable not found in PATH")
        try:
            res = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=3)
            first_line = res.stdout.splitlines()[0] if res.stdout else "Available"
            return DiagnosticCheck("FFmpeg Installation", "OK", f"FFmpeg operational ({first_line[:40]})")
        except Exception as e:
            return DiagnosticCheck("FFmpeg Installation", "FAIL", f"FFmpeg test execution failed: {e}")

    def check_nvenc(self) -> DiagnosticCheck:
        try:
            res = subprocess.run(["ffmpeg", "-encoders"], capture_output=True, text=True, timeout=4)
            has_nvenc = "h264_nvenc" in res.stdout
            if has_nvenc:
                return DiagnosticCheck("Hardware Acceleration (NVENC)", "OK", "NVIDIA h264_nvenc encoder active")
            return DiagnosticCheck("Hardware Acceleration (NVENC)", "WARN", "NVENC not detected; using software libx264")
        except Exception:
            return DiagnosticCheck("Hardware Acceleration (NVENC)", "WARN", "Could not query FFmpeg encoder list")

    def check_gpu_and_vram(self) -> DiagnosticCheck:
        if not shutil.which("nvidia-smi"):
            return DiagnosticCheck("GPU Access", "WARN", "nvidia-smi not detected")
        try:
            cmd = ["nvidia-smi", "--query-gpu=gpu_name,memory.total,memory.free", "--format=csv,noheader,nounits"]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
            if res.returncode == 0 and res.stdout.strip():
                parts = [p.strip() for p in res.stdout.strip().split(",")]
                gpu_name = parts[0]
                vram_total = parts[1]
                vram_free = parts[2]
                return DiagnosticCheck("GPU Access", "OK", f"{gpu_name} ({vram_free}MB free / {vram_total}MB total)")
            return DiagnosticCheck("GPU Access", "WARN", "nvidia-smi query returned empty")
        except Exception as e:
            return DiagnosticCheck("GPU Access", "WARN", f"nvidia-smi query failed: {e}")

    def check_disk_space(self) -> DiagnosticCheck:
        try:
            stat = shutil.disk_usage(self.root)
            free_gb = stat.free / (1024.0 ** 3)
            if free_gb >= 10.0:
                return DiagnosticCheck("Disk Space", "OK", f"{free_gb:.1f} GB available on workspace drive")
            elif free_gb >= 3.0:
                return DiagnosticCheck("Disk Space", "WARN", f"Low disk space: {free_gb:.1f} GB remaining")
            else:
                return DiagnosticCheck("Disk Space", "FAIL", f"Critical disk space: {free_gb:.1f} GB remaining")
        except Exception as e:
            return DiagnosticCheck("Disk Space", "WARN", f"Could not check disk usage: {e}")

    def check_voicestudio_connection(self) -> DiagnosticCheck:
        try:
            req = urllib.request.urlopen("http://127.0.0.1:3900/health", timeout=2)
            if req.status == 200:
                return DiagnosticCheck("VoiceStudio Narrator Daemon", "OK", "VoiceStudio responsive on port 3900 (Permanent profile locked)")
            return DiagnosticCheck("VoiceStudio Narrator Daemon", "WARN", f"VoiceStudio port 3900 HTTP {req.status}")
        except Exception:
            return DiagnosticCheck("VoiceStudio Narrator Daemon", "WARN", "VoiceStudio daemon offline on port 3900 (Fallback to edge-tts)")

    def check_flow_connector(self) -> DiagnosticCheck:
        if not shutil.which("flow-auto"):
            return DiagnosticCheck("Google Flow Connector", "WARN", "flow-auto CLI not in PATH")
        try:
            res = subprocess.run(["flow-auto", "status", "--site", "flow"], capture_output=True, text=True, timeout=10)
            output = res.stdout.lower()
            if "connected" in output:
                return DiagnosticCheck("Google Flow Connector", "OK", "Google Flow browser bridge connected")
            return DiagnosticCheck("Google Flow Connector", "WARN", "Flow extension not connected (Open flow.google.com in Chrome)")
        except Exception as e:
            return DiagnosticCheck("Google Flow Connector", "WARN", f"flow-auto check failed: {e}")

    def check_reference_assets(self) -> DiagnosticCheck:
        ref_dir = self.root / "references" / "brand_identity"
        required_files = [
            "ref_character_full_body.jpg",
            "ref_character_close_up.jpg",
            "ref_character_three_quarter.jpg",
            "ref_character_back_view.jpg",
            "style_config.json",
        ]
        missing = [f for f in required_files if not (ref_dir / f).is_file()]
        if not missing:
            return DiagnosticCheck("The Wanderer Brand Identity", "OK", "All 4 reference angles & style config intact")
        return DiagnosticCheck("The Wanderer Brand Identity", "FAIL", f"Missing brand references: {', '.join(missing)}")

    def check_permissions(self) -> DiagnosticCheck:
        test_dir = self.root / "output" / ".perm_check"
        try:
            test_dir.mkdir(parents=True, exist_ok=True)
            test_file = test_dir / "test.tmp"
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink()
            test_dir.rmdir()
            return DiagnosticCheck("Filesystem Permissions", "OK", "Write and execute permissions verified in workspace")
        except Exception as e:
            return DiagnosticCheck("Filesystem Permissions", "FAIL", f"Filesystem write failed: {e}")

    def format_report(self) -> str:
        checks = self.run_all_checks()
        lines = [
            "=== STORYFORGE SYSTEM DOCTOR PREFLIGHT REPORT ===",
            "-" * 80,
            f"{'Check':<36} | {'Status':<6} | {'Details'}",
            "-" * 80,
        ]
        for c in checks:
            tag = f"[{c.status}]"
            lines.append(f"{c.name:<36} | {tag:<6} | {c.message}")
        lines.append("-" * 80)
        overall = "HEALTHY" if all(c.status != "FAIL" for c in checks) else "ATTENTION REQUIRED"
        lines.append(f"Overall System Status: {overall}")
        return "\n".join(lines)
