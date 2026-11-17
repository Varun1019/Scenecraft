"""Google Flow / Nano Banana automation client with strict error handling and character consistency."""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import List, Dict, Any, Optional

from scenecraft.border_detector import BorderDetector
from scenecraft.visual_intelligence import (
    ImageQualityController,
    ImageValidationResult,
    VideoQualityController,
    VideoValidationResult,
)

DAILY_IMAGE_LIMIT = 40
USAGE_FILE = Path.home() / ".scenecraft" / "usage.json"
SUPPORTED_FLOW_VIDEO_MODELS = ["omni-flash", "veo-3.1-lite", "veo-3.1-fast", "veo-3.1-quality"]
SUPPORTED_FLOW_IMAGE_MODELS = ["nano-banana-pro", "nano-banana-2", "nano-banana-2-lite"]


def compute_image_content_hash(
    prompt: str,
    aspect_ratio: str = "9:16",
    reference_image: Optional[Path] = None,
) -> str:
    """Compute deterministic SHA-256 content fingerprint for prompt, aspect ratio, and reference image."""
    h = hashlib.sha256()
    h.update(prompt.strip().encode("utf-8"))
    h.update(aspect_ratio.strip().encode("utf-8"))
    if reference_image and Path(reference_image).is_file():
        ref_p = Path(reference_image)
        h.update(str(ref_p.stat().st_size).encode("utf-8"))
        try:
            with open(ref_p, "rb") as f:
                h.update(f.read(4096))
        except Exception:
            pass
    return h.hexdigest()[:16]


def reframe_or_punch_in(
    source_image: Path,
    output_path: Path,
    punch_in_scale: float = 1.25,
) -> Path:
    """Intelligently reframe / punch in on an approved image for shot diversity without burning generation quota."""
    from PIL import Image
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source_image) as im:
        w, h = im.size
        crop_w = max(10, int(w / punch_in_scale))
        crop_h = max(10, int(h / punch_in_scale))
        left = (w - crop_w) // 2
        top = (h - crop_h) // 2
        right = left + crop_w
        bottom = top + crop_h
        cropped = im.crop((left, top, right, bottom))
        resized = cropped.resize((w, h), Image.Resampling.LANCZOS)
        resized.save(output_path, quality=95)
    return output_path


class FlowConnectionError(Exception):
    """Raised when Google Flow or Flow Connector is disconnected or fails."""


class FlowQuotaExceededError(Exception):
    """Raised when daily generation allowance is exhausted."""


class FlowClient:
    """Manages interaction with Flow Connector CLI (flow-auto) and enforces quotas."""

    def __init__(self, daily_limit: int = DAILY_IMAGE_LIMIT):
        self.daily_limit = daily_limit
        self.cli_available = shutil.which("flow-auto") is not None
        self.quality_controller = ImageQualityController()
        self.video_quality_controller = VideoQualityController()
        self._init_usage()

    def _init_usage(self):
        USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
        if not USAGE_FILE.is_file():
            self._save_usage({"date": str(datetime.date.today()), "images_generated": 0})

    def _get_usage(self) -> Dict[str, Any]:
        try:
            with open(USAGE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            today = str(datetime.date.today())
            if data.get("date") != today:
                data = {"date": today, "images_generated": 0}
                self._save_usage(data)
            return data
        except Exception:
            return {"date": str(datetime.date.today()), "images_generated": 0}

    def _save_usage(self, data: Dict[str, Any]):
        with open(USAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def get_remaining_quota(self) -> int:
        usage = self._get_usage()
        count = usage.get("images_generated", 0)
        return max(0, self.daily_limit - count)

    def check_connection(self) -> Dict[str, Any]:
        """Check if Flow bridge and extension are running and connected."""
        if not self.cli_available:
            return {
                "connected": False,
                "reason": "flow-auto CLI not installed. Run: npm install -g flow-connector-cli"
            }

        try:
            res = subprocess.run(
                ["flow-auto", "status", "--site", "flow"],
                capture_output=True,
                text=True,
                timeout=8,
            )
            output = res.stdout + res.stderr
            is_connected = "extension (flow): connected" in output.lower()
            plan = "free"
            today = str(datetime.date.today())
            for line in output.splitlines():
                if line.strip().startswith("plan:"):
                    plan = line.strip().split(":", 1)[1].strip()
                    if "pro" in plan.lower() or "unlimited" in plan.lower():
                        self.daily_limit = 500
                    # Sync real usage reported by Google Flow
                    import re
                    m = re.search(r"(\d+)/(\d+)\s+images\s+today", line)
                    if m:
                        actual_used = int(m.group(1))
                        actual_limit = int(m.group(2))
                        self.daily_limit = actual_limit
                        self._save_usage({"date": today, "images_generated": actual_used})
            return {
                "connected": is_connected,
                "plan": plan,
                "raw": output.strip(),
                "remaining_quota": self.get_remaining_quota(),
            }
        except Exception as e:
            return {"connected": False, "reason": str(e)}

    def probe_agent_capabilities(self) -> Dict[str, Any]:
        """Inspect installed Flow Connector and live Flow page capabilities.
        
        Determines whether native Flow Agent mode is supported vs. standard Flow Composer.
        """
        # 1. Check live DOM detection from Flow extension bridge (port 8795)
        dom_snapshot = None
        try:
            req = urllib.request.Request("http://127.0.0.1:8795/api/dom/snapshot", headers={"User-Agent": "Scenecraft"})
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                dom_snapshot = json.loads(resp.read().decode("utf-8"))
        except Exception:
            pass

        # 2. Check flow-auto CLI modes
        cli_modes: List[str] = []
        if self.cli_available:
            try:
                res = subprocess.run(["flow-auto", "modes"], capture_output=True, text=True, timeout=5)
                for line in res.stdout.splitlines():
                    cleaned = line.strip()
                    if cleaned and not cleaned.startswith("note:") and not cleaned.startswith("Usage:"):
                        cli_modes.append(cleaned.split()[0])
            except Exception:
                pass

        # 3. Analyze native Agent vs Composer mode
        agent_found = False
        mode_name = "UNKNOWN"
        composer_detected = False

        if dom_snapshot and isinstance(dom_snapshot, dict):
            detection = dom_snapshot.get("detection", {})
            agent_found = bool(detection.get("agentFound", False))
            mode_name = str(detection.get("modeName", "NONE"))
            composer_detected = bool(detection.get("hasInputElement", False))

        has_cli_agent = any("agent" in m.lower() for m in cli_modes)
        native_agent_supported = agent_found and (mode_name == "FLOW_AGENT_NATIVE") and has_cli_agent

        if native_agent_supported:
            reason = "Google Flow native Agent mode is active and verified on current Flow tab."
            closest_alt = None
        else:
            reason = (
                f"Google Flow native Agent mode is unsupported/inactive on current Flow tab "
                f"(DOM mode: {mode_name}, agentFound: {agent_found}, cli_agent: {has_cli_agent}). "
                f"Flow UI exposes {mode_name or 'FLOW_COMPOSER'}."
            )
            closest_alt = "Sequential scene video generation via Flow Connector with character reference anchoring."

        conn_status = self.check_connection()
        return {
            "native_agent_supported": native_agent_supported,
            "mode_name": mode_name,
            "agent_found": agent_found,
            "composer_detected": composer_detected,
            "has_cli_agent": has_cli_agent,
            "reason": reason,
            "closest_alternative": closest_alt,
            "character_consistency_supported": True,
            "available_cli_modes": cli_modes,
            "connected": conn_status.get("connected", False),
            "remaining_quota": conn_status.get("remaining_quota", 0),
        }

    def generate_image(
        self,
        prompt: str,
        output_path: Path,
        scene_idx: int = 1,
        reference_image: Optional[Path] = None,
        folder_name: str = "scenecraft",
        aspect_ratio: str = "9:16",
        max_retries: int = 2,
        dry_run: bool = False,
    ) -> Path:
        """Generate still image via Google Flow and Nano Banana with quality validation and automatic caching."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if dry_run:
            print(f"  [DRY-RUN] Simulating Flow image generation for Scene {scene_idx} ({aspect_ratio})...")
            w, h = (1920, 1080) if aspect_ratio == "16:9" else (1080, 1920)
            from PIL import Image, ImageDraw
            img = Image.new("RGB", (w, h), color=(26, 26, 30))
            draw = ImageDraw.Draw(img)
            draw.rectangle([20, 20, w - 20, h - 20], outline=(160, 51, 37), width=4)
            img.save(output_path, quality=95)
            return output_path

        # 1. Cache hit verification: never regenerate an image that already exists and passes quality validation
        if output_path.is_file():
            val = self.quality_controller.validate_image(output_path, expected_aspect_ratio=aspect_ratio)
            if val.valid:
                print(f"  [✔] Reusing verified cached image for Scene {scene_idx}: {output_path.name} ({val.width}x{val.height})")
                return output_path

        # 2. Content-hash fingerprint verification across central repository
        content_hash = compute_image_content_hash(prompt, aspect_ratio=aspect_ratio, reference_image=reference_image)
        repo_dir = Path(__file__).resolve().parent.parent / "generated_images"
        hash_cached = repo_dir / f"hash_{content_hash}.jpg"
        if hash_cached.is_file():
            val = self.quality_controller.validate_image(hash_cached, expected_aspect_ratio=aspect_ratio)
            if val.valid:
                shutil.copy2(hash_cached, output_path)
                print(f"  [✔] Content-hash cache hit for Scene {scene_idx} ({content_hash}): {output_path.name}")
                return output_path

        status = self.check_connection()
        remaining = self.get_remaining_quota()

        if not status.get("connected"):
            diag = status.get("raw") or status.get("reason")
            raise FlowConnectionError(
                f"\n[ERROR] Google Flow is NOT connected!\n"
                f"Diagnostic details:\n{diag}\n\n"
                f"HOW TO CONNECT:\n"
                f"1. Open Google Chrome with the Flow Connector extension enabled.\n"
                f"2. Navigate to https://flow.google.com and log in with your Google account.\n"
                f"3. Keep the Flow browser tab open and visible (not minimized).\n"
                f"4. Verify connection by running: flow-auto status --site flow\n"
            )

        if remaining <= 0:
            raise FlowQuotaExceededError(
                f"\n[ERROR] Daily limit reached ({self.daily_limit} images/day).\n"
                f"Per user policy: Never bypass Google limits. Try again after quota reset.\n"
            )

        print(f"[*] Submitting Scene {scene_idx} to Google Flow (Nano Banana)... (Daily quota remaining: {remaining})")

        # Default to official brand identity reference image if none provided
        if reference_image is None:
            default_ref = Path(__file__).resolve().parent.parent / "references" / "brand_identity" / "ref_character_full_body.jpg"
            if default_ref.is_file():
                reference_image = default_ref

        # Use image-to-image with reference character image if provided for visual consistency
        if reference_image and Path(reference_image).is_file():
            cmd = [
                "flow-auto", "generate", "create", "flow-image-to-image",
                "--image", str(Path(reference_image).resolve()),
                "--prompt", prompt,
                "--aspect-ratio", aspect_ratio,
                "--folder", folder_name,
                "--index", str(scene_idx),
                "--wait",
                "--json"
            ]
        else:
            cmd = [
                "flow-auto", "generate", "create", "flow-text-to-image",
                "--prompt", prompt,
                "--aspect-ratio", aspect_ratio,
                "--model", "nano-banana-pro",
                "--folder", folder_name,
                "--index", str(scene_idx),
                "--wait",
                "--json"
            ]

        # Ensure Flow is not paused in a rate-limit cooldown before submitting
        for _ in range(40):
            try:
                chk = subprocess.run(["flow-auto", "status", "--site", "flow"], capture_output=True, text=True, timeout=5)
                out_txt = chk.stdout.lower()
                if "paused" in out_txt and ("continuing automatically" in out_txt or "unusual activity" in out_txt or "cooling down" in out_txt):
                    print("  [*] Flow cooldown active, sleeping 15s...")
                    time.sleep(15)
                else:
                    break
            except Exception:
                break

        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
                if res.returncode != 0:
                    last_error = f"flow-auto failed with code {res.returncode}:\n{res.stderr or res.stdout}"
                    continue

                data = json.loads(res.stdout)
                files = data.get("files", [])
                if not files or not Path(files[0]["path"]).is_file():
                    last_error = f"No downloaded file found in flow-auto response: {res.stdout}"
                    continue

                downloaded_path = Path(files[0]["path"])

                # 1. Clean provider watermark mark if available
                flow_clean_bin = shutil.which("flow-auto")
                if flow_clean_bin:
                    try:
                        clean_temp = output_path.with_suffix(".cleaned.jpg")
                        subprocess.run(
                            ["flow-auto", "clean", str(downloaded_path), "--mark", "flow", "-o", str(clean_temp)],
                            check=True,
                            capture_output=True,
                            timeout=30,
                        )
                        if clean_temp.is_file():
                            shutil.move(clean_temp, output_path)
                        else:
                            shutil.copy2(downloaded_path, output_path)
                    except Exception:
                        shutil.copy2(downloaded_path, output_path)
                else:
                    shutil.copy2(downloaded_path, output_path)

                # 2. Rigorous quality & decodability validation (including border detection and auto-crop)
                val = self.quality_controller.validate_image(output_path, expected_aspect_ratio=aspect_ratio, auto_clean_borders=True)
                if not val.valid:
                    last_error = f"Image quality validation failed on attempt {attempt}: {val.error_message}"
                    print(f"  [!] Scene {scene_idx} failed validation: {val.error_message}")
                    if output_path.exists():
                        output_path.unlink()
                    continue

                # Also save to central generated_images repository and content hash cache
                repo_dir = Path(__file__).resolve().parent.parent / "generated_images"
                repo_dir.mkdir(parents=True, exist_ok=True)
                repo_path = repo_dir / f"scene_{scene_idx:02d}_{output_path.name}"
                shutil.copy2(downloaded_path, repo_path)
                shutil.copy2(output_path, hash_cached)

                # Increment daily quota tracker
                usage = self._get_usage()
                usage["images_generated"] = usage.get("images_generated", 0) + 1
                self._save_usage(usage)

                print(f"  [✔] Scene {scene_idx} verified and saved: {output_path.name} ({val.width}x{val.height})")
                return output_path

            except subprocess.TimeoutExpired:
                last_error = "Generation timed out after 3 minutes. Keep the Flow tab active and foregrounded in Chrome."
            except json.JSONDecodeError as err:
                last_error = f"Failed to parse flow-auto JSON response: {err}\nOutput was: {res.stdout}"

        raise FlowConnectionError(f"Image generation failed after {max_retries} attempt(s): {last_error}")

    def _fetch_video_from_bridge_logs(self, prompt: str, output_path: Path) -> bool:
        """Extract signed video CDN URL from Flow bridge logs and download via curl."""
        try:
            req = urllib.request.urlopen("http://127.0.0.1:8791/logs?site=flow", timeout=4)
            data = json.loads(req.read().decode())
            entries = data.get("entries", [])
        except Exception as e:
            return False

        prompt_snippet = prompt[:40].lower()
        for e in reversed(entries):
            msg = e.get("message", "")
            if "flow-content.google/video" in msg:
                if prompt_snippet in msg.lower() or "as29s" in msg:
                    m = re.search(r'(https://flow-content\.google/video/[^\s\"\'\]]+)', msg)
                    if m:
                        raw_url = m.group(1).rstrip(chr(92))
                        clean_url = raw_url.replace(r"\u003d", "=").replace(r"\u0026", "&").replace(chr(92), "")
                        temp_dl = output_path.with_suffix(".tmp.mp4")
                        res = subprocess.run(["curl", "-s", "-L", clean_url, "-o", str(temp_dl)], timeout=90)
                        if res.returncode == 0 and temp_dl.is_file() and temp_dl.stat().st_size > 5000:
                            val = self.video_quality_controller.validate_video(temp_dl)
                            if val.valid:
                                temp_dl.replace(output_path)
                                return True
                        if temp_dl.exists():
                            temp_dl.unlink()
        return False

    def generate_video(
        self,
        prompt: str,
        output_path: Path,
        start_image: Optional[Path] = None,
        reference_image: Optional[Path] = None,
        character_name: Optional[str] = None,
        duration: int = 6,
        aspect_ratio: str = "16:9",
        model: str = "omni-flash",
        folder_name: str = "scenecraft_video",
        scene_idx: int = 1,
        max_retries: int = 2,
        dry_run: bool = False,
    ) -> Path:
        """Generate animated video clip via Google Flow with strict caching and validation."""
        output_path = Path(output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if dry_run:
            print(f"  [DRY-RUN] Simulating Flow video generation for Scene {scene_idx} ({aspect_ratio}, {duration}s)...")
            w, h = (1920, 1080) if aspect_ratio == "16:9" else (1080, 1920)
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", f"color=c=0x18181A:s={w}x{h}:d={duration}",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-r", "30",
                str(output_path)
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            return output_path

        # 1. Cache hit check: Never regenerate completed video clips
        if output_path.is_file():
            val = self.video_quality_controller.validate_video(output_path, expected_aspect_ratio=aspect_ratio)
            if val.valid:
                print(f"  [✔] Reusing verified cached video clip for Scene {scene_idx}: {output_path.name} ({val.width}x{val.height}, {val.duration:.1f}s)")
                return output_path

        # 2. Verify model availability against official Flow models
        if model not in SUPPORTED_FLOW_VIDEO_MODELS:
            raise FlowConnectionError(
                f"Unsupported Flow video model '{model}'. Supported video models: {SUPPORTED_FLOW_VIDEO_MODELS}"
            )

        # Adjust duration to model specifications
        if "veo" in model:
            duration = 8  # Veo models have fixed 8s duration in Flow
        elif duration not in [4, 6, 8, 10]:
            duration = 6  # Default balanced omni-flash duration

        status = self.check_connection()
        if not status.get("connected"):
            diag = status.get("raw") or status.get("reason")
            raise FlowConnectionError(f"Google Flow not connected: {diag}")

        print(f"[*] Submitting Scene {scene_idx} video generation ({model}, {duration}s, {aspect_ratio})...")

        if start_image and Path(start_image).is_file():
            cmd = [
                "flow-auto", "generate", "create", "flow-frame-to-video",
                "--image", str(Path(start_image).resolve()),
                "--prompt", prompt,
                "--duration", str(duration),
                "--aspect-ratio", aspect_ratio,
                "--resolution", "720p",
                "--model", model,
                "--folder", folder_name,
                "--index", str(scene_idx),
                "--wait",
                "--json"
            ]
        elif reference_image and Path(reference_image).is_file():
            cmd = [
                "flow-auto", "generate", "create", "flow-ingredients-to-video",
                "--image", str(Path(reference_image).resolve()),
                "--prompt", prompt,
                "--duration", str(duration),
                "--aspect-ratio", aspect_ratio,
                "--resolution", "720p",
                "--model", model,
                "--folder", folder_name,
                "--index", str(scene_idx),
                "--wait",
                "--json"
            ]
            if character_name:
                cmd.extend(["--character", character_name])
        else:
            cmd = [
                "flow-auto", "generate", "create", "flow-text-to-video",
                "--prompt", prompt,
                "--duration", str(duration),
                "--aspect-ratio", aspect_ratio,
                "--resolution", "720p",
                "--model", model,
                "--folder", folder_name,
                "--index", str(scene_idx),
                "--wait",
                "--json"
            ]
            if character_name:
                cmd.extend(["--character", character_name])

        last_error = ""
        for attempt in range(1, max_retries + 1):
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=360)
                downloaded_file = None
                if res.returncode == 0:
                    try:
                        data = json.loads(res.stdout)
                        files = data.get("files", [])
                        if files and Path(files[0]["path"]).is_file():
                            downloaded_file = Path(files[0]["path"])
                    except json.JSONDecodeError:
                        pass

                if downloaded_file:
                    shutil.copy2(downloaded_file, output_path)
                    val = self.video_quality_controller.validate_video(output_path, expected_aspect_ratio=aspect_ratio)
                    if val.valid:
                        print(f"  [✔] Scene {scene_idx} video verified: {output_path.name} ({val.width}x{val.height}, {val.duration:.1f}s)")
                        return output_path
                    else:
                        print(f"  [!] Direct downloaded file failed QC: {val.error_message}. Trying signed CDN stream from bridge logs...")
                        if output_path.exists():
                            output_path.unlink()

                # Fallback: check bridge logs for signed CDN MP4 stream
                if self._fetch_video_from_bridge_logs(prompt, output_path):
                    val = self.video_quality_controller.validate_video(output_path, expected_aspect_ratio=aspect_ratio)
                    if val.valid:
                        print(f"  [✔] Scene {scene_idx} video recovered from CDN: {output_path.name} ({val.width}x{val.height}, {val.duration:.1f}s)")
                        return output_path
                    if output_path.exists():
                        output_path.unlink()

                last_error = f"Generation attempt {attempt} failed: {res.stderr or res.stdout}"

            except subprocess.TimeoutExpired:
                if self._fetch_video_from_bridge_logs(prompt, output_path):
                    val = self.video_quality_controller.validate_video(output_path, expected_aspect_ratio=aspect_ratio)
                    if val.valid:
                        print(f"  [✔] Scene {scene_idx} video recovered from CDN after timeout: {output_path.name} ({val.width}x{val.height}, {val.duration:.1f}s)")
                        return output_path
                last_error = "Video generation timed out after 6 minutes."

        raise FlowConnectionError(f"Video generation failed after {max_retries} attempt(s): {last_error}")

    def generate_test_shots(
        self,
        scene_prompts: List[Any],
        output_dir: Path,
        count: int = 3,
    ) -> List[Path]:
        """Generate 2-3 test images before initiating full batch generation."""
        test_dir = output_dir / "test_shots"
        test_dir.mkdir(parents=True, exist_ok=True)
        results: List[Path] = []
        shots_to_test = scene_prompts[:min(count, len(scene_prompts))]
        print(f"\n[*] Generating {len(shots_to_test)} test shot(s) for visual verification...")
        for sp in shots_to_test:
            out_p = test_dir / f"test_scene_{sp.scene_index:02d}.jpg"
            img = self.generate_image(
                prompt=sp.full_prompt(),
                output_path=out_p,
                scene_idx=sp.scene_index,
                reference_image=getattr(sp, "reference_angle_path", None),
                aspect_ratio=sp.aspect_ratio,
            )
            results.append(img)
        return results
