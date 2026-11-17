import React, { useState, useEffect, useCallback } from "react";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Download,
  Film,
  Layers,
  Radio,
  RefreshCw,
  Sparkles,
  Terminal,
  Wifi,
  WifiOff
} from "lucide-react";

interface SceneItem {
  sceneNumber?: number;
  scene_number?: number;
  sceneTitle?: string;
  scene_title?: string;
  imagePrompt?: string;
  image_prompt?: string;
  videoPrompt?: string;
  video_prompt?: string;
  generationStatus?: string;
  downloadStatus?: string;
  status?: string;
  actualOutputFilename?: string;
  downloadPath?: string;
  mediaUrl?: string;
}

interface ProjectState {
  projectId?: string;
  project_id?: string;
  projectTitle?: string;
  project_title?: string;
  fullScript?: string;
  full_script?: string;
  scenes: SceneItem[];
  status: string;
  completedAt?: number;
  unassignedOutputs?: Array<{
    url: string;
    filename: string;
    timestamp: number;
    reason: string;
  }>;
}

interface EventItem {
  event: string;
  timestamp: number;
  project_id?: string;
  scene_number?: number;
  scene_title?: string;
  filename?: string;
  error?: string;
  mode?: string;
  confidence?: number;
  stage?: string;
}

export const App: React.FC = () => {
  const [bridgeConnected, setBridgeConnected] = useState(false);
  const [flowTabFound, setFlowTabFound] = useState(false);
  const [agentMode, setAgentMode] = useState<string>("DETECTING");
  const [activeProject, setActiveProject] = useState<ProjectState | null>(null);
  const [events, setEvents] = useState<EventItem[]>([]);

  // Fetch Bridge and Extension Status
  const pollStatus = useCallback(async () => {
    try {
      const res = await fetch("http://127.0.0.1:8795/health");
      if (res.ok) {
        const data = await res.json();
        setBridgeConnected(true);
        if (data.recentEvents && data.recentEvents.length > 0) {
          setEvents(data.recentEvents.slice().reverse());
        }
      } else {
        setBridgeConnected(false);
      }
    } catch (_) {
      setBridgeConnected(false);
    }

    // Check Flow tab from background
    chrome.runtime.sendMessage({ action: "get_status" }, (res) => {
      if (!chrome.runtime.lastError && res) {
        setFlowTabFound(Boolean(res.flowTabFound));
        if (res.activeProject) {
          setActiveProject(res.activeProject);
        }
      }
    });

    // Also fetch latest events from bridge
    try {
      const evRes = await fetch("http://127.0.0.1:8795/api/events?limit=30");
      if (evRes.ok) {
        const data = await evRes.json();
        if (data.events) {
          setEvents(data.events.slice().reverse());
          const agentEv = data.events.slice().reverse().find((e: any) => e.event === "AGENT_INTERFACE_FOUND");
          if (agentEv?.mode) setAgentMode(agentEv.mode);
        }
      }
    } catch (_) {}
  }, []);

  useEffect(() => {
    pollStatus();
    // Relaxed fallback poll: 4s
    const timer = setInterval(pollStatus, 4000);

    // Event-driven broadcast listener
    const listener = (message: any) => {
      if (message.action === "director_event" && message.payload) {
        setEvents((prev) => [message.payload, ...prev.slice(0, 49)]);
        if (message.payload.mode) setAgentMode(message.payload.mode);

        // Immediate background status refresh when meaningful events arrive
        if (
          ["SCRIPT_RECEIVED", "DOWNLOAD_COMPLETED", "JOB_COMPLETED", "DOWNLOAD_FAILED", "JOB_FAILED"].includes(
            message.payload.event
          )
        ) {
          pollStatus();
        }
      }
    };
    chrome.runtime.onMessage.addListener(listener);

    return () => {
      clearInterval(timer);
      chrome.runtime.onMessage.removeListener(listener);
    };
  }, [pollStatus]);

  const latestEvent = events[0]?.event || "IDLE";
  const recentErrors = events.filter(
    (e) =>
      e.event.includes("FAIL") ||
      e.event.includes("UNAVAILABLE") ||
      e.event.includes("NOT_DETECTED") ||
      e.event.includes("REJECTED") ||
      Boolean(e.error)
  );

  const getSceneNum = (s: SceneItem, i: number) => s.sceneNumber ?? s.scene_number ?? i + 1;
  const getSceneTitle = (s: SceneItem, i: number) => s.sceneTitle ?? s.scene_title ?? `Scene ${i + 1}`;
  const getScenePrompt = (s: SceneItem) => s.imagePrompt || s.image_prompt || s.videoPrompt || s.video_prompt || "Scene prompt";
  const getSceneDownloadPath = (s: SceneItem) => s.actualOutputFilename || s.downloadPath;
  const isSceneDownloaded = (s: SceneItem) => s.downloadStatus === "downloaded" || s.status === "downloaded";
  const isSceneGenerating = (s: SceneItem) =>
    s.generationStatus === "generating" || s.generationStatus === "submitting" || s.status === "generating";

  const completedCount = activeProject
    ? activeProject.scenes.filter((s) => isSceneDownloaded(s)).length
    : 0;

  return (
    <div className="min-h-screen bg-[#07090e] text-slate-100 p-4 font-sans selection:bg-cyan-500/30">
      {/* Top Header */}
      <header className="glass-panel p-4 mb-4 flex items-center justify-between border-cyan-500/20 shadow-lg shadow-cyan-950/20">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-600 via-indigo-600 to-fuchsia-600 flex items-center justify-center shadow-lg shadow-indigo-500/30">
            <Film className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-base font-bold tracking-tight text-white flex items-center gap-2">
              Flow Connect
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
                2.0 PROD
              </span>
            </h1>
            <p className="text-xs text-slate-400 font-mono">Antigravity Autonomous Director Bridge</p>
          </div>
        </div>

        <button
          onClick={pollStatus}
          className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 transition-all border border-white/10"
          title="Refresh Status"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </header>

      {/* Connection & Status Strip */}
      <div className="grid grid-cols-3 gap-2.5 mb-4">
        {/* Bridge Status */}
        <div className="glass-card p-3 border border-white/5">
          <div className="flex items-center gap-2 mb-1">
            {bridgeConnected ? (
              <Wifi className="w-3.5 h-3.5 text-emerald-400 animate-pulse" />
            ) : (
              <WifiOff className="w-3.5 h-3.5 text-rose-400" />
            )}
            <span className="text-[11px] font-medium uppercase tracking-wider text-slate-400">Bridge</span>
          </div>
          <div className="text-xs font-semibold font-mono">
            {bridgeConnected ? (
              <span className="text-emerald-400">Port 8795 OK</span>
            ) : (
              <span className="text-rose-400">Disconnected</span>
            )}
          </div>
        </div>

        {/* Flow Tab Status */}
        <div className="glass-card p-3 border border-white/5">
          <div className="flex items-center gap-2 mb-1">
            <Radio className={`w-3.5 h-3.5 ${flowTabFound ? "text-cyan-400" : "text-amber-400"}`} />
            <span className="text-[11px] font-medium uppercase tracking-wider text-slate-400">Flow Tab</span>
          </div>
          <div className="text-xs font-semibold font-mono">
            {flowTabFound ? (
              <span className="text-cyan-400">Detected</span>
            ) : (
              <span className="text-amber-400">Searching...</span>
            )}
          </div>
        </div>

        {/* Flow Agent Mode */}
        <div className="glass-card p-3 border border-white/5">
          <div className="flex items-center gap-2 mb-1">
            <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
            <span className="text-[11px] font-medium uppercase tracking-wider text-slate-400">Agent Mode</span>
          </div>
          <div className="text-xs font-semibold font-mono truncate text-indigo-300" title={agentMode}>
            {agentMode === "DETECTING" ? "Auto-Detect" : agentMode.replace("FLOW_", "")}
          </div>
        </div>
      </div>

      {/* Quick Validation Triggers (Requirement 10) */}
      <div className="grid grid-cols-3 gap-2 mb-4">
        {/* Test 1: 2-Scene Project */}
        <button
          onClick={() => {
            fetch("http://127.0.0.1:8795/api/project/submit", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                project_id: `test_2scenes_${Date.now()}`,
                project_title: "Stickman_Artist_Studio",
                full_script: "PROJECT: Stickman Artist Studio\n\n[SCENE 1: Stickman Artist Awakening]\nMacro shot of textured rough watercolor paper on wooden desk. Sharp realistic 2D stickman drawn in dark 2B graphite pencil sitting up, paper texture visible, 8k.\n\n[SCENE 2: Stickman Drawing Portal]\nClose-up of stickman drawing a luminous glowing archway portal on paper, graphite dust catching rim light.",
                scenes: [
                  {
                    scene_number: 1,
                    scene_title: "Stickman_Artist_Awakening",
                    image_prompt: "Macro shot of textured rough watercolor paper on wooden desk. Sharp realistic 2D stickman drawn in dark 2B graphite pencil sitting up, paper texture visible, 8k."
                  },
                  {
                    scene_number: 2,
                    scene_title: "Stickman_Drawing_Portal",
                    image_prompt: "Close-up of stickman drawing a luminous glowing archway portal on paper, graphite dust catching rim light."
                  }
                ]
              })
            }).then(pollStatus);
          }}
          className="p-2 rounded-lg bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 text-[11px] font-mono font-semibold transition-all text-center flex items-center justify-center gap-1.5"
        >
          <Film className="w-3.5 h-3.5" />
          <span>Test 1 (2 Scenes)</span>
        </button>

        {/* Test 2: 5-Scene Project */}
        <button
          onClick={() => {
            fetch("http://127.0.0.1:8795/api/project/submit", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                project_id: `test_5scenes_${Date.now()}`,
                project_title: "Cyberpunk_Metropolis_5_Scenes",
                full_script: "PROJECT: Cyberpunk Metropolis\n\n[SCENE 1: Neon Skyline]\nWide aerial shot of cyberpunk skyline in purple neon rain.\n\n[SCENE 2: Chrome Interceptor]\nTracking shot of chrome hover vehicle through drenched lower streets.\n\n[SCENE 3: Cybernetic Pilot]\nCockpit view of augmented pilot with optical HUD reflections.\n\n[SCENE 4: Drone Ambush]\nSecurity drone squadron descending through neon billboards with red searchlights.\n\n[SCENE 5: Safe Haven]\nVehicle arriving at hidden subterranean sanctuary illuminated by amber glow.",
                scenes: [
                  { scene_number: 1, scene_title: "Neon_Skyline", image_prompt: "Wide aerial shot of cyberpunk skyline in purple neon rain." },
                  { scene_number: 2, scene_title: "Chrome_Interceptor", image_prompt: "Tracking shot of chrome hover vehicle through drenched lower streets." },
                  { scene_number: 3, scene_title: "Cybernetic_Pilot", image_prompt: "Cockpit view of augmented pilot with optical HUD reflections." },
                  { scene_number: 4, scene_title: "Drone_Ambush", image_prompt: "Security drone squadron descending through neon billboards with red searchlights." },
                  { scene_number: 5, scene_title: "Safe_Haven", image_prompt: "Vehicle arriving at hidden subterranean sanctuary illuminated by amber glow." }
                ]
              })
            }).then(pollStatus);
          }}
          className="p-2 rounded-lg bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 text-[11px] font-mono font-semibold transition-all text-center flex items-center justify-center gap-1.5"
        >
          <Film className="w-3.5 h-3.5" />
          <span>Test 2 (5 Scenes)</span>
        </button>

        {/* Test 3: Delayed & Out-of-Order Project */}
        <button
          onClick={() => {
            fetch("http://127.0.0.1:8795/api/project/submit", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                project_id: `test_ooo_${Date.now()}`,
                project_title: "Deep_Space_Out_Of_Order",
                full_script: "PROJECT: Deep Space Out of Order\n\n[SCENE 1: Starship Launch]\nStarship accelerating past lunar orbit with blue plasma trail.\n\n[SCENE 2: Asteroid Drift]\nStarship maneuvering through rotating ice asteroids.\n\n[SCENE 3: Distant Quasar]\nBlinding golden light from ancient quasar illuminating ship hull.",
                scenes: [
                  { scene_number: 1, scene_title: "Starship_Launch", image_prompt: "Starship accelerating past lunar orbit with blue plasma trail." },
                  { scene_number: 2, scene_title: "Asteroid_Drift", image_prompt: "Starship maneuvering through rotating ice asteroids." },
                  { scene_number: 3, scene_title: "Distant_Quasar", image_prompt: "Blinding golden light from ancient quasar illuminating ship hull." }
                ]
              })
            }).then(pollStatus);
          }}
          className="p-2 rounded-lg bg-fuchsia-500/10 hover:bg-fuchsia-500/20 text-fuchsia-300 border border-fuchsia-500/30 text-[11px] font-mono font-semibold transition-all text-center flex items-center justify-center gap-1.5"
        >
          <Film className="w-3.5 h-3.5" />
          <span>Test 3 (Out-of-Order)</span>
        </button>
      </div>

      {/* Production Stage Timeline */}
      <div className="glass-panel p-4 mb-4 border border-indigo-500/20">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-cyan-400" />
            <span className="text-xs font-bold uppercase tracking-wider text-slate-300">Live Stage</span>
          </div>
          <span className="text-[11px] font-mono px-2 py-0.5 rounded-md bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
            {latestEvent}
          </span>
        </div>

        <div className="grid grid-cols-4 gap-1.5 text-center text-[10px] font-mono">
          <div
            className={`p-1.5 rounded border ${
              [
                "SCRIPT_RECEIVED",
                "SCRIPT_INSERTED",
                "SCRIPT_SUBMITTED",
                "AGENT_ACCEPTED",
                "GENERATION_STARTED",
                "MEDIA_DETECTED",
                "DOWNLOAD_COMPLETED",
                "JOB_COMPLETED"
              ].includes(latestEvent)
                ? "bg-cyan-500/20 border-cyan-500/40 text-cyan-300 font-bold"
                : "bg-white/5 border-white/5 text-slate-500"
            }`}
          >
            1. Received
          </div>
          <div
            className={`p-1.5 rounded border ${
              [
                "SCRIPT_SUBMITTED",
                "AGENT_ACCEPTED",
                "GENERATION_STARTED",
                "MEDIA_DETECTED",
                "DOWNLOAD_COMPLETED",
                "JOB_COMPLETED"
              ].includes(latestEvent)
                ? "bg-indigo-500/20 border-indigo-500/40 text-indigo-300 font-bold"
                : "bg-white/5 border-white/5 text-slate-500"
            }`}
          >
            2. Submitted
          </div>
          <div
            className={`p-1.5 rounded border ${
              [
                "GENERATION_STARTED",
                "MEDIA_DETECTED",
                "DOWNLOAD_COMPLETED",
                "JOB_COMPLETED"
              ].includes(latestEvent)
                ? "bg-purple-500/20 border-purple-500/40 text-purple-300 font-bold"
                : "bg-white/5 border-white/5 text-slate-500"
            }`}
          >
            3. Generating
          </div>
          <div
            className={`p-1.5 rounded border ${
              latestEvent === "JOB_COMPLETED"
                ? "bg-emerald-500/20 border-emerald-500/40 text-emerald-300 font-bold"
                : "bg-white/5 border-white/5 text-slate-500"
            }`}
          >
            4. Downloaded
          </div>
        </div>
      </div>

      {/* Active Project & Scenes List */}
      <div className="glass-panel p-4 mb-4 border border-white/5">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-indigo-400" />
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-200">
              {activeProject ? activeProject.projectTitle || activeProject.project_title : "No Active Project"}
            </h2>
          </div>
          {activeProject && (
            <div className="flex items-center gap-2 text-xs font-mono">
              <span className="text-emerald-400 font-semibold">{completedCount} Downloaded</span>
              <span className="text-slate-500">/</span>
              <span className="text-slate-300">{activeProject.scenes.length} Scenes</span>
            </div>
          )}
        </div>

        {activeProject ? (
          <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
            {activeProject.scenes.map((scene, idx) => {
              const num = getSceneNum(scene, idx);
              const title = getSceneTitle(scene, idx);
              const prompt = getScenePrompt(scene);
              const downloadPath = getSceneDownloadPath(scene);
              const downloaded = isSceneDownloaded(scene);
              const generating = isSceneGenerating(scene);

              return (
                <div
                  key={num}
                  className="p-2.5 rounded-lg bg-white/5 border border-white/10 flex items-start justify-between gap-3"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-cyan-500/20 text-cyan-300">
                        #{String(num).padStart(2, "0")}
                      </span>
                      <span className="text-xs font-semibold text-slate-200 truncate">{title}</span>
                    </div>
                    <p className="text-[11px] text-slate-400 line-clamp-2">{prompt}</p>
                    {downloadPath && (
                      <div className="mt-1 flex items-center gap-1.5 text-[10px] font-mono text-emerald-400">
                        <Download className="w-3 h-3 shrink-0" />
                        <span className="truncate">{downloadPath}</span>
                      </div>
                    )}
                  </div>

                  <div className="pt-0.5">
                    {downloaded ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    ) : generating ? (
                      <Clock className="w-4 h-4 text-indigo-400 animate-spin shrink-0" />
                    ) : (
                      <Clock className="w-4 h-4 text-slate-500 shrink-0" />
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="py-8 text-center text-slate-500 text-xs">
            Awaiting project dispatch from Antigravity...
          </div>
        )}
      </div>

      {/* Diagnostics & Recent Errors */}
      {recentErrors.length > 0 && (
        <div className="glass-panel p-3 mb-4 border border-rose-500/30 bg-rose-950/20">
          <div className="flex items-center gap-2 mb-2 text-xs font-bold uppercase tracking-wider text-rose-300">
            <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
            <span>Failing Stage Diagnostics</span>
          </div>
          <div className="space-y-1.5 font-mono text-[11px]">
            {recentErrors.slice(0, 3).map((err, i) => (
              <div key={i} className="p-2 rounded bg-rose-900/30 border border-rose-500/20 text-rose-200">
                <div className="font-semibold text-rose-300">Stage: {err.stage || err.event}</div>
                <div className="text-rose-400 text-[10px] mt-0.5">{err.error || "Stage execution failed"}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Real-time Automation Logs */}
      <div className="glass-panel p-4 border border-white/5">
        <div className="flex items-center gap-2 mb-2 text-xs font-bold uppercase tracking-wider text-slate-300">
          <Terminal className="w-3.5 h-3.5 text-cyan-400" />
          <span>Automation Log</span>
        </div>
        <div className="bg-black/40 rounded-lg p-2.5 font-mono text-[11px] max-h-36 overflow-y-auto space-y-1 border border-white/5">
          {events.length === 0 ? (
            <div className="text-slate-600 italic">No events recorded yet.</div>
          ) : (
            events.slice(0, 15).map((ev, i) => (
              <div key={i} className="flex items-start gap-2">
                <span className="text-slate-500 shrink-0">
                  {new Date(ev.timestamp).toLocaleTimeString().slice(0, 8)}
                </span>
                <span
                  className={
                    ev.event.includes("FAIL") || ev.event.includes("UNAVAILABLE") || ev.event.includes("NOT_DETECTED")
                      ? "text-rose-400"
                      : ev.event.includes("COMPLETED")
                      ? "text-emerald-400"
                      : "text-cyan-300"
                  }
                >
                  {ev.event}
                </span>
                {ev.filename && <span className="text-slate-400 truncate">{ev.filename}</span>}
                {ev.error && <span className="text-rose-300 truncate">{ev.error}</span>}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default App;
