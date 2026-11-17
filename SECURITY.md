# Security Policy

## Reporting Security Issues

We take security and user privacy seriously. If you discover a potential vulnerability in Scenecraft, please disclose it responsibly so we can resolve it before public disclosure.

### How to Report Privately

Please **do not** open a public GitHub issue for security vulnerabilities. Instead:

1. Use GitHub's private vulnerability reporting feature:
   👉 [Submit a Security Advisory](https://github.com/Varun1019/Scenecraft/security/advisories/new)
2. If GitHub advisories are unavailable, contact the project maintainer via the email registered in GitHub author metadata.

Please include:
- A description of the vulnerability and its potential impact.
- Steps to reproduce or a minimal proof-of-concept.
- Affected component(s) (e.g., CLI, extension bridge, asset cleaner, subtitle generator).

You will receive an acknowledgment within 48 hours.

---

## Extension Bridge & Localhost Architecture

Scenecraft includes a local HTTP bridge communicating between the user's browser extension and the local Python pipeline:

- **Loopback Only:** The bridge binds strictly to `127.0.0.1` (`localhost`). It never binds to `0.0.0.0` or listens on external network interfaces.
- **Per-Install Pairing Token:** All control endpoints require a high-entropy random authentication token generated during setup (`bridge_token.json`). Requests without a matching bearer token are rejected.
- **Reporting Extension Bridge Bugs:** Vulnerability reports regarding bridge authentication, CORS bypasses, or potential localhost cross-site request forgery (CSRF) vectors are welcome and prioritized.

---

## Sensitive Data & Automatic Redaction

Scenecraft includes built-in privacy protection:
- `scenecraft report` automatically scrubs user home directories (`~`), local usernames (`<user>`), email addresses, Google Gemini API keys, OpenAI keys, GitHub tokens, and bridge authentication secrets from output.
- Logs are stored locally in the platform log directory (`scenecraft.log`) and are never sent to external servers or telemetry backends.
