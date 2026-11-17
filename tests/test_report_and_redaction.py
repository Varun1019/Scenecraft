"""Unit tests for diagnostic report generation and privacy redaction."""

import os
import tempfile
import unittest
from pathlib import Path

from scenecraft.redactor import redact_sensitive_text
from scenecraft.report import generate_markdown_report
from scenecraft.logger import setup_logging, get_latest_log_lines, get_log_file_path


class TestRedactorAndReport(unittest.TestCase):

    def test_redact_personal_paths(self):
        home = str(Path.home())
        raw = f"Error reading config at {home}/secrets/config.yaml"
        redacted = redact_sensitive_text(raw)
        self.assertNotIn(home, redacted)
        self.assertIn("~/secrets/config.yaml", redacted)

    def test_redact_api_keys_and_tokens(self):
        fake_gemini = "AIzaSyD-fakeGeminiKeyForTesting12345678"
        fake_openai = "sk-1234567890abcdefghijklmnopqrstuvwxyzAB"
        fake_github = "ghp_abcdefghijklmnopqrstuvwxyz123456"
        fake_bridge = "flow_bridge_secret_token_abcdef123"

        text = (
            f"Config dump: gemini={fake_gemini}, openai={fake_openai}, "
            f"github={fake_github}, bridge={fake_bridge}"
        )
        redacted = redact_sensitive_text(text, extra_tokens=[fake_bridge])

        self.assertNotIn(fake_gemini, redacted)
        self.assertNotIn(fake_openai, redacted)
        self.assertNotIn(fake_github, redacted)
        self.assertNotIn(fake_bridge, redacted)
        self.assertIn("[REDACTED_GEMINI_KEY]", redacted)
        self.assertIn("[REDACTED_API_KEY]", redacted)
        self.assertIn("[REDACTED_GITHUB_TOKEN]", redacted)
        self.assertIn("[REDACTED_TOKEN]", redacted)

    def test_redact_email_and_bearer(self):
        raw = "Contact support@example.com with Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.test"
        redacted = redact_sensitive_text(raw)
        self.assertNotIn("support@example.com", redacted)
        self.assertIn("[REDACTED_EMAIL]", redacted)
        self.assertIn("Bearer [REDACTED_TOKEN]", redacted)

    def test_redact_private_key_block(self):
        raw = (
            "-----BEGIN RSA PRIVATE KEY-----\n"
            "MIIEowIBAAKCAQEA0fakePrivateKeyPayload123456\n"
            "-----END RSA PRIVATE KEY-----"
        )
        redacted = redact_sensitive_text(raw)
        self.assertNotIn("fakePrivateKeyPayload", redacted)
        self.assertIn("[REDACTED_PRIVATE_KEY]", redacted)

    def test_generate_markdown_report_structure(self):
        report = generate_markdown_report()
        self.assertIn("### 📋 Scenecraft Diagnostic Report", report)
        self.assertIn("**Scenecraft Version:**", report)
        self.assertIn("**Operating System:**", report)
        self.assertIn("**Python Version:**", report)
        self.assertIn("**FFmpeg Version:**", report)
        self.assertIn("<details>", report)
        # Verify no unredacted user home path appears
        home = str(Path.home())
        if home != "/":
            self.assertNotIn(home, report)

    def test_logger_initialization_and_reading(self):
        logger = setup_logging()
        test_msg = "Diagnostic sanity ping 999"
        logger.info(test_msg)
        lines = get_latest_log_lines(10)
        self.assertTrue(any(test_msg in l for l in lines))


if __name__ == "__main__":
    unittest.main()
