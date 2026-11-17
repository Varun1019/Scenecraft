# Scenecraft Flow Connector

Browser extension connecting Google Flow (`flow.google.com`) with the Scenecraft automation pipeline.

---

## Features

- **Side Panel Automation:** Seamless integration with Google Flow inside Chrome, Edge, and Brave.
- **Agent Bridge:** Local bridge server on `127.0.0.1:8795` for automated generation dispatch.
- **Batch Processing:** Sequential queue execution with rate-limit pacing and automatic retry.
- **Asset Download:** Automated capture and naming of generated images and videos.
- **Token Security:** Authenticated local HTTP endpoint rejecting unauthorized external connections.

---

## Installation (Load Unpacked)

The pre-built extension is ready to load directly from the `dist/` directory (no Node/npm build required).

1. Open your browser extension manager:
   - **Chrome / Brave:** Navigate to `chrome://extensions`
   - **Edge:** Navigate to `edge://extensions`
2. Enable **Developer mode** (toggle in top-right corner).
3. Click **Load unpacked**.
4. Select the `extension/dist` folder inside your cloned Scenecraft repository.
5. Navigate to [flow.google.com](https://flow.google.com) and sign in.
6. Click the extension icon in your toolbar to open the Scenecraft Flow side panel.

---

## Local Bridge Security

The bridge server runs strictly on loopback (`127.0.0.1:8795`).

1. A random authentication token is generated on initial run and cached locally in `~/.cache/scenecraft/bridge_token.json` (or OS cache directory).
2. All non-health bridge requests require the token via:
   - Header: `Authorization: Bearer <token>` or `X-Bridge-Token: <token>`
3. Set a custom token via the `SCENECRAFT_BRIDGE_TOKEN` environment variable if desired.
