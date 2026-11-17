#!/usr/bin/env node

/**
 * Flow Connect 2.0 - Production Bridge Server
 * Runs on 127.0.0.1:8795
 * Unifies REST and Director APIs with State Persistence & Diagnostics
 */

const http = require("http");
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const os = require("os");

const PORT = 8795;
const STATE_FILE = path.join(__dirname, ".bridge_state.json");

function getOrInitBridgeToken() {
  if (process.env.SCENECRAFT_BRIDGE_TOKEN) {
    return process.env.SCENECRAFT_BRIDGE_TOKEN.trim();
  }
  const tokenPaths = [
    path.join(__dirname, ".token.json"),
    path.join(os.homedir(), ".cache", "scenecraft", "bridge_token.json")
  ];
  for (const p of tokenPaths) {
    try {
      if (fs.existsSync(p)) {
        const d = JSON.parse(fs.readFileSync(p, "utf8"));
        if (d && d.token) return d.token.trim();
      }
    } catch (_) {}
  }
  const newToken = crypto.randomBytes(16).toString("hex");
  try {
    fs.writeFileSync(tokenPaths[0], JSON.stringify({ token: newToken }, null, 2), "utf8");
  } catch (_) {}
  return newToken;
}

const BRIDGE_TOKEN = getOrInitBridgeToken();

let lastExtensionPing = 0;
let reloadRequested = false;
let reloadTabRequested = false;
let inspectRequested = false;
let latestDomSnapshot = null;

// Project & Event State
let projectQueue = [];
const activeProjects = new Map(); // id -> projectState
const recordedEvents = [];
const jobQueue = [];
const jobHistory = [];

// Load persisted state if exists
function loadPersistedState() {
  try {
    if (fs.existsSync(STATE_FILE)) {
      const data = JSON.parse(fs.readFileSync(STATE_FILE, "utf8"));
      if (Array.isArray(data.projects)) {
        for (const p of data.projects) {
          activeProjects.set(p.project_id || p.id, p);
        }
      }
      if (Array.isArray(data.events)) {
        recordedEvents.push(...data.events.slice(-100));
      }
      console.log(`[Bridge] Restored ${activeProjects.size} projects from persistence.`);
    }
  } catch (err) {
    console.warn("[Bridge] State load warning:", err.message);
  }
}
loadPersistedState();

let persistTimer = null;
function persistStateDebounced() {
  if (persistTimer) clearTimeout(persistTimer);
  persistTimer = setTimeout(() => {
    try {
      const state = {
        projects: Array.from(activeProjects.values()),
        events: recordedEvents.slice(-200)
      };
      fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2), "utf8");
    } catch (err) {
      console.warn("[Bridge] State save warning:", err.message);
    }
  }, 1000);
}

function isExtensionConnected() {
  return Date.now() - lastExtensionPing < 15000;
}

function setCors(res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
}

function sendJson(res, statusCode, data) {
  res.writeHead(statusCode, { "Content-Type": "application/json" });
  res.end(JSON.stringify(data));
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let body = "";
    req.on("data", (chunk) => (body += chunk));
    req.on("end", () => {
      try {
        resolve(JSON.parse(body || "{}"));
      } catch (e) {
        reject(e);
      }
    });
    req.on("error", reject);
  });
}

function normalizeProjectPayload(data) {
  const projectId = data.project_id || data.projectId || `proj_${Date.now()}`;
  const projectTitle = data.project_title || data.title || data.projectTitle || "Project";
  const fullScript = data.full_script || data.fullScript || data.brief || "";

  const scenes = Array.isArray(data.scenes)
    ? data.scenes.map((s, idx) => ({
        scene_number: s.scene_number || s.sceneNumber || idx + 1,
        scene_title: s.scene_title || s.title || s.sceneTitle || `Scene ${idx + 1}`,
        image_prompt: s.image_prompt || s.imagePrompt || "",
        video_prompt: s.video_prompt || s.videoPrompt || "",
        status: s.status || "pending"
      }))
    : [];

  return {
    project_id: projectId,
    project_title: projectTitle,
    full_script: fullScript,
    scenes
  };
}

const server = http.createServer(async (req, res) => {
  setCors(res);

  if (req.method === "OPTIONS") {
    res.writeHead(204);
    res.end();
    return;
  }

  const url = new URL(req.url, `http://${req.headers.host}`);

  // Token authentication check (reject invalid or missing tokens, allow /health for doctor probe)
  const authHeader = req.headers["authorization"] || req.headers["x-bridge-token"] || "";
  const clientToken = authHeader.replace(/^Bearer\s+/i, "").trim();
  if (url.pathname !== "/health" && clientToken !== BRIDGE_TOKEN) {
    return sendJson(res, 401, { error: "Unauthorized: Invalid or missing bridge token" });
  }

  // 1. Health & Bridge Status
  if (req.method === "GET" && (url.pathname === "/health" || url.pathname === "/api/status")) {
    const latestEvents = recordedEvents.slice(-15);
    return sendJson(res, 200, {
      status: "ok",
      port: PORT,
      extensionConnected: isExtensionConnected(),
      pendingProjects: projectQueue.length,
      activeProjectsCount: activeProjects.size,
      recentEvents: latestEvents,
      timestamp: Date.now()
    });
  }

  // 2. Extension Heartbeat
  if (req.method === "POST" && url.pathname === "/api/heartbeat") {
    lastExtensionPing = Date.now();
    return sendJson(res, 200, { ok: true, connected: true });
  }

  // 3. Antigravity submits a complete Project (Primary v2.0 Workflow)
  if (req.method === "POST" && url.pathname === "/api/project/submit") {
    try {
      const raw = await readBody(req);
      const project = normalizeProjectPayload(raw);

      if (!project.project_id || project.scenes.length === 0) {
        return sendJson(res, 400, {
          error: "Validation failed: payload must contain project_id and non-empty scenes array"
        });
      }

      const projectState = {
        ...project,
        status: "queued",
        submittedAt: Date.now(),
        events: [],
        downloads: []
      };

      activeProjects.set(project.project_id, projectState);
      projectQueue.push(project);

      // Also queue legacy job format
      const fullScriptText =
        project.full_script ||
        project.scenes
          .map((s) => `[SCENE ${s.scene_number}: ${s.scene_title}]\n${s.image_prompt || s.video_prompt}`)
          .join("\n\n");

      jobQueue.push({
        id: project.project_id,
        prompt: fullScriptText,
        resolvedPrompt: fullScriptText,
        aspectRatio: "16:9",
        project_title: project.project_title,
        scenes: project.scenes
      });

      persistStateDebounced();
      console.log(
        `[Bridge] Project queued: ${project.project_id} - "${project.project_title}" (${project.scenes.length} scenes)`
      );

      return sendJson(res, 200, {
        ok: true,
        project_id: project.project_id,
        status: "queued"
      });
    } catch (err) {
      return sendJson(res, 400, { error: `Invalid JSON: ${err.message}` });
    }
  }

  // 4. Query Project Status
  if (req.method === "GET" && url.pathname === "/api/project/status") {
    const projectId = url.searchParams.get("id");
    if (!projectId) {
      return sendJson(res, 400, { error: "Missing project id parameter" });
    }

    const state = activeProjects.get(projectId);
    if (!state) {
      return sendJson(res, 404, { error: `Project ${projectId} not found` });
    }

    return sendJson(res, 200, { project: state });
  }

  // 5. Query Project Manifest
  if (req.method === "GET" && url.pathname === "/api/project/manifest") {
    const projectId = url.searchParams.get("id");
    const state = activeProjects.get(projectId);
    if (!state) {
      return sendJson(res, 404, { error: `Project ${projectId} not found` });
    }

    return sendJson(res, 200, {
      projectId: state.project_id,
      projectTitle: state.project_title,
      status: state.status,
      totalScenes: state.scenes ? state.scenes.length : 0,
      completedScenes: state.downloads ? state.downloads.length : 0,
      scenes: state.scenes,
      downloads: state.downloads,
      events: state.events
    });
  }

  // 6. Extension polls for next project
  if (req.method === "GET" && url.pathname === "/api/agent/next") {
    lastExtensionPing = Date.now();

    if (reloadRequested) {
      reloadRequested = false;
      return sendJson(res, 200, { action: "reload" });
    }

    if (reloadTabRequested) {
      reloadTabRequested = false;
      return sendJson(res, 200, { action: "reload_flow_tab" });
    }

    if (inspectRequested) {
      inspectRequested = false;
      return sendJson(res, 200, { action: "inspect_dom" });
    }

    if (projectQueue.length > 0) {
      const nextProj = projectQueue.shift();
      const st = activeProjects.get(nextProj.project_id);
      if (st) st.status = "dispatched_to_extension";

      recordedEvents.push({
        event: "SCRIPT_RECEIVED",
        timestamp: Date.now(),
        project_id: nextProj.project_id,
        project_title: nextProj.project_title,
        scene_count: nextProj.scenes.length
      });
      persistStateDebounced();

      return sendJson(res, 200, { project: nextProj });
    }

    return sendJson(res, 200, { project: null });
  }

  // 7. Extension reports status events
  if (req.method === "POST" && url.pathname === "/api/agent/event") {
    try {
      const ev = await readBody(req);
      lastExtensionPing = Date.now();
      recordedEvents.push(ev);

      console.log(`[Bridge Event] ${ev.event} | Project: ${ev.project_id || "N/A"}`);

      if (ev.project_id && activeProjects.has(ev.project_id)) {
        const st = activeProjects.get(ev.project_id);
        st.events = st.events || [];
        st.downloads = st.downloads || [];
        st.events.push(ev);

        if (ev.event === "DOWNLOAD_COMPLETED" && ev.filename) {
          st.downloads.push({
            scene: ev.scene_number,
            title: ev.scene_title,
            filename: ev.filename,
            timestamp: ev.timestamp
          });
        }

        if (ev.event === "JOB_COMPLETED") {
          st.status = "completed";
          st.completedAt = Date.now();
        } else if (ev.event === "JOB_FAILED" || ev.event.includes("FAIL")) {
          st.status = "failed";
          st.error = ev.error;
        } else {
          st.status = ev.event;
        }
      }

      persistStateDebounced();
      return sendJson(res, 200, { ok: true });
    } catch (err) {
      return sendJson(res, 400, { error: err.message });
    }
  }

  // 8. Director API Endpoints (MCP Support)
  if (req.method === "POST" && url.pathname === "/api/director/project/create") {
    try {
      const data = await readBody(req);
      const projectId = "proj_" + Date.now() + "_" + Math.random().toString(36).slice(2, 6);
      const project = {
        project_id: projectId,
        project_title: data.title || "Untitled Project",
        full_script: data.brief || "",
        scenes: [],
        status: "draft",
        createdAt: Date.now(),
        updatedAt: Date.now()
      };
      activeProjects.set(projectId, project);
      persistStateDebounced();
      return sendJson(res, 200, { success: true, projectId, project });
    } catch (err) {
      return sendJson(res, 400, { error: err.message });
    }
  }

  if (req.method === "POST" && url.pathname === "/api/director/storyboard/create") {
    try {
      const data = await readBody(req);
      const proj = activeProjects.get(data.projectId);
      if (!proj) return sendJson(res, 404, { error: "Project not found" });

      const scenes = (data.scenes || []).map((s, idx) => ({
        scene_number: s.sceneNumber || idx + 1,
        scene_title: s.title || `Scene ${idx + 1}`,
        image_prompt: s.imagePrompt || "",
        video_prompt: s.videoPrompt || "",
        status: "pending"
      }));

      proj.scenes = scenes;
      proj.status = "queued";
      proj.updatedAt = Date.now();

      // Automatically queue to extension
      projectQueue.push(proj);
      persistStateDebounced();

      return sendJson(res, 200, { success: true, projectId: data.projectId, scenesCount: scenes.length });
    } catch (err) {
      return sendJson(res, 400, { error: err.message });
    }
  }

  if (req.method === "POST" && url.pathname === "/api/director/scene/flow-agent") {
    try {
      const data = await readBody(req);
      const singleProj = {
        project_id: data.projectId || "proj_" + Date.now(),
        project_title: "Flow Agent Scene",
        full_script: data.instructions || "",
        scenes: [
          {
            scene_number: 1,
            scene_title: "Flow Agent Scene",
            image_prompt: data.instructions || ""
          }
        ]
      };
      projectQueue.push(singleProj);
      return sendJson(res, 200, { success: true, message: "Scene queued for Flow Agent submission" });
    } catch (err) {
      return sendJson(res, 400, { error: err.message });
    }
  }

  // 9. View Recorded Events
  if (req.method === "GET" && url.pathname === "/api/events") {
    const limit = parseInt(url.searchParams.get("limit") || "50", 10);
    return sendJson(res, 200, { events: recordedEvents.slice(-limit) });
  }

  // 10. Extension Reload
  if (req.method === "POST" && url.pathname === "/api/extension/reload") {
    reloadRequested = true;
    return sendJson(res, 200, { ok: true, message: "Extension will reload on next heartbeat" });
  }

  // 10a. Target Tab Reload
  if (req.method === "POST" && url.pathname === "/api/tab/reload") {
    reloadTabRequested = true;
    return sendJson(res, 200, { ok: true, message: "Flow tab will reload on next heartbeat" });
  }

  // 10b. DOM Inspection Endpoints
  if (req.method === "POST" && url.pathname === "/api/dom/inspect") {
    inspectRequested = true;
    return sendJson(res, 200, { ok: true, message: "DOM inspection requested" });
  }

  if (req.method === "POST" && url.pathname === "/api/dom/snapshot") {
    try {
      latestDomSnapshot = await readBody(req);
      return sendJson(res, 200, { ok: true });
    } catch (e) {
      return sendJson(res, 400, { error: e.message });
    }
  }

  if (req.method === "GET" && url.pathname === "/api/dom/snapshot") {
    return sendJson(res, 200, latestDomSnapshot || { pending: true });
  }

  // 11. Legacy generate fallback
  if (req.method === "POST" && url.pathname === "/api/generate") {
    try {
      const data = await readBody(req);
      const jobId = "job_" + Date.now();
      const singleProj = {
        project_id: jobId,
        project_title: "Quick Generation",
        full_script: data.prompt,
        scenes: [
          {
            scene_number: 1,
            scene_title: "Image",
            image_prompt: data.prompt
          }
        ]
      };
      projectQueue.push(singleProj);
      return sendJson(res, 200, { ok: true, jobId, status: "queued" });
    } catch (err) {
      return sendJson(res, 400, { error: err.message });
    }
  }

  // 404
  sendJson(res, 404, { error: "Not found", path: url.pathname });
});

server.listen(PORT, "127.0.0.1", () => {
  console.log(`[Flow Bridge 2.0] Running on http://127.0.0.1:${PORT}`);
});
