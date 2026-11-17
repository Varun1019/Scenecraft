#!/usr/bin/env node

/**
 * Lightweight local bridge server for Flow Chrome Extension and Antigravity MCP.
 * Runs on 127.0.0.1:8792 with zero external dependencies.
 */

const http = require("http");

const PORT = 8795;
let lastExtensionPing = 0;
const jobQueue = [];
const jobHistory = [];
const waitingResponses = new Map(); // jobId -> res
const waitingExtensionPolls = []; // Array of res

function isExtensionConnected() {
  return Date.now() - lastExtensionPing < 15000;
}

function setCors(res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
}

const server = http.createServer((req, res) => {
  setCors(res);

  if (req.method === "OPTIONS") {
    res.writeHead(204);
    res.end();
    return;
  }

  const url = new URL(req.url, `http://${req.headers.host}`);

  // Health / Status
  if (req.method === "GET" && (url.pathname === "/health" || url.pathname === "/api/status")) {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(
      JSON.stringify({
        status: "ok",
        port: PORT,
        extensionConnected: isExtensionConnected(),
        queueLength: jobQueue.length,
        historyCount: jobHistory.length,
        timestamp: Date.now()
      })
    );
    return;
  }

  // History
  if (req.method === "GET" && url.pathname === "/api/history") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ history: jobHistory }));
    return;
  }

  // Projects list
  if (req.method === "GET" && url.pathname === "/api/projects") {
    const list = global.directorState ? Array.from(global.directorState.projects.values()) : [];
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ projects: list }));
    return;
  }

  // Extension Heartbeat
  if (req.method === "POST" && url.pathname === "/api/heartbeat") {
    lastExtensionPing = Date.now();
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ ok: true }));
    return;
  }

  // Extension Poll for next job
  if (req.method === "GET" && url.pathname === "/api/jobs/next") {
    lastExtensionPing = Date.now();

    if (jobQueue.length > 0) {
      const job = jobQueue.shift();
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ job }));
    } else {
      // Long poll for 25s
      const timer = setTimeout(() => {
        const idx = waitingExtensionPolls.indexOf(res);
        if (idx !== -1) waitingExtensionPolls.splice(idx, 1);
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ job: null }));
      }, 25000);

      res.on("close", () => {
        clearTimeout(timer);
        const idx = waitingExtensionPolls.indexOf(res);
        if (idx !== -1) waitingExtensionPolls.splice(idx, 1);
      });

      waitingExtensionPolls.push(res);
    }
    return;
  }

  // Extension reports job completed
  if (req.method === "POST" && url.pathname === "/api/jobs/complete") {
    let body = "";
    req.on("data", (chunk) => (body += chunk));
    req.on("end", () => {
      lastExtensionPing = Date.now();
      try {
        const data = JSON.parse(body || "{}");
        const { id, success, filename, url: mediaUrl, error } = data;

        if (waitingResponses.has(id)) {
          const clientRes = waitingResponses.get(id);
          waitingResponses.delete(id);

          clientRes.writeHead(200, { "Content-Type": "application/json" });
          clientRes.end(
            JSON.stringify({
              success: !!success,
              filename: filename || null,
              url: mediaUrl || null,
              error: error || null
            })
          );
        }

        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ ok: true }));
      } catch (err) {
        res.writeHead(400, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ error: String(err) }));
      }
    });
    return;
  }

  // Antigravity / Client requests new generation job
  if (req.method === "POST" && url.pathname === "/api/generate") {
    let body = "";
    req.on("data", (chunk) => (body += chunk));
    req.on("end", () => {
      try {
        const data = JSON.parse(body || "{}");
        if (!data.prompt) {
          res.writeHead(400, { "Content-Type": "application/json" });
          res.end(JSON.stringify({ error: "Missing 'prompt' parameter" }));
          return;
        }

        const jobId = "job_" + Date.now() + "_" + Math.random().toString(36).slice(2, 7);
        const job = {
          id: jobId,
          prompt: data.prompt,
          aspectRatio: data.aspectRatio || "16:9",
          createdAt: Date.now()
        };
        jobHistory.unshift({ id: jobId, prompt: data.prompt, aspectRatio: data.aspectRatio || "16:9", status: "pending", createdAt: Date.now() });

        // Timeout after 180s
        const timeoutTimer = setTimeout(() => {
          if (waitingResponses.has(jobId)) {
            waitingResponses.delete(jobId);
            res.writeHead(504, { "Content-Type": "application/json" });
            res.end(JSON.stringify({ error: "Generation timed out waiting for extension" }));
          }
        }, 180000);

        waitingResponses.set(jobId, res);
        res.on("close", () => {
          clearTimeout(timeoutTimer);
          waitingResponses.delete(jobId);
        });

        // Dispatch immediately if an extension poll is waiting
        if (waitingExtensionPolls.length > 0) {
          const pollRes = waitingExtensionPolls.shift();
          pollRes.writeHead(200, { "Content-Type": "application/json" });
          pollRes.end(JSON.stringify({ job }));
        } else {
          jobQueue.push(job);
        }
      } catch (err) {
        res.writeHead(400, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ error: String(err) }));
      }
    });
    return;
  }

  // =====================================================
  // VIDEO DIRECTOR ENDPOINTS
  // =====================================================

  // In-memory store for director projects and scenes (persisted via chrome storage through extension)
  // Bridge acts as a relay — the extension's IndexedDB is the source of truth
  // Bridge keeps a lightweight cache for fast status polling
  if (!global.directorState) {
    global.directorState = {
      projects: new Map(),   // projectId -> ProjectState
      scenes: new Map(),     // sceneId -> SceneState
      pendingOps: [],        // operations waiting for extension
      waitingStatusPolls: new Map() // sceneId/projectId -> [res]
    };
  }

  function readBody(req) {
    return new Promise((resolve, reject) => {
      let body = "";
      req.on("data", (chunk) => (body += chunk));
      req.on("end", () => {
        try { resolve(JSON.parse(body || "{}")); }
        catch (e) { reject(e); }
      });
      req.on("error", reject);
    });
  }

  function directorResponse(res, data, status = 200) {
    res.writeHead(status, { "Content-Type": "application/json" });
    res.end(JSON.stringify(data));
  }

  function enqueueDirectorOp(op) {
    global.directorState.pendingOps.push(op);
    // Wake any waiting extension polls
    if (waitingExtensionPolls.length > 0) {
      const pollRes = waitingExtensionPolls.shift();
      pollRes.writeHead(200, { "Content-Type": "application/json" });
      pollRes.end(JSON.stringify({ job: null, directorOp: op }));
    }
  }

  // POST /api/director/project/create
  if (req.method === "POST" && url.pathname === "/api/director/project/create") {
    readBody(req).then((data) => {
      const projectId = "proj_" + Date.now() + "_" + Math.random().toString(36).slice(2, 6);
      const project = {
        id: projectId,
        title: data.title || "Untitled Project",
        brief: data.brief || "",
        mode: data.mode || "auto",
        autonomousMode: data.autonomousMode || false,
        status: "draft",
        sceneIds: [],
        totalScenes: 0,
        completedScenes: 0,
        failedScenes: 0,
        createdAt: Date.now(),
        updatedAt: Date.now()
      };
      global.directorState.projects.set(projectId, project);
      enqueueDirectorOp({ type: "create_project", project });
      directorResponse(res, { success: true, projectId, project });
    }).catch((e) => directorResponse(res, { error: String(e) }, 400));
    return;
  }

  // POST /api/director/project/update
  if (req.method === "POST" && url.pathname === "/api/director/project/update") {
    readBody(req).then((data) => {
      const proj = global.directorState.projects.get(data.projectId);
      if (!proj) return directorResponse(res, { error: "Project not found" }, 404);
      Object.assign(proj, data.fields || {}, { updatedAt: Date.now() });
      enqueueDirectorOp({ type: "update_project", projectId: data.projectId, fields: data.fields });
      directorResponse(res, { success: true, project: proj });
    }).catch((e) => directorResponse(res, { error: String(e) }, 400));
    return;
  }

  // GET /api/director/project/:id/status
  if (req.method === "GET" && url.pathname.startsWith("/api/director/project/") && url.pathname.endsWith("/status")) {
    const parts = url.pathname.split("/");
    const projectId = parts[4];
    const proj = global.directorState.projects.get(projectId);
    if (!proj) return directorResponse(res, { error: "Project not found" }, 404);
    const scenes = Array.from(global.directorState.scenes.values()).filter(s => s.projectId === projectId);
    directorResponse(res, { project: proj, scenes });
    return;
  }

  // POST /api/director/storyboard/create
  if (req.method === "POST" && url.pathname === "/api/director/storyboard/create") {
    readBody(req).then((data) => {
      const proj = global.directorState.projects.get(data.projectId);
      if (!proj) return directorResponse(res, { error: "Project not found" }, 404);
      
      const sceneIds = [];
      for (const sceneData of (data.scenes || [])) {
        const sceneId = "scene_" + data.projectId + "_" + String(sceneData.sceneNumber).padStart(3, "0");
        const scene = {
          id: sceneId,
          projectId: data.projectId,
          sceneNumber: sceneData.sceneNumber,
          title: sceneData.title || `Scene ${sceneData.sceneNumber}`,
          narrativePurpose: sceneData.narrativePurpose || "",
          description: sceneData.description || "",
          durationSeconds: sceneData.durationSeconds || 8,
          imagePrompt: sceneData.imagePrompt || "",
          videoPrompt: sceneData.videoPrompt || "",
          characterRefs: sceneData.characterRefs || [],
          environmentRefs: sceneData.environmentRefs || [],
          cameraInstructions: sceneData.cameraInstructions || "",
          motionInstructions: sceneData.motionInstructions || "",
          aspectRatio: sceneData.aspectRatio || "16:9",
          model: sceneData.model || "nano-banana-pro",
          dependsOn: sceneData.dependsOn || [],
          status: "pending",
          retryCount: 0,
          maxRetries: 3,
          createdAt: Date.now(),
          updatedAt: Date.now()
        };
        global.directorState.scenes.set(sceneId, scene);
        sceneIds.push(sceneId);
      }
      proj.sceneIds = sceneIds;
      proj.totalScenes = sceneIds.length;
      proj.updatedAt = Date.now();
      enqueueDirectorOp({ type: "create_storyboard", projectId: data.projectId, scenes: Array.from(global.directorState.scenes.values()).filter(s => s.projectId === data.projectId) });
      directorResponse(res, { success: true, projectId: data.projectId, sceneIds });
    }).catch((e) => directorResponse(res, { error: String(e) }, 400));
    return;
  }

  // POST /api/director/scene/create
  if (req.method === "POST" && url.pathname === "/api/director/scene/create") {
    readBody(req).then((data) => {
      const proj = global.directorState.projects.get(data.projectId);
      if (!proj) return directorResponse(res, { error: "Project not found" }, 404);
      const sceneId = "scene_" + data.projectId + "_" + String(data.sceneNumber || Date.now()).padStart(3, "0");
      const scene = { id: sceneId, projectId: data.projectId, status: "pending", retryCount: 0, maxRetries: 3, createdAt: Date.now(), updatedAt: Date.now(), ...data };
      global.directorState.scenes.set(sceneId, scene);
      proj.sceneIds.push(sceneId);
      proj.totalScenes = proj.sceneIds.length;
      enqueueDirectorOp({ type: "create_scene", scene });
      directorResponse(res, { success: true, sceneId, scene });
    }).catch((e) => directorResponse(res, { error: String(e) }, 400));
    return;
  }

  // POST /api/director/scene/update
  if (req.method === "POST" && url.pathname === "/api/director/scene/update") {
    readBody(req).then((data) => {
      const scene = global.directorState.scenes.get(data.sceneId);
      if (!scene) return directorResponse(res, { error: "Scene not found" }, 404);
      Object.assign(scene, data.fields || {}, { updatedAt: Date.now() });
      enqueueDirectorOp({ type: "update_scene", sceneId: data.sceneId, fields: data.fields });
      directorResponse(res, { success: true, scene });
    }).catch((e) => directorResponse(res, { error: String(e) }, 400));
    return;
  }

  // POST /api/director/scene/generate-image
  if (req.method === "POST" && url.pathname === "/api/director/scene/generate-image") {
    readBody(req).then((data) => {
      const scene = global.directorState.scenes.get(data.sceneId);
      if (!scene) return directorResponse(res, { error: "Scene not found" }, 404);
      
      const jobId = "job_" + Date.now() + "_" + Math.random().toString(36).slice(2, 7);
      scene.imageJobId = jobId;
      scene.status = "generating_image";
      scene.updatedAt = Date.now();

      const job = {
        id: jobId,
        prompt: scene.imagePrompt,
        aspectRatio: scene.aspectRatio || "16:9",
        model: scene.model,
        createdAt: Date.now(),
        sceneId: scene.id,
        projectId: scene.projectId,
        jobType: "scene_image"
      };

      // Set up response waiter
      const timeoutTimer = setTimeout(() => {
        if (waitingResponses.has(jobId)) {
          waitingResponses.delete(jobId);
          scene.status = "failed";
          scene.error = "Image generation timed out";
          res.writeHead(504, { "Content-Type": "application/json" });
          res.end(JSON.stringify({ error: "Generation timed out" }));
        }
      }, 300000); // 5 min

      waitingResponses.set(jobId, res);
      res.on("close", () => {
        clearTimeout(timeoutTimer);
        waitingResponses.delete(jobId);
      });

      if (waitingExtensionPolls.length > 0) {
        const pollRes = waitingExtensionPolls.shift();
        pollRes.writeHead(200, { "Content-Type": "application/json" });
        pollRes.end(JSON.stringify({ job }));
      } else {
        jobQueue.push(job);
      }
    }).catch((e) => directorResponse(res, { error: String(e) }, 400));
    return;
  }

  // POST /api/director/scene/generate-video
  if (req.method === "POST" && url.pathname === "/api/director/scene/generate-video") {
    readBody(req).then((data) => {
      const scene = global.directorState.scenes.get(data.sceneId);
      if (!scene) return directorResponse(res, { error: "Scene not found" }, 404);

      const jobId = "job_" + Date.now() + "_" + Math.random().toString(36).slice(2, 7);
      scene.videoJobId = jobId;
      scene.status = "generating_video";
      scene.updatedAt = Date.now();

      const job = {
        id: jobId,
        prompt: scene.videoPrompt,
        aspectRatio: scene.aspectRatio || "16:9",
        model: data.videoModel || "veo-3.1-quality",
        duration: scene.durationSeconds || 8,
        referenceImagePath: scene.imageLocalPath,
        createdAt: Date.now(),
        sceneId: scene.id,
        projectId: scene.projectId,
        jobType: "scene_video"
      };

      const timeoutTimer = setTimeout(() => {
        if (waitingResponses.has(jobId)) {
          waitingResponses.delete(jobId);
          scene.status = "failed";
          scene.error = "Video generation timed out";
          res.writeHead(504, { "Content-Type": "application/json" });
          res.end(JSON.stringify({ error: "Generation timed out" }));
        }
      }, 600000); // 10 min

      waitingResponses.set(jobId, res);
      res.on("close", () => {
        clearTimeout(timeoutTimer);
        waitingResponses.delete(jobId);
      });

      if (waitingExtensionPolls.length > 0) {
        const pollRes = waitingExtensionPolls.shift();
        pollRes.writeHead(200, { "Content-Type": "application/json" });
        pollRes.end(JSON.stringify({ job }));
      } else {
        jobQueue.push(job);
      }
    }).catch((e) => directorResponse(res, { error: String(e) }, 400));
    return;
  }

  // POST /api/director/scene/flow-agent
  if (req.method === "POST" && url.pathname === "/api/director/scene/flow-agent") {
    readBody(req).then((data) => {
      const scene = global.directorState.scenes.get(data.sceneId);
      if (!scene) return directorResponse(res, { error: "Scene not found" }, 404);
      scene.status = "generating_image";
      scene.updatedAt = Date.now();
      enqueueDirectorOp({ type: "flow_agent_scene", sceneId: data.sceneId, scene, instructions: data.instructions });
      directorResponse(res, { success: true, message: "Flow Agent operation queued", sceneId: data.sceneId });
    }).catch((e) => directorResponse(res, { error: String(e) }, 400));
    return;
  }

  // GET /api/director/scene/:id/status
  if (req.method === "GET" && url.pathname.startsWith("/api/director/scene/") && url.pathname.endsWith("/status")) {
    const sceneId = url.pathname.split("/")[4];
    const scene = global.directorState.scenes.get(sceneId);
    if (!scene) return directorResponse(res, { error: "Scene not found" }, 404);
    directorResponse(res, { scene });
    return;
  }

  // POST /api/director/scene/approve
  if (req.method === "POST" && url.pathname === "/api/director/scene/approve") {
    readBody(req).then((data) => {
      const scene = global.directorState.scenes.get(data.sceneId);
      if (!scene) return directorResponse(res, { error: "Scene not found" }, 404);
      scene.status = "approved";
      scene.updatedAt = Date.now();
      enqueueDirectorOp({ type: "approve_scene", sceneId: data.sceneId });
      directorResponse(res, { success: true, scene });
    }).catch((e) => directorResponse(res, { error: String(e) }, 400));
    return;
  }

  // POST /api/director/scene/regenerate
  if (req.method === "POST" && url.pathname === "/api/director/scene/regenerate") {
    readBody(req).then((data) => {
      const scene = global.directorState.scenes.get(data.sceneId);
      if (!scene) return directorResponse(res, { error: "Scene not found" }, 404);
      if (data.type === "video") {
        scene.status = "pending";
        scene.videoJobId = undefined;
        scene.videoLocalPath = undefined;
      } else {
        scene.status = "pending";
        scene.imageJobId = undefined;
        scene.imageLocalPath = undefined;
        scene.videoJobId = undefined;
        scene.videoLocalPath = undefined;
      }
      scene.retryCount = (scene.retryCount || 0) + 1;
      scene.error = undefined;
      scene.updatedAt = Date.now();
      enqueueDirectorOp({ type: "regenerate_scene", sceneId: data.sceneId, regenerateType: data.type || "full" });
      directorResponse(res, { success: true, scene });
    }).catch((e) => directorResponse(res, { error: String(e) }, 400));
    return;
  }

  // POST /api/director/scene/download
  if (req.method === "POST" && url.pathname === "/api/director/scene/download") {
    readBody(req).then((data) => {
      const scene = global.directorState.scenes.get(data.sceneId);
      if (!scene) return directorResponse(res, { error: "Scene not found" }, 404);
      enqueueDirectorOp({ type: "download_scene", sceneId: data.sceneId, scene });
      directorResponse(res, { success: true, message: "Download queued", sceneId: data.sceneId });
    }).catch((e) => directorResponse(res, { error: String(e) }, 400));
    return;
  }

  // GET /api/director/project/:id/dependencies
  if (req.method === "GET" && url.pathname.startsWith("/api/director/project/") && url.pathname.endsWith("/dependencies")) {
    const projectId = url.pathname.split("/")[4];
    const scenes = Array.from(global.directorState.scenes.values()).filter(s => s.projectId === projectId);
    const nodes = scenes.map(s => ({ id: s.id, sceneNumber: s.sceneNumber, title: s.title, status: s.status }));
    const edges = scenes.flatMap(s => s.dependsOn.map(dep => ({ from: dep, to: s.id })));
    directorResponse(res, { nodes, edges, sceneCount: scenes.length });
    return;
  }

  // POST /api/director/project/export
  if (req.method === "POST" && url.pathname === "/api/director/project/export") {
    readBody(req).then((data) => {
      const proj = global.directorState.projects.get(data.projectId);
      if (!proj) return directorResponse(res, { error: "Project not found" }, 404);
      const scenes = Array.from(global.directorState.scenes.values())
        .filter(s => s.projectId === data.projectId)
        .sort((a, b) => a.sceneNumber - b.sceneNumber);
      
      const report = {
        projectId: proj.id,
        projectTitle: proj.title,
        exportedAt: Date.now(),
        brief: proj.brief,
        status: proj.status,
        totalScenes: proj.totalScenes,
        completedScenes: proj.completedScenes,
        failedScenes: proj.failedScenes,
        scenes: scenes.map(s => ({
          sceneNumber: s.sceneNumber,
          title: s.title,
          status: s.status,
          imageLocalPath: s.imageLocalPath,
          videoLocalPath: s.videoLocalPath,
          qcPassed: s.qcPassed,
          error: s.error
        }))
      };
      enqueueDirectorOp({ type: "export_project", projectId: data.projectId, report });
      directorResponse(res, { success: true, report });
    }).catch((e) => directorResponse(res, { error: String(e) }, 400));
    return;
  }

  // POST /api/director/project/assemble
  if (req.method === "POST" && url.pathname === "/api/director/project/assemble") {
    readBody(req).then((data) => {
      const proj = global.directorState.projects.get(data.projectId);
      if (!proj) return directorResponse(res, { error: "Project not found" }, 404);
      
      // Check ffmpeg availability then spawn
      const { exec, spawn: spawnChild } = require("child_process");
      exec("which ffmpeg", (err, stdout) => {
        if (err || !stdout.trim()) {
          return directorResponse(res, { error: "ffmpeg not found. Install ffmpeg to use video assembly." }, 503);
        }
        
        const scenes = Array.from(global.directorState.scenes.values())
          .filter(s => s.projectId === data.projectId && s.status === "completed" || s.status === "approved")
          .sort((a, b) => a.sceneNumber - b.sceneNumber);
        
        if (scenes.length === 0) {
          return directorResponse(res, { error: "No completed scenes to assemble" }, 400);
        }
        
        // Build ffmpeg concat list
        const os = require("os");
        const path = require("path");
        const fs = require("fs");
        const downloadsDir = path.join(os.homedir(), "Downloads");
        const projectDir = path.join(downloadsDir, proj.downloadFolder || "GoogleFlow/Projects/" + proj.title.replace(/\s+/g, "_"));
        const concatFile = path.join(os.tmpdir(), "flow_concat_" + data.projectId + ".txt");
        const outputDir = path.join(projectDir, "04_Final_Sequence");
        const outputFile = path.join(outputDir, data.outputFilename || "final_movie.mp4");
        
        try {
          fs.mkdirSync(outputDir, { recursive: true });
          const concatLines = scenes
            .filter(s => s.videoLocalPath)
            .map(s => `file '${path.join(downloadsDir, s.videoLocalPath)}'`)
            .join("\n");
          fs.writeFileSync(concatFile, concatLines);
        } catch (fsErr) {
          return directorResponse(res, { error: "Failed to prepare assembly: " + fsErr.message }, 500);
        }
        
        const opts = data.options || {};
        const fps = opts.fps || 24;
        const resolution = opts.resolution || "1920x1080";
        
        const args = ["-y", "-f", "concat", "-safe", "0", "-i", concatFile];
        if (opts.musicPath) args.push("-i", opts.musicPath);
        args.push("-vf", `scale=${resolution.replace("x", ":")}:force_original_aspect_ratio=decrease,pad=${resolution.replace("x", ":")}:(ow-iw)/2:(oh-ih)/2,setsar=1`);
        args.push("-r", String(fps));
        if (opts.musicPath) args.push("-shortest");
        args.push("-c:v", "libx264", "-c:a", "aac", outputFile);
        
        const ffmpegProc = spawnChild("ffmpeg", args, { stdio: ["ignore", "pipe", "pipe"] });
        let stderr = "";
        ffmpegProc.stderr.on("data", (d) => (stderr += d));
        
        ffmpegProc.on("close", (code) => {
          if (code === 0) {
            directorResponse(res, { success: true, outputFile: outputFile, message: "Assembly complete" });
          } else {
            directorResponse(res, { error: "FFmpeg failed", stderr: stderr.slice(-2000) }, 500);
          }
        });
      });
    }).catch((e) => directorResponse(res, { error: String(e) }, 400));
    return;
  }

  // POST /api/director/job/complete (extension reports a director scene job done)
  if (req.method === "POST" && url.pathname === "/api/director/job/complete") {
    readBody(req).then((data) => {
      const { jobId, sceneId, jobType, success, filename, url: mediaUrl, fileSize, error } = data;
      const scene = global.directorState.scenes.get(sceneId);
      if (scene) {
        if (success) {
          if (jobType === "scene_image") {
            scene.imageLocalPath = filename;
            scene.status = "generating_video";
          } else if (jobType === "scene_video") {
            scene.videoLocalPath = filename;
            scene.status = "completed";
            const proj = global.directorState.projects.get(scene.projectId);
            if (proj) { proj.completedScenes = (proj.completedScenes || 0) + 1; proj.updatedAt = Date.now(); }
          }
        } else {
          scene.status = "failed";
          scene.error = error || "Unknown error";
          const proj = global.directorState.projects.get(scene.projectId);
          if (proj) { proj.failedScenes = (proj.failedScenes || 0) + 1; proj.updatedAt = Date.now(); }
        }
        scene.updatedAt = Date.now();
      }
      
      // Also resolve the waiting response
      if (waitingResponses.has(jobId)) {
        const waitRes = waitingResponses.get(jobId);
        waitingResponses.delete(jobId);
        waitRes.writeHead(200, { "Content-Type": "application/json" });
        waitRes.end(JSON.stringify({ success: !!success, filename, url: mediaUrl, fileSize, error }));
      }
      
      directorResponse(res, { ok: true });
    }).catch((e) => directorResponse(res, { error: String(e) }, 400));
    return;
  }

  // GET /api/director/ops/next (extension polls for director ops)
  if (req.method === "GET" && url.pathname === "/api/director/ops/next") {
    const op = global.directorState.pendingOps.shift();
    directorResponse(res, { op: op || null });
    return;
  }

  res.writeHead(404, { "Content-Type": "application/json" });
  res.end(JSON.stringify({ error: "Not found" }));
});

server.listen(PORT, "127.0.0.1", () => {
  console.log(`[Flow Bridge] Running on http://127.0.0.1:${PORT}`);
});
