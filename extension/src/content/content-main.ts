import { FlowAdapter } from "./flow-adapter";
import { CooldownManager } from "./cooldown-manager";
import { queryAllDeep } from "./shadow-dom";

const adapter = new FlowAdapter();
const cooldown = new CooldownManager();
const seenMediaUrls = new Set<string>();

let activeMutationObserver: MutationObserver | null = null;
let isMonitoringActive = false;
let domScanDebounceTimer: any = null;

// 1. Inject Network Interceptor into Google Flow Page World
function injectNetworkInterceptor() {
  if (document.getElementById("flow-studio-injected-script")) return;
  const script = document.createElement("script");
  script.id = "flow-studio-injected-script";
  try {
    script.src = chrome.runtime.getURL("dist/injected.js");
  } catch (_) {
    script.src = chrome.runtime.getURL("injected.js");
  }
  script.onload = () => script.remove();
  (document.head || document.documentElement).appendChild(script);
}

if (adapter.isFlowPage()) {
  injectNetworkInterceptor();
}

// 2. Listen for Media Events from Injected Interceptor
window.addEventListener("message", (event) => {
  if (event.source !== window) return;

  let mediaUrl = "";
  let metadata: any = undefined;

  if (event.data?.type === "FLOW_MEDIA_READY" && event.data.url) {
    mediaUrl = event.data.url;
    metadata = event.data.metadata;
  } else if (event.data?.__faNet && event.data.kind === "media-ready" && event.data.url) {
    mediaUrl = event.data.url;
  }

  if (!mediaUrl || seenMediaUrls.has(mediaUrl)) return;
  seenMediaUrls.add(mediaUrl);

  console.log("[Flow Automation Content] Captured Media URL:", mediaUrl);

  chrome.runtime
    .sendMessage({
      action: "media_intercepted",
      url: mediaUrl,
      metadata,
      timestamp: Date.now()
    })
    .catch(() => {});
});

// 3. Lightweight Scoped DOM Observation for Rendered Media Images
function scanDomMedia() {
  if (!adapter.isFlowPage()) return;
  const elements = queryAllDeep([
    "img",
    "video",
    "source",
    "[style*='background-image']",
    "flow-media-card",
    "flow-image-card"
  ]);

  let cardIndex = 0;
  for (const el of elements) {
    let src = "";
    let promptSnippet: string | undefined;

    if (el.tagName === "IMG" || el instanceof HTMLImageElement) {
      src = (el as HTMLImageElement).src || el.getAttribute("src") || "";
      promptSnippet = el.getAttribute("alt") || el.getAttribute("aria-label") || undefined;
    } else if (el.tagName === "VIDEO" || el.tagName === "SOURCE") {
      src = (el as HTMLVideoElement).src || el.getAttribute("src") || "";
      promptSnippet = el.getAttribute("aria-label") || undefined;
    } else {
      const bg = el.style?.backgroundImage || window.getComputedStyle(el).backgroundImage || "";
      const match = bg.match(/url\(["']?([^"')]+)["']?\)/);
      if (match) src = match[1];
      promptSnippet = el.getAttribute("aria-label") || el.getAttribute("title") || undefined;
    }

    if (!src || src.startsWith("data:image/svg") || seenMediaUrls.has(src)) continue;
    const isGeneratedMedia =
      (src.startsWith("blob:") ||
        src.startsWith("data:image") ||
        src.includes("flow-content.google/image/") ||
        src.includes("flow-content.google/video/") ||
        src.includes("googleusercontent.com/image/") ||
        src.includes("googleusercontent.com/video/")) &&
      !src.includes("/ogw/") &&
      !src.includes("photo.jpg") &&
      !src.includes("profile") &&
      !src.includes("account") &&
      !src.includes("avatar") &&
      !src.includes("icon") &&
      !src.includes("=s");

    if (isGeneratedMedia) {
      seenMediaUrls.add(src);
      console.log("[Flow Content DOM] Captured Generated Media:", src.slice(0, 50));

      const itemMetadata = {
        promptSnippet,
        cardIndex,
        source: "dom"
      };
      cardIndex++;

      if (src.startsWith("blob:")) {
        fetch(src)
          .then((r) => r.blob())
          .then((blob) => {
            const reader = new FileReader();
            reader.onloadend = () => {
              const dataUrl = reader.result as string;
              chrome.runtime
                .sendMessage({
                  action: "media_intercepted",
                  url: dataUrl,
                  metadata: itemMetadata,
                  timestamp: Date.now()
                })
                .catch(() => {});
            };
            reader.readAsDataURL(blob);
          })
          .catch(() => {
            chrome.runtime
              .sendMessage({
                action: "media_intercepted",
                url: src,
                metadata: itemMetadata,
                timestamp: Date.now()
              })
              .catch(() => {});
          });
      } else {
        chrome.runtime
          .sendMessage({
            action: "media_intercepted",
            url: src,
            metadata: itemMetadata,
            timestamp: Date.now()
          })
          .catch(() => {});
      }
    }
  }
}

function startDomMonitoring() {
  if (isMonitoringActive) return;
  isMonitoringActive = true;

  // Initial baseline scan
  scanDomMedia();

  // Scoped MutationObserver with debouncing
  if (!activeMutationObserver) {
    activeMutationObserver = new MutationObserver(() => {
      if (domScanDebounceTimer) clearTimeout(domScanDebounceTimer);
      domScanDebounceTimer = setTimeout(() => {
        if (isMonitoringActive) scanDomMedia();
      }, 600);
    });

    const target = document.body || document.documentElement;
    activeMutationObserver.observe(target, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ["src", "style", "class"]
    });
  }
}

function stopDomMonitoring() {
  isMonitoringActive = false;
  if (domScanDebounceTimer) {
    clearTimeout(domScanDebounceTimer);
    domScanDebounceTimer = null;
  }
  if (activeMutationObserver) {
    activeMutationObserver.disconnect();
    activeMutationObserver = null;
  }
}

// Initial baseline indexing on page load
if (adapter.isFlowPage()) {
  setTimeout(scanDomMedia, 1500);
}

// 4. Message Router for Background Service Worker
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "ping") {
    const isFlow = adapter.isFlowPage();
    const authenticated = isFlow && adapter.isAuthenticated();
    const detection = isFlow ? adapter.detectAgentOrComposer() : null;
    sendResponse({
      pong: true,
      isFlow,
      url: window.location.href,
      title: document.title,
      authenticated,
      inProject: !!detection?.inputElement,
      agentMode: detection?.modeName || "NONE",
      agentFound: !!detection?.agentFound,
      isCooldown: cooldown.waiting
    });
    return true;
  }

  if (request.action === "inspect_dom") {
    const detection = adapter.detectAgentOrComposer();
    const composer = detection.inputElement;
    const submitBtn = adapter.findSubmitButton();
    const allBtns = queryAllDeep(["button", 'div[role="button"]']).map((b: any) => ({
      tag: b.tagName,
      text: (b.innerText || b.textContent || "").trim().slice(0, 40),
      ariaLabel: b.getAttribute("aria-label"),
      disabled: b.disabled || b.getAttribute("aria-disabled") === "true",
      rect: b.getBoundingClientRect()
    }));

    const allImgs = queryAllDeep(["img", "video", "[style*='background-image']"]).map((el: any) => {
      let src = el.src || el.getAttribute("src") || "";
      if (!src && el.style?.backgroundImage) {
        const m = el.style.backgroundImage.match(/url\(["']?([^"')]+)["']?\)/);
        if (m) src = m[1];
      }
      return {
        tag: el.tagName,
        src: src.slice(0, 150),
        alt: (el.alt || el.getAttribute("aria-label") || el.title || "").slice(0, 50),
        width: el.naturalWidth || el.videoWidth || el.clientWidth || 0,
        height: el.naturalHeight || el.videoHeight || el.clientHeight || 0
      };
    });

    sendResponse({
      url: window.location.href,
      title: document.title,
      detection: {
        modeName: detection.modeName,
        agentFound: detection.agentFound,
        hasInputElement: !!detection.inputElement
      },
      composerText: composer ? (composer.textContent || (composer as any).value || "").slice(0, 200) : null,
      submitBtn: submitBtn
        ? {
            tag: submitBtn.tagName,
            text: (submitBtn.innerText || submitBtn.textContent || "").trim(),
            ariaLabel: submitBtn.getAttribute("aria-label"),
            disabled: submitBtn.disabled || submitBtn.getAttribute("aria-disabled") === "true",
            rect: submitBtn.getBoundingClientRect()
          }
        : null,
      allButtonsCount: allBtns.length,
      buttons: allBtns.filter((b: any) => b.text || b.ariaLabel).slice(0, 30),
      images: allImgs,
      bodyText: document.body.innerText.slice(0, 1000)
    });
    return true;
  }

  if (request.action === "start_monitoring") {
    startDomMonitoring();
    sendResponse({ ok: true });
    return true;
  }

  if (request.action === "stop_monitoring") {
    stopDomMonitoring();
    sendResponse({ ok: true });
    return true;
  }

  if (request.action === "submit_project_script") {
    startDomMonitoring();
    handleProjectScriptSubmission(request.project).then((res) => {
      sendResponse(res);
    });
    return true;
  }

  if (request.action === "flow_agent_submit") {
    startDomMonitoring();
    const project = {
      project_id: request.sceneId || "proj_" + Date.now(),
      project_title: request.scene?.sceneTitle || "Production",
      full_script: request.instructions || request.scene?.imagePrompt || "",
      scenes: request.scene ? [request.scene] : []
    };
    handleProjectScriptSubmission(project).then((res) => {
      sendResponse(res);
    });
    return true;
  }

  if (
    request.action === "submit_scene_prompt" ||
    request.action === "submit_job" ||
    request.action === "run_prompt"
  ) {
    startDomMonitoring();
    const promptText = request.prompt || request.job?.resolvedPrompt || request.job?.prompt || "";
    handleSinglePromptSubmission(promptText, request.sceneNumber || 1).then((res) => {
      sendResponse(res);
    });
    return true;
  }
});

/**
 * Executes Part 2: Real Flow Agent / Composer submission with strict State Machine:
 * EDITOR_DETECTED -> SCRIPT_INSERTED -> EDITOR_UPDATED -> GENERATE_READY -> SUBMIT_TRIGGERED -> AGENT_ACCEPTED -> GENERATION_STARTED
 */
async function handleProjectScriptSubmission(project: any): Promise<{
  success: boolean;
  step: string;
  agentMode: string;
  error?: string;
}> {
  if (!adapter.isFlowPage()) {
    return {
      success: false,
      step: "FLOW_TAB_NOT_FLOW",
      agentMode: "NONE",
      error: "Not a Google Flow tab"
    };
  }

  if (cooldown.detectUnusualActivity()) {
    console.warn("[Flow Content] Unusual activity detected before submission.");
    await cooldown.handleCooldown(120);
  }

  const inProject = await adapter.ensureInProject();
  if (!inProject) {
    return {
      success: false,
      step: "FLOW_TAB_NOT_READY",
      agentMode: "NONE",
      error: "Could not open or locate Flow project composer"
    };
  }

  // 1. EDITOR_DETECTED
  const detection = adapter.detectAgentOrComposer();
  if (!detection.inputElement || !adapter.checkEditorReady(detection.inputElement)) {
    return {
      success: false,
      step: "EDITOR_NOT_READY",
      agentMode: detection.modeName,
      error: detection.reason || "Flow prompt editor not ready for input"
    };
  }

  chrome.runtime.sendMessage({
    action: "director_event",
    payload: { event: "EDITOR_DETECTED", project_id: project.project_id, agentMode: detection.modeName, timestamp: Date.now() }
  }).catch(() => {});

  // 2. SCRIPT_INSERTED
  const scriptContent = project.full_script || buildScriptFromScenes(project);
  const inserted = await adapter.insertScriptText(detection.inputElement, scriptContent);
  if (!inserted) {
    return {
      success: false,
      step: "SCRIPT_INSERTION_FAILED",
      agentMode: detection.modeName,
      error: "Failed to insert script into Flow editor"
    };
  }

  chrome.runtime.sendMessage({
    action: "director_event",
    payload: { event: "SCRIPT_INSERTED", project_id: project.project_id, timestamp: Date.now() }
  }).catch(() => {});

  // 3. EDITOR_UPDATED
  const retainedText = (detection.inputElement.textContent || (detection.inputElement as any).value || "").trim();
  if (retainedText.length === 0) {
    return {
      success: false,
      step: "SCRIPT_INSERTION_FAILED",
      agentMode: detection.modeName,
      error: "Editor did not retain inserted script"
    };
  }

  chrome.runtime.sendMessage({
    action: "director_event",
    payload: { event: "EDITOR_UPDATED", project_id: project.project_id, length: retainedText.length, timestamp: Date.now() }
  }).catch(() => {});

  // 4. GENERATE_READY
  const readyCheck = await adapter.waitForGenerateReady(8000);
  if (!readyCheck.ready || !readyCheck.btn) {
    const candidateButtons = queryAllDeep(["button", 'div[role="button"]'])
      .map((b: any) => `<${b.tagName} label="${b.getAttribute("aria-label")}" text="${b.innerText?.trim()?.slice(0, 20)}" class="${b.className?.slice?.(0, 25)}">`)
      .slice(0, 12)
      .join("; ");
    return {
      success: false,
      step: readyCheck.error || "GENERATE_BUTTON_DISABLED",
      agentMode: detection.modeName,
      error: `Generate button not ready (${readyCheck.error}) [Buttons: ${candidateButtons}]`
    };
  }

  chrome.runtime.sendMessage({
    action: "director_event",
    payload: { event: "GENERATE_READY", project_id: project.project_id, btnText: readyCheck.btn.innerText?.trim(), timestamp: Date.now() }
  }).catch(() => {});

  // 5. SUBMIT_TRIGGERED
  const triggerRes = await adapter.triggerSubmit(readyCheck.btn, detection.inputElement, scriptContent);
  if (!triggerRes.success) {
    return {
      success: false,
      step: "SUBMISSION_NOT_TRIGGERED",
      agentMode: detection.modeName,
      error: triggerRes.error || "Failed to trigger Generate interaction"
    };
  }

  chrome.runtime.sendMessage({
    action: "director_event",
    payload: { event: "SUBMIT_TRIGGERED", project_id: project.project_id, agentMode: detection.modeName, timestamp: Date.now() }
  }).catch(() => {});

  // 6. AGENT_ACCEPTED & GENERATION_STARTED
  const verifyRes = await adapter.verifySubmissionAccepted(9000);
  if (!verifyRes.accepted) {
    const btn = adapter.findSubmitButton();
    const btnInfo = btn
      ? `<${btn.tagName} disabled=${btn.disabled} aria-label="${btn.getAttribute("aria-label")}">`
      : "null";
    return {
      success: false,
      step: "AGENT_NOT_ACKNOWLEDGED",
      agentMode: detection.modeName,
      error: `Flow did not acknowledge generation submission within deadline (btn=${btnInfo})`
    };
  }

  chrome.runtime.sendMessage({
    action: "director_event",
    payload: { event: "AGENT_ACCEPTED", project_id: project.project_id, evidence: verifyRes.evidence, timestamp: Date.now() }
  }).catch(() => {});

  chrome.runtime.sendMessage({
    action: "director_event",
    payload: { event: "GENERATION_STARTED", project_id: project.project_id, timestamp: Date.now() }
  }).catch(() => {});

  return {
    success: true,
    step: "GENERATION_STARTED",
    agentMode: detection.modeName
  };
}

async function handleSinglePromptSubmission(
  promptText: string,
  sceneNumber: number
): Promise<{
  success: boolean;
  step: string;
  error?: string;
}> {
  const inProject = await adapter.ensureInProject();
  if (!inProject) {
    return {
      success: false,
      step: "FLOW_TAB_NOT_READY",
      error: "Could not find Flow project composer"
    };
  }

  // 1. EDITOR_DETECTED
  const detection = adapter.detectAgentOrComposer();
  if (!detection.inputElement || !adapter.checkEditorReady(detection.inputElement)) {
    return {
      success: false,
      step: "EDITOR_NOT_READY",
      error: "Prompt input element not ready"
    };
  }

  chrome.runtime.sendMessage({
    action: "director_event",
    payload: { event: "EDITOR_DETECTED", scene_number: sceneNumber, agentMode: detection.modeName, timestamp: Date.now() }
  }).catch(() => {});

  // 2. SCRIPT_INSERTED
  const inserted = await adapter.insertScriptText(detection.inputElement, promptText);
  if (!inserted) {
    return {
      success: false,
      step: "SCRIPT_INSERTION_FAILED",
      error: "Failed to type prompt into Flow input"
    };
  }

  chrome.runtime.sendMessage({
    action: "director_event",
    payload: { event: "SCRIPT_INSERTED", scene_number: sceneNumber, timestamp: Date.now() }
  }).catch(() => {});

  // 3. GENERATE_READY (allow up to 10s for button enabled state between scenes)
  const readyCheck = await adapter.waitForGenerateReady(10000);
  if (!readyCheck.ready || !readyCheck.btn) {
    const candidateButtons = queryAllDeep(["button", 'div[role="button"]'])
      .map((b: any) => `<${b.tagName} label="${b.getAttribute("aria-label")}" text="${b.innerText?.trim()?.slice(0, 20)}" class="${b.className?.slice?.(0, 25)}">`)
      .slice(0, 12)
      .join("; ");
    return {
      success: false,
      step: readyCheck.error || "GENERATE_BUTTON_DISABLED",
      error: `Generate button not ready (${readyCheck.error}) [Buttons: ${candidateButtons}]`
    };
  }

  chrome.runtime.sendMessage({
    action: "director_event",
    payload: { event: "GENERATE_READY", scene_number: sceneNumber, timestamp: Date.now() }
  }).catch(() => {});

  // 4. SUBMIT_TRIGGERED
  const triggerRes = await adapter.triggerSubmit(readyCheck.btn, detection.inputElement, promptText);
  if (!triggerRes.success) {
    return {
      success: false,
      step: "SUBMISSION_NOT_TRIGGERED",
      error: triggerRes.error
    };
  }

  chrome.runtime.sendMessage({
    action: "director_event",
    payload: { event: "SUBMIT_TRIGGERED", scene_number: sceneNumber, timestamp: Date.now() }
  }).catch(() => {});

  // 5. AGENT_ACCEPTED
  const verifyRes = await adapter.verifySubmissionAccepted(10000);
  if (!verifyRes.accepted) {
    return {
      success: false,
      step: "AGENT_NOT_ACKNOWLEDGED",
      error: "Flow did not transition to generating state within deadline"
    };
  }

  chrome.runtime.sendMessage({
    action: "director_event",
    payload: { event: "AGENT_ACCEPTED", scene_number: sceneNumber, evidence: verifyRes.evidence, timestamp: Date.now() }
  }).catch(() => {});

  return { success: true, step: "GENERATION_STARTED" };
}

function buildScriptFromScenes(project: any): string {
  if (!project.scenes || project.scenes.length === 0) return project.full_script || "";
  let script = `PROJECT: ${project.project_title || project.title || "Autonomous Production"}\n\n`;
  for (const scene of project.scenes) {
    const num = scene.scene_number || scene.sceneNumber || 1;
    const title = scene.scene_title || scene.title || scene.sceneTitle || `Scene ${num}`;
    const desc = scene.image_prompt || scene.imagePrompt || scene.video_prompt || scene.videoPrompt || "";
    script += `[SCENE ${num}: ${title}]\n${desc}\n\n`;
  }
  return script.trim();
}

// Keepalive heartbeat to Service Worker to prevent MV3 termination while Flow tab is open
setInterval(() => {
  if (adapter.isFlowPage()) {
    chrome.runtime.sendMessage({ action: "content_heartbeat" }).catch(() => {});
  }
}, 4000);
