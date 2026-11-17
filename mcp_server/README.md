# Scenecraft MCP Server

Model Context Protocol (MCP) server for Scenecraft. Exposes deterministic video generation tools (`doctor`, `setup`, `visuals`, `clean`, `narrate`, `subtitles`, `assemble`, `validate`) directly to AI coding agents.

---

## Installation

Install Scenecraft and MCP dependencies:

```bash
pip install -e .
pip install mcp
```

---

## Configuration

### Claude Desktop (`claude_desktop_config.json`)

On macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`  
On Windows: `%APPDATA%\Claude\claude_desktop_config.json`  
On Linux: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "scenecraft": {
      "command": "python",
      "args": ["-m", "mcp_server.server"]
    }
  }
}
```

If using a virtual environment, specify the full path to python:

```json
{
  "mcpServers": {
    "scenecraft": {
      "command": "/path/to/venv/bin/python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "/path/to/scenecraft"
    }
  }
}
```

### Antigravity (`~/.gemini/antigravity/mcp_config.json`)

```json
{
  "mcpServers": {
    "scenecraft": {
      "command": "python",
      "args": ["-m", "mcp_server.server"]
    }
  }
}
```

---

## Available MCP Tools

| Tool | Parameters | Description |
|---|---|---|
| `doctor` | None | Runs system diagnostics across GPU, FFmpeg, models, and TTS |
| `setup` | `whisper_model`, `force` | Downloads LaMa ONNX and Faster-Whisper models |
| `visuals` | `project_json`, `output_dir`, `dry_run` | Generates visual scene images via Google Flow |
| `clean` | `input_path`, `output_path`, `corner` | Removes visible watermarks with LaMa ONNX |
| `narrate` | `project_json`, `output_path`, `engine` | Synthesizes voice narration audio |
| `subtitles` | `project_json`, `audio_path`, `output_path` | Generates word-synced ASS subtitles |
| `assemble` | `bundle_path`, `aspect_ratio`, `dry_run` | Assembles final vertical/horizontal MP4 |
| `validate` | `video_path` | Verifies stream decode integrity |
