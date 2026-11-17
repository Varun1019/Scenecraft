"""Generate privacy-safe markdown diagnostic reports for bug triage and GitHub issues."""

from __future__ import annotations

import json
import platform
import sys
from pathlib import Path
from typing import List, Optional

from scenecraft import __version__
from scenecraft.config import get_config
from scenecraft.doctor import SystemDoctor, detect_platform_info
from scenecraft.logger import get_latest_log_lines
from scenecraft.redactor import redact_sensitive_text


def _get_bridge_tokens() -> List[str]:
    """Retrieve local bridge tokens for redaction without exposing them."""
    tokens = []
    cfg = get_config()
    token_files = [
        Path.cwd() / "bridge_token.json",
        cfg.cache_dir / "bridge_token.json",
    ]
    for tf in token_files:
        if tf.is_file():
            try:
                data = json.loads(tf.read_text(encoding="utf-8"))
                tok = data.get("token") or data.get("bridge_token")
                if tok and isinstance(tok, str):
                    tokens.append(tok)
            except Exception:
                pass
    return tokens


def generate_markdown_report(workspace_root: Optional[Path] = None, max_log_lines: int = 50) -> str:
    """Generate a sanitized Markdown report block ready to paste into GitHub issues."""
    doc = SystemDoctor(workspace_root)
    checks = {c.name: c for c in doc.run_all_checks()}

    os_info = checks.get("Operating System")
    py_info = checks.get("Python Environment")
    ffmpeg_info = checks.get("FFmpeg Installation")
    nvenc_info = checks.get("NVIDIA Hardware Acceleration")
    tts_info = checks.get("TTS Audio Engine")
    models_info = checks.get("LaMa ONNX Model")
    bridge_info = checks.get("Flow Extension Bridge")
    disk_info = checks.get("Disk Space")

    log_lines = get_latest_log_lines(max_log_lines)
    log_content = "\n".join(log_lines) if log_lines else "(No logs recorded yet)"

    report_lines = [
        "<!-- Copy and paste the block below into your GitHub issue -->",
        "### 📋 Scenecraft Diagnostic Report",
        "",
        f"- **Scenecraft Version:** `v{__version__}`",
        f"- **Operating System:** `{os_info.message if os_info else detect_platform_info()}`",
        f"- **Python Version:** `{py_info.message if py_info else sys.version.split()[0]}`",
        f"- **FFmpeg Version:** `{ffmpeg_info.message if ffmpeg_info else 'Unknown'}`",
        f"- **Encoder / Acceleration:** `{nvenc_info.message if nvenc_info else 'Unknown'}`",
        f"- **TTS Engine:** `{tts_info.message if tts_info else 'Unknown'}`",
        f"- **Models Installed:** `{models_info.message if models_info else 'Unknown'}`",
        f"- **Extension Bridge:** `{bridge_info.message if bridge_info else 'Unknown'}`",
        f"- **Disk Storage:** `{disk_info.message if disk_info else 'Unknown'}`",
        "",
        "<details>",
        f"<summary>Recent Logs (last {len(log_lines)} lines)</summary>",
        "",
        "```text",
        log_content,
        "```",
        "</details>",
    ]

    raw_report = "\n".join(report_lines)
    extra_tokens = _get_bridge_tokens()
    return redact_sensitive_text(raw_report, extra_tokens=extra_tokens)
