# Contributing to Scenecraft

Thank you for your interest in contributing to Scenecraft! Whether you are fixing a bug, adding an audio preset, or improving documentation, we appreciate your help.

---

## First Contribution

New to the project? Here are great ways to make your first contribution:
1. **Look for `good first issue`:** Check the [issue tracker](https://github.com/Varun1019/Scenecraft/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22) for small, self-contained improvements.
2. **Improve Documentation & Examples:** Clarify setup instructions, write tutorials, or add new sample scripts in `examples/`.
3. **Report Edge Cases:** Run `scenecraft doctor` on your platform and report any missing package managers or hardware quirks.

---

## Development Setup

1. Fork and clone the repository.
2. Create and activate a Python virtual environment (Python 3.10+):
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate       # On Linux / macOS
   # .venv\Scripts\Activate.ps1    # On Windows PowerShell
   ```
3. Install package in editable mode:
   ```bash
   pip install -e ".[dev]"
   ```
4. Verify your local environment:
   ```bash
   scenecraft doctor
   ```

---

## Running Tests

Run the full unit test suite and self-tests before opening a pull request:

```bash
# Run all unit tests
python -m unittest discover tests -v

# Run fast tiny E2E render test
python -m unittest tests/test_e2e_tiny.py -v

# Run doctor preflight checks
scenecraft doctor
```

All CI workflows (Ubuntu, Windows Server, Arch Linux) must pass before merging.

---

## Filing a Good Bug Report

When filing a bug:
1. Run `scenecraft report` in your workspace.
2. Copy the generated Markdown block. It includes your Scenecraft version, OS, FFmpeg status, and recent logs with personal paths and secrets automatically redacted.
3. Open a bug report at [New Issue](https://github.com/Varun1019/Scenecraft/issues/new/choose) and paste the block in the diagnostic field.
4. If you have a question or idea rather than a bug, join [GitHub Discussions](https://github.com/Varun1019/Scenecraft/discussions).

---

## Code Guidelines

- **Portability:** Use `pathlib.Path` everywhere. Never use hardcoded absolute paths (`/home/...`, `C:\...`) or POSIX-only shell utilities (`rm -rf`, `pgrep`, `grep`).
- **Safety & Privacy:** Never commit secrets, cookies, API keys, or personal paths. All reporting commands must scrub private data.
- **Licenses:** Any bundled assets (fonts, audio, presets) must be CC0, MIT, Apache 2.0, or OFL-licensed with entries in `assets/licenses.json` and `THIRD_PARTY_NOTICES.md`.
- **Conventional Commits:** Use standard commit prefixes (`feat:`, `fix:`, `docs:`, `test:`, `chore:`).
