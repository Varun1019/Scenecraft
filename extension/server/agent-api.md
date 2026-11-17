# Flow Studio Pro — Agent Integration & MCP API Reference

## 1. Overview

Flow Studio Pro provides a secure, loopback-only companion service (`127.0.0.1:8792`) allowing compatible AI coding agents (Antigravity, Claude Code, Cursor, Windsurf) to automate image and video generation directly within your authenticated Google Flow browser session.

## 2. Model Context Protocol (MCP) Tools

Flow Studio Pro provides an MCP server running on stdio:
```bash
node server/mcp-server.cjs
```

### Configured in `~/.gemini/config/mcp_config.json`:
```json
{
  "mcpServers": {
    "flow-studio-pro": {
      "command": "node",
      "args": ["./extension/server/mcp-server.cjs"]
    }
  }
}
```

### Available Tools:

| Tool Name | Arguments | Description |
|---|---|---|
| `flow_status` | None | Returns bridge and extension connection health. |
| `flow_generate_image` | `prompt` (string, required), `aspect_ratio` ("16:9", "1:1", "9:16"), `model` (string) | Submits text-to-image prompt to Flow, waits for generation, downloads file. |
| `flow_generate_video` | `prompt` (string, required), `duration` (4 or 8), `aspect_ratio` ("16:9", "9:16"), `model` (string) | Submits text-to-video prompt, waits for completion, downloads video. |
| `flow_submit_batch` | `prompts` (array of strings, required), `aspect_ratio` (string) | Queues multiple prompts for sequential processing. |
| `flow_get_job` | `job_id` (string, required) | Retrieves status, media URL, and saved file path for a specific job. |
| `flow_get_history` | None | Retrieves list of recently generated assets and completed files. |
| `flow_list_projects` | None | Returns project and session diagnostic info. |

---

## 3. Localhost REST API

Base URL: `http://127.0.0.1:8792`

### Endpoints

#### `GET /health` / `GET /api/status`
Returns bridge health, queue size, and extension heartbeat.
```json
{
  "status": "ok",
  "port": 8792,
  "extensionConnected": true,
  "queueLength": 0,
  "historyCount": 12,
  "timestamp": 1794297120000
}
```

#### `POST /api/generate`
Submits single generation job and holds connection until media is downloaded or timeout occurs (up to 180s).
**Request:**
```json
{
  "prompt": "Cyberpunk city street in the rain with glowing neon signs",
  "aspectRatio": "16:9",
  "type": "text-to-image",
  "model": "nano-banana-pro"
}
```
**Response:**
```json
{
  "success": true,
  "id": "job_1794297120000_a8f9",
  "filename": "GoogleFlow/Cyberpunk_city_street_1794297120.png",
  "url": "https://flow-content.google/image/...",
  "error": null
}
```

#### `POST /api/batch`
Queues a batch of prompts.
**Request:**
```json
{
  "prompts": [
    "A majestic lion in the savannah at sunset",
    "A cozy wooden cabin during a snowy winter night"
  ],
  "defaultAspectRatio": "16:9",
  "defaultType": "text-to-image"
}
```
**Response:**
```json
{
  "success": true,
  "count": 2,
  "jobIds": ["job_123", "job_124"]
}
```

#### `GET /api/jobs/:id`
Retrieves job status, filename, and errors.

#### `GET /api/history`
Returns the 50 most recent jobs and their download status.
