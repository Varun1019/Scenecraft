"""Privacy-safe redaction utilities for diagnostic reports and logs."""

from __future__ import annotations

import getpass
import os
import re
from pathlib import Path
from typing import List, Optional


EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
)

GEMINI_KEY_PATTERN = re.compile(
    r"\bAIza[0-9A-Za-z\-_]{35}\b"
)

OPENAI_KEY_PATTERN = re.compile(
    r"\b(sk-[A-Za-z0-9_\-]{20,}|sk_[A-Za-z0-9_\-]{20,})\b"
)

GITHUB_TOKEN_PATTERN = re.compile(
    r"\b(ghp|gho|ghu|ghs|ghr|github_pat)_[A-Za-z0-9_]{16,}\b"
)

BEARER_PATTERN = re.compile(
    r"(?i)\bBearer\s+([A-Za-z0-9_\-\.]{12,})"
)

ASSIGNMENT_SECRET_PATTERN = re.compile(
    r"(?i)\b(api_key|apikey|secret|token|password|auth|authorization)\s*[:=]\s*['\"]?([A-Za-z0-9_\-\.]{8,})['\"]?"
)

PRIVATE_KEY_BLOCK_PATTERN = re.compile(
    r"-----BEGIN [A-Z ]+ PRIVATE KEY-----[\s\S]*?-----END [A-Z ]+ PRIVATE KEY-----"
)


def redact_sensitive_text(text: str, extra_tokens: Optional[List[str]] = None) -> str:
    """Redact personal paths, usernames, emails, API keys, and bridge tokens."""
    if not text:
        return text

    # Redact private key blocks
    text = PRIVATE_KEY_BLOCK_PATTERN.sub("[REDACTED_PRIVATE_KEY]", text)

    # Redact home directory paths first (before username redaction)
    try:
        home_path = str(Path.home().resolve())
        if home_path and home_path != "/":
            text = text.replace(home_path, "~")
            # Also handle Windows forward slashes if on Windows
            if "\\" in home_path:
                text = text.replace(home_path.replace("\\", "/"), "~")
    except Exception:
        pass

    # Redact username
    try:
        username = getpass.getuser()
        if username and username.lower() not in ("root", "admin", "runner", "user", "none"):
            # Case-insensitive replacement if longer than 2 characters
            if len(username) > 2:
                text = re.sub(re.escape(username), "<user>", text, flags=re.IGNORECASE)
    except Exception:
        pass

    # Redact extra custom tokens (e.g. extension bridge token, known secrets)
    if extra_tokens:
        for tok in extra_tokens:
            if tok and len(tok) >= 6:
                text = text.replace(tok, "[REDACTED_TOKEN]")

    # Redact common API keys and tokens
    text = GEMINI_KEY_PATTERN.sub("[REDACTED_GEMINI_KEY]", text)
    text = OPENAI_KEY_PATTERN.sub("[REDACTED_API_KEY]", text)
    text = GITHUB_TOKEN_PATTERN.sub("[REDACTED_GITHUB_TOKEN]", text)
    text = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", text)
    text = BEARER_PATTERN.sub(r"Bearer [REDACTED_TOKEN]", text)

    # Redact key/secret assignments
    text = ASSIGNMENT_SECRET_PATTERN.sub(r"\1=[REDACTED_SECRET]", text)

    return text
