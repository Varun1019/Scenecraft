"""Central Resource Manager and logical 3-worker execution system for Scenecraft.

Protects hardware (Lenovo LOQ with RTX 3050 6GB Laptop GPU) from thrashing,
monitors GPU/VRAM/CPU/RAM, and coordinates logical workers.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable, Tuple


@dataclass
class SystemMetrics:
    cpu_percent: float = 0.0
    ram_used_mb: float = 0.0
    ram_total_mb: float = 0.0
    ram_percent: float = 0.0
    gpu_util_percent: float = 0.0
    vram_used_mb: float = 0.0
    vram_total_mb: float = 0.0
    vram_free_mb: float = 0.0
    gpu_temp_c: float = 0.0
    active_ffmpeg_processes: int = 0
    safe_to_render: bool = True
    throttle_reason: Optional[str] = None


class ResourceManager:
    """Monitors system resources and enforces safe scheduling for RTX 3050 6GB GPU."""

    # Safety limits for Lenovo LOQ RTX 3050 6GB
    MAX_GPU_TEMP_C = 83.0
    MIN_FREE_VRAM_MB = 900.0
    MAX_FFMPEG_CONCURRENT = 2

    def get_metrics(self) -> SystemMetrics:
        """Poll system metrics: CPU, RAM, GPU utilization, VRAM, and temperature."""
        cpu_pct = 0.0
        try:
            # Read 1-minute load average
            load1, _, _ = os.getloadavg()
            cpu_count = os.cpu_count() or 1
            cpu_pct = min(100.0, round((load1 / cpu_count) * 100.0, 1))
        except Exception:
            pass

        ram_used_mb = 0.0
        ram_total_mb = 0.0
        ram_pct = 0.0
        try:
            with open("/proc/meminfo", "r") as f:
                mem = {}
                for line in f:
                    parts = line.split(":")
                    if len(parts) == 2:
                        k = parts[0].strip()
                        v = parts[1].strip().split()[0]
                        mem[k] = float(v) / 1024.0  # MB
                ram_total_mb = mem.get("MemTotal", 16000.0)
                mem_avail = mem.get("MemAvailable", 8000.0)
                ram_used_mb = ram_total_mb - mem_avail
                ram_pct = round((ram_used_mb / ram_total_mb) * 100.0, 1)
        except Exception:
            pass

        gpu_util = 0.0
        vram_used = 0.0
        vram_total = 6144.0  # RTX 3050 6GB baseline
        vram_free = 6144.0
        gpu_temp = 45.0

        if shutil.which("nvidia-smi"):
            try:
                cmd = [
                    "nvidia-smi",
                    "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu",
                    "--format=csv,noheader,nounits",
                ]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
                if res.returncode == 0 and res.stdout.strip():
                    parts = [p.strip() for p in res.stdout.strip().split(",")]
                    if len(parts) >= 4:
                        gpu_util = float(parts[0])
                        vram_used = float(parts[1])
                        vram_total = float(parts[2])
                        vram_free = max(0.0, vram_total - vram_used)
                        gpu_temp = float(parts[3])
            except Exception:
                pass

        # Count active FFmpeg processes cross-platform
        ffmpeg_count = 0
        try:
            import psutil
            for p in psutil.process_iter(['name']):
                try:
                    pname = (p.info.get('name') or '').lower()
                    if 'ffmpeg' in pname:
                        ffmpeg_count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except ImportError:
            try:
                if os.name == 'nt':
                    res = subprocess.run(["tasklist", "/fi", "imagename eq ffmpeg.exe"], capture_output=True, text=True, timeout=2)
                    ffmpeg_count = res.stdout.lower().count("ffmpeg.exe")
                else:
                    res = subprocess.run(["pgrep", "-c", "ffmpeg"], capture_output=True, text=True, timeout=2)
                    if res.returncode == 0 and res.stdout.strip():
                        ffmpeg_count = int(res.stdout.strip())
            except Exception:
                pass

        # Evaluate safety conditions
        safe = True
        throttle_reason = None
        if gpu_temp >= self.MAX_GPU_TEMP_C:
            safe = False
            throttle_reason = f"GPU temperature high ({gpu_temp}°C >= {self.MAX_GPU_TEMP_C}°C). Cooling down."
        elif vram_free < self.MIN_FREE_VRAM_MB:
            safe = False
            throttle_reason = f"Low GPU VRAM ({vram_free:.0f}MB free < {self.MIN_FREE_VRAM_MB:.0f}MB required)."
        elif ffmpeg_count >= self.MAX_FFMPEG_CONCURRENT:
            safe = False
            throttle_reason = f"{ffmpeg_count} active FFmpeg processes already running."

        return SystemMetrics(
            cpu_percent=cpu_pct,
            ram_used_mb=ram_used_mb,
            ram_total_mb=ram_total_mb,
            ram_percent=ram_pct,
            gpu_util_percent=gpu_util,
            vram_used_mb=vram_used,
            vram_total_mb=vram_total,
            vram_free_mb=vram_free,
            gpu_temp_c=gpu_temp,
            active_ffmpeg_processes=ffmpeg_count,
            safe_to_render=safe,
            throttle_reason=throttle_reason,
        )

    def wait_for_render_slot(self, timeout_seconds: int = 45) -> bool:
        """Wait until GPU/system resources are within safe operating limits."""
        start = time.time()
        while time.time() - start < timeout_seconds:
            metrics = self.get_metrics()
            if metrics.safe_to_render:
                return True
            print(f"  [*] Resource throttle active: {metrics.throttle_reason}. Pausing 3s...")
            time.sleep(3)
        return False


# ==============================================================================
# LOGICAL WORKERS
# ==============================================================================

class ImageAssetWorker:
    """Logical Worker 1: Prompt compilation, Flow generation queue, image validation, asset caching."""

    def __init__(self, flow_client=None):
        if flow_client is None:
            from scenecraft.flow_client import FlowClient
            flow_client = FlowClient()
        self.flow_client = flow_client

    def prepare_and_generate(
        self,
        scene_prompts: List[Any],
        output_dir: Path,
        aspect_ratio: str = "9:16",
        test_mode: bool = False,
    ) -> List[Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        results = []
        if test_mode:
            return self.flow_client.generate_test_shots(scene_prompts, output_dir, count=3)

        for sp in scene_prompts:
            out_p = output_dir / f"scene_{sp.scene_index:02d}.jpg"
            img = self.flow_client.generate_image(
                prompt=sp.full_prompt(),
                output_path=out_p,
                scene_idx=sp.scene_index,
                reference_image=getattr(sp, "reference_angle_path", None),
                aspect_ratio=aspect_ratio,
            )
            results.append(img)
        return results


class AudioWorker:
    """Logical Worker 2: VoiceStudio synthesis, audio processing, narration validation, subtitle preparation."""

    def __init__(self):
        from scenecraft.audio_manager import AudioManager
        self.audio_manager = AudioManager()

    def process_narration_and_subtitles(
        self,
        scenes: List[Dict[str, Any]],
        output_dir: Path,
        aspect_ratio: str = "9:16",
    ) -> Tuple[List[Dict[str, Any]], Path, Path]:
        from scenecraft.narration import generate_full_narration
        return generate_full_narration(scenes=scenes, output_dir=output_dir, aspect_ratio=aspect_ratio)


class VideoWorker:
    """Logical Worker 3: FFmpeg rendering, Ken Burns motion, transitions, final composition, encoding."""

    def __init__(self, resource_manager: Optional[ResourceManager] = None):
        from scenecraft.video_engine import VideoEngine
        self.video_engine = VideoEngine()
        self.resource_manager = resource_manager or ResourceManager()

    def render_composition(
        self,
        scenes: List[Dict[str, Any]],
        narration_audio: Path,
        subtitles_ass: Optional[Path],
        output_mp4: Path,
        temp_dir: Path,
        fps: int = 30,
        width: int = 1080,
        height: int = 1920,
        use_nvenc: bool = False,
        quality_preset: str = "master",
    ) -> Path:
        # Enforce safe GPU slot before initiating render
        self.resource_manager.wait_for_render_slot(timeout_seconds=30)
        return self.video_engine.build_full_video(
            scenes=scenes,
            narration_audio=narration_audio,
            subtitles_ass=subtitles_ass,
            output_mp4=output_mp4,
            temp_dir=temp_dir,
            fps=fps,
            width=width,
            height=height,
            use_nvenc=use_nvenc,
            quality_preset=quality_preset,
        )
