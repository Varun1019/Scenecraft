/**
 * Flow Connect 2.0 - Production Background Service Worker
 * Manifest V3 - Smart Scene Tracking, Auto-Recovery, Verified Downloads,
 * Event-Driven Performance, and Error Diagnostics.
 */

import { SceneTracker, TrackedProject } from "../shared/scene-tracker";

const BRIDGE_URL = "http://127.0.0.1:8795";

let sceneTracker: SceneTracker | null = null;
let isBridgeConnected = false;
let isProjectSubmitted = false;
let cachedFlowTabId: number | null = null;
const downloadedMediaUrls = new Set<string>();

interface InFlightDownload {
  sceneNumber: number;
  filename: string;
  mediaUrl: string;
  retries: number;
}
const inFlightDownloads = new Map<number, InFlightDownload>();

// 1. Setup Side Panel Behavior
if (chrome.sidePanel && chrome.sidePanel.setPanelBehavior) {
  chrome.sidePanel
    .setPanelBehavior({ openPanelOnActionClick: true })
    .catch((err) => console.warn("[ServiceWorker] Side panel setup:", err));
}

// 2. Tab Discovery & Caching with Event Listeners
async function getFlowTabId(): Promise<number | null> {
  if (cachedFlowTabId) {
    try {
      const tab = await chrome.tabs.get(cachedFlowTabId);
      if (tab?.url && (tab.url.includes("flow.google.com") || tab.url.includes("labs.google"))) {
        return cachedFlowTabId;
      }
    } catch (_) {
      cachedFlowTabId = null;
    }
  }

  try {
    const tabs = await chrome.tabs.query({});
    const flowTab = tabs.find(
      (t) => t.url && (t.url.includes("flow.google.com") || t.url.includes("labs.google"))
    );
    cachedFlowTabId = flowTab?.id || null;
    return cachedFlowTabId;
  } catch (err) {
    console.warn("[ServiceWorker] locateFlowTab error:", err);
    return null;
  }
}

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (tab.url && (tab.url.includes("flow.google.com") || tab.url.includes("labs.google"))) {
    cachedFlowTabId = tabId;
  }
});

chrome.tabs.onRemoved.addListener((tabId) => {
  if (cachedFlowTabId === tabId) {
    cachedFlowTabId = null;
  }
});

// 3. Reliable Tab Messaging with Automatic Content Script Injection Fallback
async function sendToFlowTab(tabId: number, msg: any): Promise<any> {
  return new Promise((resolve) => {
    chrome.tabs.sendMessage(tabId, msg, async (response) => {
      const err = chrome.runtime.lastError;
      if (err && err.message?.includes("Could not establish connection")) {
        try {
          await chrome.scripting.executeScript({
            target: { tabId },
            files: ["dist/content.js"]
          });
          await new Promise((r) => setTimeout(r, 600));
          chrome.tabs.sendMessage(tabId, msg, (retryRes) => {
            resolve(retryRes || { success: !chrome.runtime.lastError, error: chrome.runtime.lastError?.message });
          });
        } catch (injectErr: any) {
          resolve({ success: false, error: "Content script injection failed: " + injectErr.message });
        }
      } else {
        resolve(response || { success: !err, error: err?.message });
      }
    });
  });
}

// 4. Status Event Dispatcher
async function emitStatusEvent(event: string, details: Record<string, any> = {}) {
  const p = sceneTracker?.getProject();
  const payload = {
    event,
    timestamp: Date.now(),
    project_id: p?.projectId,
    ...details
  };

  console.log(`[Flow Director Event] ${event}:`, details);

  // Broadcast to Sidepanel
  chrome.runtime.sendMessage({ action: "director_event", payload }).catch(() => {});

  // Post to Bridge
  try {
    await fetch(`${BRIDGE_URL}/api/agent/event`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
  } catch (_) {}
}

// 5. State Persistence & Auto-Recovery
async function persistState() {
  if (!sceneTracker) return;
  const p = sceneTracker.getProject();
  try {
    await chrome.storage.local.set({
      flow_active_project: p,
      flow_downloaded_urls: Array.from(downloadedMediaUrls),
      flow_submission_state: {
        projectId: p.projectId,
        isSubmitted: isProjectSubmitted
      }
    });
  } catch (err) {
    console.warn("[ServiceWorker] Failed to persist state:", err);
  }
}

async function restoreState() {
  try {
    const data = await chrome.storage.local.get([
      "flow_active_project",
      "flow_downloaded_urls",
      "flow_submission_state"
    ]);

    if (Array.isArray(data.flow_downloaded_urls)) {
      data.flow_downloaded_urls.forEach((u: string) => downloadedMediaUrls.add(u));
    }

    if (data.flow_active_project) {
      sceneTracker = new SceneTracker(data.flow_active_project);
      if (data.flow_submission_state?.projectId === data.flow_active_project.projectId) {
        isProjectSubmitted = Boolean(data.flow_submission_state.isSubmitted);
      }
      console.log(`[ServiceWorker] Restored project state: ${data.flow_active_project.projectId}`);

      // If project was mid-production, ensure DOM monitoring is awake
      if (data.flow_active_project.status === "processing") {
        const tabId = await getFlowTabId();
        if (tabId) {
          sendToFlowTab(tabId, { action: "start_monitoring" }).catch(() => {});
        }
      }
    }
  } catch (err) {
    console.warn("[ServiceWorker] State restoration error:", err);
  }
}

// 6. Trusted Click & Input via Chrome Debugger
async function submitTrusted(
  tabId: number,
  opts: {
    btnX?: number;
    btnY?: number;
    editorX?: number;
    editorY?: number;
    scriptText?: string;
  }
): Promise<{ success: boolean; error?: string }> {
  const target = { tabId };
  try {
    await chrome.debugger.attach(target, "1.3");
  } catch (e: any) {
    if (!e.message?.includes("already attached")) {
      console.warn("[Debugger] attach failed:", e);
      return { success: false, error: e.message };
    }
  }

  try {
    // 1. Focus editor and insert text if scriptText provided
    if (opts.scriptText) {
      if (typeof opts.editorX === "number" && typeof opts.editorY === "number") {
        await chrome.debugger.sendCommand(target, "Input.dispatchMouseEvent", {
          type: "mousePressed",
          x: opts.editorX,
          y: opts.editorY,
          button: "left",
          clickCount: 1
        });
        await new Promise((r) => setTimeout(r, 60));
        await chrome.debugger.sendCommand(target, "Input.dispatchMouseEvent", {
          type: "mouseReleased",
          x: opts.editorX,
          y: opts.editorY,
          button: "left",
          clickCount: 1
        });
        await new Promise((r) => setTimeout(r, 100));
      }

      await chrome.debugger.sendCommand(target, "Input.insertText", {
        text: opts.scriptText
      });
      await new Promise((r) => setTimeout(r, 150));
    }

    // 2. Click Generate button with trusted dispatch
    if (typeof opts.btnX === "number" && typeof opts.btnY === "number") {
      await chrome.debugger.sendCommand(target, "Input.dispatchMouseEvent", {
        type: "mouseMoved",
        x: opts.btnX,
        y: opts.btnY,
        button: "none"
      });
      await new Promise((r) => setTimeout(r, 80));

      await chrome.debugger.sendCommand(target, "Input.dispatchMouseEvent", {
        type: "mousePressed",
        x: opts.btnX,
        y: opts.btnY,
        button: "left",
        clickCount: 1
      });
      await new Promise((r) => setTimeout(r, 80));

      await chrome.debugger.sendCommand(target, "Input.dispatchMouseEvent", {
        type: "mouseReleased",
        x: opts.btnX,
        y: opts.btnY,
        button: "left",
        clickCount: 1
      });
      await new Promise((r) => setTimeout(r, 100));
    }

    // 3. Dispatch Enter key
    await chrome.debugger.sendCommand(target, "Input.dispatchKeyEvent", {
      type: "rawKeyDown",
      key: "Enter",
      code: "Enter",
      windowsVirtualKeyCode: 13,
      text: "\r",
      unmodifiedText: "\r"
    });
    await new Promise((r) => setTimeout(r, 60));
    await chrome.debugger.sendCommand(target, "Input.dispatchKeyEvent", {
      type: "keyUp",
      key: "Enter",
      code: "Enter",
      windowsVirtualKeyCode: 13
    });

    await new Promise((r) => setTimeout(r, 200));
    return { success: true };
  } catch (err: any) {
    console.warn("[Debugger] submitTrusted failed:", err);
    return { success: false, error: err.message };
  } finally {
    try {
      await chrome.debugger.detach(target);
    } catch (_) {}
  }
}

async function clickTrusted(tabId: number, x: number, y: number): Promise<boolean> {
  const res = await submitTrusted(tabId, { btnX: x, btnY: y });
  return res.success;
}

// 7. Project Execution Pipeline
async function executeProject(projectPayload: any) {
  if (!projectPayload || (!projectPayload.project_id && !projectPayload.projectId)) {
    await emitStatusEvent("JOB_FAILED", {
      stage: "PAYLOAD_VALIDATION",
      error: "Invalid project payload format: project_id required"
    });
    return;
  }

  // Prevent duplicate submissions of an already active or completed project
  if (sceneTracker) {
    const existing = sceneTracker.getProject();
    const incomingId = projectPayload.project_id || projectPayload.projectId;
    if (existing.projectId === incomingId && existing.status === "processing" && isProjectSubmitted) {
      console.log(`[ServiceWorker] Project ${incomingId} already actively processing; ignoring duplicate trigger.`);
      return;
    }
  }

  sceneTracker = new SceneTracker(projectPayload);
  isProjectSubmitted = false;
  await persistState();

  const p = sceneTracker.getProject();
  await emitStatusEvent("SCRIPT_RECEIVED", {
    project_id: p.projectId,
    project_title: p.projectTitle,
    scene_count: p.scenes.length
  });

  // Stage: Flow Tab Discovery
  const tabId = await getFlowTabId();
  if (!tabId) {
    await emitStatusEvent("FLOW_TAB_UNAVAILABLE", {
      error: "Google Flow tab not found. Please ensure flow.google.com is open."
    });
    p.status = "failed";
    await persistState();
    return;
  }

  await emitStatusEvent("FLOW_TAB_FOUND", { tabId });

  // Ensure network interceptor is injected into main world
  try {
    await chrome.scripting.executeScript({
      target: { tabId },
      world: "MAIN",
      files: ["dist/injected.js"]
    });
  } catch (_) {}

  // Stage: Tab Ping & Readiness Check
  const pingRes = await sendToFlowTab(tabId, { action: "ping" });
  if (!pingRes || !pingRes.pong) {
    await emitStatusEvent("FLOW_TAB_UNAVAILABLE", {
      error: "Flow tab content script not responding: " + (pingRes?.error || "connection timed out")
    });
    p.status = "failed";
    await persistState();
    return;
  }

  await emitStatusEvent("FLOW_TAB_READY", {
    url: pingRes.url,
    title: pingRes.title,
    authenticated: pingRes.authenticated,
    inProject: pingRes.inProject,
    agentMode: pingRes.agentMode
  });

  if (pingRes.agentFound) {
    await emitStatusEvent("AGENT_INTERFACE_FOUND", { mode: pingRes.agentMode });
  } else {
    await emitStatusEvent("AGENT_INTERFACE_FOUND", {
      mode: pingRes.agentMode || "FLOW_COMPOSER",
      note: "Using Google Flow Composer interface"
    });
  }

  await emitStatusEvent("SCRIPT_INSERTED", { project_id: p.projectId });

  // Start DOM monitoring on Flow tab
  await sendToFlowTab(tabId, { action: "start_monitoring" });

  if (pingRes.agentMode === "FLOW_AGENT_NATIVE") {
    // Flow Agent Native: Submit full project script
    const submitRes = await sendToFlowTab(tabId, {
      action: "submit_project_script",
      project: p
    });

    if (!submitRes || !submitRes.success) {
      await emitStatusEvent(submitRes?.step || "SUBMISSION_NOT_ACCEPTED", {
        error: submitRes?.error || "Failed to submit script to Google Flow Agent"
      });
      p.status = "failed";
      await persistState();
      return;
    }

    isProjectSubmitted = true;
    p.scenes.forEach((s) => sceneTracker?.markSceneGenerating(s.sceneNumber));
    await persistState();

    await emitStatusEvent("SCRIPT_SUBMITTED", { agentMode: submitRes.agentMode });
    await emitStatusEvent("AGENT_ACCEPTED", { agentMode: submitRes.agentMode });
    await emitStatusEvent("GENERATION_STARTED", { project_id: p.projectId });
  } else {
    // Direct Composer Mode: Submit Scene 1
    const scene1 = p.scenes[0];
    const prompt1 = scene1?.imagePrompt || scene1?.videoPrompt || p.fullScript;
    sceneTracker.markSceneSubmitting(scene1.sceneNumber);
    await persistState();

    const submitRes = await sendToFlowTab(tabId, {
      action: "submit_scene_prompt",
      prompt: prompt1,
      sceneNumber: scene1.sceneNumber
    });

    if (!submitRes || !submitRes.success) {
      await emitStatusEvent(submitRes?.step || "SUBMISSION_NOT_ACCEPTED", {
        error: submitRes?.error || `Failed to submit Scene 1 to Flow Composer`
      });
      p.status = "failed";
      await persistState();
      return;
    }

    isProjectSubmitted = true;
    sceneTracker.markSceneGenerating(scene1.sceneNumber);
    await persistState();

    await emitStatusEvent("SCRIPT_SUBMITTED", { agentMode: "FLOW_COMPOSER" });
    await emitStatusEvent("AGENT_ACCEPTED", { agentMode: "FLOW_COMPOSER" });
    await emitStatusEvent("GENERATION_STARTED", {
      project_id: p.projectId,
      scene_number: scene1.sceneNumber,
      scene_title: scene1.sceneTitle
    });
  }
}

// 8. Handle Intercepted Media with Smart Scene Matching
async function handleCapturedMedia(mediaUrl: string, metadata?: any) {
  if (!sceneTracker || downloadedMediaUrls.has(mediaUrl)) return;
  downloadedMediaUrls.add(mediaUrl);

  const match = sceneTracker.matchMediaToScene(mediaUrl, metadata);
  await persistState();

  if (match.flagged || !match.matched) {
    console.warn(`[ServiceWorker] Flagged ambiguous media: ${match.reason}`);
    await emitStatusEvent("IMAGE_DETECTION_FLAGGED", {
      mediaUrl,
      reason: match.reason,
      savedAs: match.filename
    });
  } else if (match.scene) {
    await emitStatusEvent("MEDIA_DETECTED", {
      mediaUrl,
      scene_number: match.scene.sceneNumber,
      scene_title: match.scene.sceneTitle,
      confidence: match.confidence
    });
  }

  // Trigger Download
  await initiateDownload(mediaUrl, match.filename, match.scene?.sceneNumber);
}

async function initiateDownload(url: string, filename: string, sceneNumber?: number) {
  if (sceneNumber) {
    await emitStatusEvent("DOWNLOAD_STARTED", {
      scene_number: sceneNumber,
      filename
    });
  }

  chrome.downloads.download(
    {
      url,
      filename,
      saveAs: false
    },
    (downloadId) => {
      const err = chrome.runtime.lastError;
      if (err || !downloadId) {
        const errorMsg = `Download failed to initiate: ${err?.message || "Unknown error"}`;
        if (sceneNumber) {
          sceneTracker?.markSceneFailed(sceneNumber, errorMsg);
          emitStatusEvent("DOWNLOAD_FAILED", {
            scene_number: sceneNumber,
            filename,
            error: errorMsg
          });
        }
        return;
      }

      if (sceneNumber) {
        inFlightDownloads.set(downloadId, {
          sceneNumber,
          filename,
          mediaUrl: url,
          retries: 0
        });
      }
    }
  );
}

// 9. Download State Verification via chrome.downloads.onChanged
chrome.downloads.onChanged.addListener(async (delta) => {
  const item = inFlightDownloads.get(delta.id);
  if (!item) return;

  if (delta.state?.current === "complete") {
    inFlightDownloads.delete(delta.id);
    sceneTracker?.markSceneDownloaded(item.sceneNumber, delta.id, item.filename);
    await persistState();

    const scene = sceneTracker?.getScene(item.sceneNumber);
    await emitStatusEvent("DOWNLOAD_COMPLETED", {
      scene_number: item.sceneNumber,
      scene_title: scene?.sceneTitle,
      downloadId: delta.id,
      filename: item.filename
    });

    if (sceneTracker?.isAllScenesDownloaded()) {
      await handleProjectCompletion();
    } else {
      // Direct Composer mode: submit next scene
      handleNextSceneDispatch();
    }
  } else if (delta.state?.current === "interrupted") {
    const errorMsg = delta.error?.current || "Download interrupted";
    console.warn(`[ServiceWorker] Download ${delta.id} interrupted: ${errorMsg}`);

    if (item.retries < 3) {
      item.retries++;
      console.log(`[ServiceWorker] Retrying download for scene ${item.sceneNumber} (${item.retries}/3)...`);
      setTimeout(() => {
        chrome.downloads.download({ url: item.mediaUrl, filename: item.filename, saveAs: false }, (newId) => {
          if (newId) {
            inFlightDownloads.delete(delta.id);
            inFlightDownloads.set(newId, item);
          }
        });
      }, 1500 * item.retries);
    } else {
      inFlightDownloads.delete(delta.id);
      sceneTracker?.markSceneFailed(item.sceneNumber, errorMsg);
      await persistState();
      await emitStatusEvent("DOWNLOAD_FAILED", {
        scene_number: item.sceneNumber,
        filename: item.filename,
        error: errorMsg
      });
    }
  }
});

// 10. Sequential Scene Dispatcher for Composer Mode
async function handleNextSceneDispatch(retryCount = 0) {
  if (!sceneTracker) return;
  const p = sceneTracker.getProject();
  if (p.status !== "processing") return;

  const nextScene = p.scenes.find((s) => s.downloadStatus === "pending" && s.generationStatus === "pending");
  if (!nextScene) return;

  console.log(`[ServiceWorker] Submitting next sequential scene: #${nextScene.sceneNumber} - ${nextScene.sceneTitle}`);
  setTimeout(async () => {
    const tabId = await getFlowTabId();
    if (tabId && sceneTracker && sceneTracker.getProject().status === "processing") {
      const prompt = nextScene.imagePrompt || nextScene.videoPrompt || "";
      sceneTracker.markSceneSubmitting(nextScene.sceneNumber);
      await persistState();

      await emitStatusEvent("SCRIPT_SUBMITTED", {
        project_id: p.projectId,
        scene_number: nextScene.sceneNumber,
        scene_title: nextScene.sceneTitle
      });

      const res = await sendToFlowTab(tabId, {
        action: "submit_scene_prompt",
        prompt,
        sceneNumber: nextScene.sceneNumber
      });

      if (res?.success) {
        sceneTracker.markSceneGenerating(nextScene.sceneNumber);
        await persistState();

        await emitStatusEvent("GENERATION_STARTED", {
          project_id: p.projectId,
          scene_number: nextScene.sceneNumber,
          scene_title: nextScene.sceneTitle
        });
      } else {
        const errorMsg = res?.error || "Failed to submit scene prompt";
        console.warn(`[ServiceWorker] Scene ${nextScene.sceneNumber} submission error:`, errorMsg);

        if (retryCount < 2) {
          console.log(`[ServiceWorker] Retrying Scene ${nextScene.sceneNumber} after cooldown (attempt ${retryCount + 1}/2)...`);
          setTimeout(() => handleNextSceneDispatch(retryCount + 1), 6000);
        } else {
          sceneTracker.markSceneFailed(nextScene.sceneNumber, errorMsg);
          await persistState();
          await emitStatusEvent("SUBMISSION_NOT_ACCEPTED", {
            project_id: p.projectId,
            scene_number: nextScene.sceneNumber,
            error: errorMsg
          });
        }
      }
    }
  }, 3500);
}

// 11. Project Manifest Saving on Completion
async function saveProjectManifest() {
  if (!sceneTracker) return;
  const manifest = sceneTracker.generateManifest();
  const manifestJson = JSON.stringify(manifest, null, 2);
  const dataUri = `data:application/json;charset=utf-8,${encodeURIComponent(manifestJson)}`;
  const p = sceneTracker.getProject();
  const filename = `Generated/${p.projectTitle}/manifest.json`;

  chrome.downloads.download({
    url: dataUri,
    filename,
    saveAs: false,
    conflictAction: "overwrite"
  });
}

async function handleProjectCompletion() {
  if (!sceneTracker) return;
  const p = sceneTracker.getProject();
  p.status = "completed";
  p.completedAt = Date.now();
  await persistState();
  await saveProjectManifest();

  // Turn off DOM monitoring on tab
  const tabId = await getFlowTabId();
  if (tabId) {
    sendToFlowTab(tabId, { action: "stop_monitoring" }).catch(() => {});
  }

  await emitStatusEvent("JOB_COMPLETED", {
    project_id: p.projectId,
    project_title: p.projectTitle,
    total_scenes: p.scenes.length,
    downloads: p.scenes.map((s) => ({
      scene: s.sceneNumber,
      title: s.sceneTitle,
      path: s.actualOutputFilename
    }))
  });
}

// 12. Lightweight Event-Driven Bridge Polling
async function checkBridgeOnce() {
  try {
    const ping = await fetch(`${BRIDGE_URL}/api/heartbeat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" }
    });

    if (ping.ok) {
      if (!isBridgeConnected) {
        isBridgeConnected = true;
        await emitStatusEvent("BRIDGE_CONNECTED", { port: 8795 });
      }
    } else {
      isBridgeConnected = false;
    }

    // Check for incoming projects
    const res = await fetch(`${BRIDGE_URL}/api/agent/next`);
    if (res.ok) {
      const data = await res.json();
      if (data && data.action === "reload") {
        console.log("[ServiceWorker] Reload requested by bridge");
        chrome.runtime.reload();
        return;
      }
      if (data && data.action === "reload_flow_tab") {
        const tabId = await getFlowTabId();
        if (tabId) {
          console.log("[ServiceWorker] Reloading Flow tab:", tabId);
          chrome.tabs.reload(tabId);
        }
        return;
      }
      if (data && data.action === "inspect_dom") {
        const tabId = await getFlowTabId();
        if (tabId) {
          const dom = await sendToFlowTab(tabId, { action: "inspect_dom" });
          await fetch(`${BRIDGE_URL}/api/dom/snapshot`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(dom || {})
          }).catch(() => {});
        }
        return;
      }
      if (data && data.project) {
        await executeProject(data.project);
      }
    }
  } catch (_) {
    isBridgeConnected = false;
  }
}

async function startBridgePolling() {
  await restoreState();

  // Setup periodic alarm for MV3 service worker resilience
  try {
    chrome.alarms.create("flow_bridge_alarm", { periodInMinutes: 0.1 });
    chrome.alarms.onAlarm.addListener((alarm) => {
      if (alarm.name === "flow_bridge_alarm") {
        checkBridgeOnce();
      }
    });
  } catch (_) {}

  while (true) {
    let pollInterval = 4000; // Normal poll rate: 4s
    await checkBridgeOnce();

    // Faster polling only when active project is processing
    if (sceneTracker && sceneTracker.getProject().status === "processing") {
      pollInterval = 1500;
    }

    await new Promise((r) => setTimeout(r, pollInterval));
  }
}

// 13. Runtime Message Listener
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === "content_heartbeat") {
    if (!isBridgeConnected) {
      checkBridgeOnce();
    }
    sendResponse({ ok: true, bridgeConnected: isBridgeConnected });
    return true;
  }

  if (message.action === "submit_trusted") {
    const tabId = sender.tab?.id || cachedFlowTabId;
    if (tabId) {
      submitTrusted(tabId, message).then((res) => sendResponse(res));
      return true;
    }
    sendResponse({ success: false, error: "No target tab for trusted submit" });
    return true;
  }

  if (message.action === "director_event" && message.payload) {
    emitStatusEvent(message.payload.event, message.payload);
    sendResponse({ ok: true });
    return true;
  }

  if (message.action === "click_trusted") {
    const tabId = sender.tab?.id || cachedFlowTabId;
    if (tabId) {
      clickTrusted(tabId, message.x, message.y).then((ok) => sendResponse({ ok }));
      return true;
    }
    sendResponse({ ok: false, error: "No sender tab" });
    return true;
  }

  if (message.action === "media_intercepted") {
    handleCapturedMedia(message.url, message.metadata);
    sendResponse({ ok: true });
    return true;
  }

  if (message.action === "get_status") {
    getFlowTabId().then((tabId) => {
      sendResponse({
        bridgeConnected: isBridgeConnected,
        activeProject: sceneTracker?.getProject() || null,
        flowTabFound: Boolean(tabId)
      });
    });
    return true;
  }

  if (message.action === "submit_test_project") {
    executeProject(message.project).then(() => sendResponse({ ok: true }));
    return true;
  }
});

startBridgePolling();
