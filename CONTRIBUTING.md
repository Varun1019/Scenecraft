# Contributing to Scenecraft

Thank you for your interest in contributing to Scenecraft!

---

## Development Setup

1. Fork and clone the repository.
2. Create and activate a Python virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate   # On Windows: .venv\Scripts\Activate.ps1
   ```
3. Install package in editable mode with development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```
4. Verify your setup:
   ```bash
   scenecraft doctor
   ```

---

## Running Tests

Always run unit tests before submitting changes:

```bash
python3 -m unittest discover tests
```

---

## Code Guidelines

- **Portability:** Use `pathlib.Path` for all filesystem operations. Never use hardcoded absolute paths or POSIX-only shell calls (`/tmp`, `/home`, `rm -rf`, `pgrep`, `os.nice`).
- **Determinism:** Steps 3–9 must remain deterministic and reproducible across Windows and Linux.
- **Licenses:** Any bundled assets (fonts, audio, models) must have documented open-source licenses in `assets/licenses.json` or `THIRD_PARTY_NOTICES.md`.
- **Commits:** Write clear Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`).
