import React, { useState, useEffect, useRef } from "react";
import {
  VideoProject,
  Scene,
  ProductionMode,
  SceneStatus,
  DependencyGraph
} from "../../shared/video-types";
import {
  saveProject,
  getAllProjects,
  getScenesForProject,
  saveScene,
  updateScene as updateSceneDB,
  updateProject as updateProjectDB
} from "../../shared/video-db";
import { buildDependencyGraph } from "../../shared/scene-scheduler";
import {
  Clapperboard,
  Play,
  Pause,
  Square,
  CheckCircle2,
  Clock,
  XCircle,
  Sparkles,
  ChevronDown,
  ChevronUp,
  Film,
  FolderDown,
  AlertTriangle,
  Edit3,
  RefreshCw,
  GitFork,
  Check,
  Wand2,
  Layers,
  ArrowRight
} from "lucide-react";

interface Props {
  bridgeConnected: boolean;
}

const BRIDGE_URL = "http://127.0.0.1:8795";

export const VideoDirectorView: React.FC<Props> = ({ bridgeConnected }) => {
  // Projects state
  const [projects, setProjects] = useState<VideoProject[]>([]);
  const [activeProject, setActiveProject] = useState<VideoProject | null>(null);
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [depGraph, setDepGraph] = useState<DependencyGraph | null>(null);

  // Form state
  const [brief, setBrief] = useState("");
  const [title, setTitle] = useState("");
  const [mode, setMode] = useState<ProductionMode>("auto");
  const [autonomous, setAutonomous] = useState(true);
  const [isCreating, setIsCreating] = useState(false);

  // Playback & UI state
  const [isRunning, setIsRunning] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [expandedScenes, setExpandedScenes] = useState<Record<string, boolean>>({});
  const [editingSceneId, setEditingSceneId] = useState<string | null>(null);
  const [editedImagePrompt, setEditedImagePrompt] = useState("");
  const [editedVideoPrompt, setEditedVideoPrompt] = useState("");
  const [logs, setLogs] = useState<string[]>([]);
  const [activeTab, setActiveTab] = useState<"scenes" | "dependencies" | "logs">("scenes");

  const pollTimerRef = useRef<number | null>(null);

  const addLog = (msg: string) => {
    const time = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    setLogs((prev) => [`[${time}] ${msg}`, ...prev.slice(0, 99)]);
  };

  // Load existing projects on mount
  useEffect(() => {
    loadProjects();
  }, []);

  const loadProjects = async () => {
    try {
      const list = await getAllProjects();
      setProjects(list.reverse());
      if (list.length > 0 && !activeProject) {
        selectProject(list[0]);
      }
    } catch (err) {
      console.error("Failed to load director projects:", err);
    }
  };

  const selectProject = async (proj: VideoProject) => {
    setActiveProject(proj);
    try {
      const scns = await getScenesForProject(proj.id);
      setScenes(scns);
      if (scns.length > 0) {
        setDepGraph(buildDependencyGraph(scns));
      } else {
        setDepGraph(null);
      }
    } catch (err) {
      console.error("Failed to load scenes for project:", err);
    }
  };

  // Poll project status from bridge
  useEffect(() => {
    if (!activeProject || !isRunning || isPaused) {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
      return;
    }

    const poll = async () => {
      try {
        const res = await fetch(`${BRIDGE_URL}/api/director/project/${activeProject.id}/status`);
        if (res.ok) {
          const data = await res.json();
          if (data.project) {
            setActiveProject(data.project);
            await updateProjectDB(data.project.id, data.project);
          }
          if (data.scenes && data.scenes.length > 0) {
            setScenes(data.scenes);
            setDepGraph(buildDependencyGraph(data.scenes));
            for (const s of data.scenes) {
              await saveScene(s);
            }
          }
        }
      } catch (_) {}
    };

    poll();
    pollTimerRef.current = window.setInterval(poll, 3000);
    return () => {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    };
  }, [activeProject, isRunning, isPaused]);

  // Load Realistic Stickman 2D Figure Test Preset
  const handleLoadStickmanPreset = async () => {
    const stickmanTitle = "Realistic Stickman 2D — Fluid Kinematics";
    const stickmanBrief =
      "A cinematic animated short featuring a realistic stickman 2D figure with athletic anatomical proportions and fluid martial arts kinematics, drawn with graphite pencil on textured cotton paper that comes to life with ink splash physics and dramatic studio rim lighting.";

    setTitle(stickmanTitle);
    setBrief(stickmanBrief);
    setIsCreating(true);
    addLog("⚡ Loading Realistic Stickman 2D test production...");

    try {
      const pId = "proj_stickman_" + Date.now();
      const project: VideoProject = {
        id: pId,
        title: stickmanTitle,
        brief: stickmanBrief,
        productionPlan: {
          concept: "Realistic 2D stickman animated on textured drafting paper with hyper-fluid kinematics",
          storyline: "Graphite sketch comes to life, performs fluid acrobatic kata, weaves through neon ink droplets, and lands in dramatic hero stance.",
          visualStyle: "Tactile textured cotton paper, crisp 2B graphite pencil shading, cinematic studio lighting, fluid particle physics",
          colorPalette: "Monochrome graphite with neon cyan luminescence highlights",
          cameraStyle: "Macro lens close-ups, dynamic lateral tracking pans, slow-motion impact freeze",
          totalDurationSeconds: 32,
          sceneCount: 4,
          createdAt: Date.now()
        },
        mode: "auto",
        autonomousMode: true,
        status: "approved",
        sceneIds: [
          `scene_${pId}_001`,
          `scene_${pId}_002`,
          `scene_${pId}_003`,
          `scene_${pId}_004`
        ],
        downloadFolder: "GoogleFlow/Projects/Realistic_Stickman_2D",
        totalScenes: 4,
        completedScenes: 0,
        failedScenes: 0,
        createdAt: Date.now(),
        updatedAt: Date.now()
      };

      const stickmanScenes: Scene[] = [
        {
          id: `scene_${pId}_001`,
          projectId: pId,
          sceneNumber: 1,
          title: "The Sketch Awakens",
          narrativePurpose: "Establish realistic proportioned 2D stickman drawn in dark graphite pencil on cotton paper",
          description: "Extreme macro close-up of textured heavy watercolor paper. A realistically proportioned 2D stickman figure drawn in dark 2B graphite pencil comes to life and pushes off the surface.",
          durationSeconds: 8,
          imagePrompt: "Macro photograph, extreme close-up of textured heavy watercolor paper on artist desk, sharp detailed 2D stickman figure drawn in dark 2B graphite pencil with realistic athletic proportions, dramatic single light source casting realistic paper fiber shadow, 8k cinematic masterpiece",
          videoPrompt: "Slow macro tracking shot as the graphite 2D stickman drawing peels itself off the paper, bending its joints with fluid motion, subtle graphite dust floating in the rim light, 24fps cinematic motion",
          characterRefs: [],
          environmentRefs: [],
          cameraInstructions: "Extreme macro 85mm lens, shallow depth of field, slow focus pull from paper texture to character head",
          motionInstructions: "Gentle unfolding and rising motion, paper fibers flexing slightly",
          aspectRatio: "16:9",
          model: "nano-banana-pro",
          dependsOn: [],
          status: "pending",
          retryCount: 0,
          maxRetries: 3,
          createdAt: Date.now(),
          updatedAt: Date.now()
        },
        {
          id: `scene_${pId}_002`,
          projectId: pId,
          sceneNumber: 2,
          title: "Fluid Kinematic Kata",
          narrativePurpose: "Showcase realistic martial arts motion and kinematics of the 2D stickman",
          description: "The 2D stickman performs an acrobatic martial arts sequence across the drafting table, kicking graphite dust with realistic momentum.",
          durationSeconds: 8,
          imagePrompt: "Side profile action shot, athletic 2D stickman figure in mid-air flying spinning kick pose, crisp black ink lines with graphite hatching, dramatic rim light, wooden drafting desk background with architectural rulers, ultra-detailed 8k",
          videoPrompt: "High-speed camera tracking the 2D stickman performing a seamless martial arts spin kick, ink-trail motion blur ribbons trailing from its limbs, realistic motion physics and footwork impact, cinematic slow-motion",
          characterRefs: [],
          environmentRefs: [],
          cameraInstructions: "Side-scrolling tracking camera following rapid lateral movement, sudden speed ramp into 50% slow-mo",
          motionInstructions: "High-energy spin kick, rotational torque, smooth kinematic follow-through",
          aspectRatio: "16:9",
          model: "nano-banana-pro",
          dependsOn: [`scene_${pId}_001`],
          status: "pending",
          retryCount: 0,
          maxRetries: 3,
          createdAt: Date.now(),
          updatedAt: Date.now()
        },
        {
          id: `scene_${pId}_003`,
          projectId: pId,
          sceneNumber: 3,
          title: "Neon Ink Crucible",
          narrativePurpose: "Interact with glowing cyan fluid droplets on the drafting surface",
          description: "Neon cyan ink droplets fall onto the desk like meteorites; the 2D stickman parkours and vaults over the luminous fluid splashes.",
          durationSeconds: 8,
          imagePrompt: "Cinematic medium shot, athletic 2D black graphite stickman vaulting over glowing neon cyan ink droplet splashing into crowns on desk, reflected cyan luminescence illuminating stickman lines, dark atmospheric studio, 8k",
          videoPrompt: "Dynamic circular camera orbit as the 2D stickman vaults over glowing cyan ink splashes in ultra slow-motion, liquid droplets scattering with surface tension physics, cinematic lighting",
          characterRefs: [],
          environmentRefs: [],
          cameraInstructions: "360-degree rotational orbit shot around the stickman at desk level",
          motionInstructions: "Parkour vault, inverted flip, aerial tuck and roll",
          aspectRatio: "16:9",
          model: "nano-banana-pro",
          dependsOn: [`scene_${pId}_002`],
          status: "pending",
          retryCount: 0,
          maxRetries: 3,
          createdAt: Date.now(),
          updatedAt: Date.now()
        },
        {
          id: `scene_${pId}_004`,
          projectId: pId,
          sceneNumber: 4,
          title: "Heroic Impact Freeze",
          narrativePurpose: "Final heroic three-point landing with radial paper shockwave",
          description: "The stickman executes a superhero landing onto the center of the sketchbook, causing a shockwave of graphite dust and neon sparks.",
          durationSeconds: 8,
          imagePrompt: "Dramatic low-angle hero shot, realistic 2D stickman in low three-point superhero landing pose on open sketchbook, radial shockwave dust ring, dramatic top spotlight, anamorphic lens flare, award-winning cinematic still, 8k",
          videoPrompt: "Downward crane camera rushing in as the 2D stickman drops from above and slams down into three-point landing, shockwave rippling paper surface, freeze-frame ending with cinematic lens flare",
          characterRefs: [],
          environmentRefs: [],
          cameraInstructions: "Rapid vertical plunge crane down, locking abruptly into low angle hero perspective",
          motionInstructions: "High-velocity descent, ground impact with recoil vibration, stone-still hero pose",
          aspectRatio: "16:9",
          model: "nano-banana-pro",
          dependsOn: [`scene_${pId}_003`],
          status: "pending",
          retryCount: 0,
          maxRetries: 3,
          createdAt: Date.now(),
          updatedAt: Date.now()
        }
      ];

      await saveProject(project);
      for (const sc of stickmanScenes) {
        await saveScene(sc);
      }

      if (bridgeConnected) {
        await fetch(`${BRIDGE_URL}/api/director/project/create`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            title: stickmanTitle,
            brief: stickmanBrief,
            mode: "auto",
            autonomousMode: true
          })
        }).catch(() => {});

        await fetch(`${BRIDGE_URL}/api/director/storyboard/create`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            projectId: pId,
            scenes: stickmanScenes
          })
        }).catch(() => {});
      }

      await loadProjects();
      setActiveProject(project);
      setScenes(stickmanScenes);
      setDepGraph(buildDependencyGraph(stickmanScenes));
      addLog("Realistic Stickman 2D storyboard generated: 4 production scenes ready!");
    } catch (err: any) {
      addLog(`Preset error: ${err.message}`);
    } finally {
      setIsCreating(false);
    }
  };

  // Handle Project Creation from user input
  const handleCreateProject = async () => {
    if (!brief.trim()) return;
    setIsCreating(true);
    addLog(`Creating project "${title || "Untitled Project"}"...`);

    try {
      let createdProject: VideoProject;

      if (bridgeConnected) {
        const res = await fetch(`${BRIDGE_URL}/api/director/project/create`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            title: title.trim() || "Untitled Project",
            brief: brief.trim(),
            mode,
            autonomousMode: autonomous
          })
        });
        const data = await res.json();
        createdProject = data.project;
      } else {
        const pId = "proj_" + Date.now() + "_" + Math.random().toString(36).slice(2, 6);
        createdProject = {
          id: pId,
          title: title.trim() || "Untitled Project",
          brief: brief.trim(),
          productionPlan: {
            concept: brief.trim().slice(0, 100),
            storyline: brief.trim(),
            visualStyle: "Cinematic 4K",
            colorPalette: "Rich contrast with vivid studio rim lights",
            cameraStyle: "Dynamic anamorphic framing",
            totalDurationSeconds: 60,
            sceneCount: 0,
            createdAt: Date.now()
          },
          mode,
          autonomousMode: autonomous,
          status: "draft",
          sceneIds: [],
          downloadFolder: `GoogleFlow/Projects/${(title || "Project").replace(/\s+/g, "_")}`,
          totalScenes: 0,
          completedScenes: 0,
          failedScenes: 0,
          createdAt: Date.now(),
          updatedAt: Date.now()
        };
      }

      await saveProject(createdProject);
      addLog(`Project ${createdProject.id} saved! Ready for storyboard.`);
      await loadProjects();
      setActiveProject(createdProject);
      setScenes([]);
      setDepGraph(null);
      setBrief("");
      setTitle("");
    } catch (err: any) {
      addLog(`Error creating project: ${err.message}`);
    } finally {
      setIsCreating(false);
    }
  };

  // Production Controls
  const handleStartProduction = () => {
    setIsRunning(true);
    setIsPaused(false);
    addLog("▶ Production started! Autonomous scheduler active.");
  };

  const handlePauseProduction = () => {
    setIsPaused(true);
    addLog("⏸ Production paused.");
  };

  const handleResumeProduction = () => {
    setIsPaused(false);
    addLog("▶ Production resumed.");
  };

  const handleStopProduction = () => {
    setIsRunning(false);
    setIsPaused(false);
    addLog("⏹ Production stopped.");
  };

  // Scene Operations
  const handleRegenerateScene = async (sceneId: string, type: "image" | "video" | "full") => {
    addLog(`Regenerating scene ${sceneId} (${type})...`);
    try {
      if (bridgeConnected) {
        await fetch(`${BRIDGE_URL}/api/director/scene/regenerate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ sceneId, type })
        });
      }
      await updateSceneDB(sceneId, {
        status: "pending",
        error: undefined,
        ...(type === "video" ? { videoLocalPath: undefined } : { imageLocalPath: undefined, videoLocalPath: undefined })
      });
      if (activeProject) selectProject(activeProject);
    } catch (err: any) {
      addLog(`Regenerate failed: ${err.message}`);
    }
  };

  const handleApproveScene = async (sceneId: string) => {
    addLog(`Approved scene ${sceneId}.`);
    try {
      if (bridgeConnected) {
        await fetch(`${BRIDGE_URL}/api/director/scene/approve`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ sceneId })
        });
      }
      await updateSceneDB(sceneId, { status: "approved" });
      if (activeProject) selectProject(activeProject);
    } catch (err: any) {
      addLog(`Approve failed: ${err.message}`);
    }
  };

  const handleSkipScene = async (sceneId: string) => {
    addLog(`Skipped scene ${sceneId}.`);
    try {
      if (bridgeConnected) {
        await fetch(`${BRIDGE_URL}/api/director/scene/update`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ sceneId, fields: { status: "skipped" } })
        });
      }
      await updateSceneDB(sceneId, { status: "skipped" });
      if (activeProject) selectProject(activeProject);
    } catch (err: any) {
      addLog(`Skip failed: ${err.message}`);
    }
  };

  const handleSaveScenePrompt = async (sceneId: string) => {
    try {
      if (bridgeConnected) {
        await fetch(`${BRIDGE_URL}/api/director/scene/update`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            sceneId,
            fields: {
              imagePrompt: editedImagePrompt,
              videoPrompt: editedVideoPrompt
            }
          })
        });
      }
      await updateSceneDB(sceneId, {
        imagePrompt: editedImagePrompt,
        videoPrompt: editedVideoPrompt
      });
      setEditingSceneId(null);
      addLog(`Updated prompts for scene ${sceneId}`);
      if (activeProject) selectProject(activeProject);
    } catch (err: any) {
      addLog(`Prompt update failed: ${err.message}`);
    }
  };

  // Export Project Manifest & Report
  const handleExportProject = async () => {
    if (!activeProject) return;
    addLog("Exporting project package & report...");
    try {
      if (bridgeConnected) {
        const res = await fetch(`${BRIDGE_URL}/api/director/project/export`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ projectId: activeProject.id })
        });
        const data = await res.json();
        if (data.success) {
          addLog("Project report exported to Downloads folder!");
          alert("Project manifest & generation report saved!");
        } else {
          addLog(`Export failed: ${data.error}`);
        }
      } else {
        const blob = new Blob([JSON.stringify({ project: activeProject, scenes }, null, 2)], {
          type: "application/json"
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `manifest_${activeProject.id}.json`;
        a.click();
        addLog("Exported JSON manifest directly.");
      }
    } catch (err: any) {
      addLog(`Export error: ${err.message}`);
    }
  };

  // Video Assembly Pipeline
  const handleAssembleVideo = async () => {
    if (!activeProject) return;
    const completedScenes = scenes.filter((s) => s.status === "completed" || s.status === "approved");
    if (completedScenes.length === 0) {
      alert("No completed video scenes available yet for assembly.");
      return;
    }

    const fpsStr = prompt("Assemble video at what frame rate (fps)?", "24");
    const fps = parseInt(fpsStr || "24", 10) || 24;

    addLog(`Initiating local FFmpeg assembly at ${fps} fps...`);
    try {
      const res = await fetch(`${BRIDGE_URL}/api/director/project/assemble`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          projectId: activeProject.id,
          options: { fps, resolution: "1920x1080", transitions: true }
        })
      });
      const data = await res.json();
      if (data.success) {
        addLog(`Video assembled successfully: ${data.outputFile}`);
        alert(`Final movie assembled!\nPath: ${data.outputFile}`);
      } else {
        addLog(`Assembly error: ${data.error || "FFmpeg failure"}`);
        alert(`Assembly failed: ${data.error}\nEnsure ffmpeg is installed locally.`);
      }
    } catch (err: any) {
      addLog(`Assembly call failed: ${err.message}`);
    }
  };

  // Status metrics
  const total = scenes.length;
  const completed = scenes.filter((s) => s.status === "completed" || s.status === "approved").length;
  const failed = scenes.filter((s) => s.status === "failed").length;
  const inProgress = scenes.filter((s) =>
    ["generating_image", "generating_video", "downloading", "qc_check"].includes(s.status)
  ).length;
  const pct = total > 0 ? Math.round((completed / total) * 100) : 0;

  const toggleExpand = (id: string) => {
    setExpandedScenes((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const getStatusBadge = (status: SceneStatus) => {
    switch (status) {
      case "completed":
      case "approved":
        return (
          <span className="flex items-center gap-1 text-[10px] font-semibold text-emerald-300 bg-emerald-950/70 border border-emerald-500/40 px-2 py-0.5 rounded-full shadow-[0_0_8px_rgba(16,185,129,0.2)]">
            <CheckCircle2 className="w-3 h-3 text-emerald-400" /> {status}
          </span>
        );
      case "generating_image":
      case "generating_video":
        return (
          <span className="flex items-center gap-1 text-[10px] font-semibold text-amber-300 bg-amber-950/70 border border-amber-500/40 px-2 py-0.5 rounded-full animate-pulse shadow-[0_0_8px_rgba(245,158,11,0.2)]">
            <Sparkles className="w-3 h-3 text-amber-400" /> {status.replace("_", " ")}
          </span>
        );
      case "downloading":
      case "qc_check":
        return (
          <span className="flex items-center gap-1 text-[10px] font-semibold text-cyan-300 bg-cyan-950/70 border border-cyan-500/40 px-2 py-0.5 rounded-full shadow-[0_0_8px_rgba(6,182,212,0.2)]">
            <Clock className="w-3 h-3 text-cyan-400" /> {status}
          </span>
        );
      case "failed":
        return (
          <span className="flex items-center gap-1 text-[10px] font-semibold text-red-300 bg-red-950/70 border border-red-500/40 px-2 py-0.5 rounded-full shadow-[0_0_8px_rgba(239,68,68,0.2)]">
            <XCircle className="w-3 h-3 text-red-400" /> failed
          </span>
        );
      case "skipped":
        return (
          <span className="text-[10px] font-semibold text-slate-400 bg-slate-900/60 border border-slate-700/60 px-2 py-0.5 rounded-full">
            skipped
          </span>
        );
      case "waiting_deps":
        return (
          <span className="flex items-center gap-1 text-[10px] font-semibold text-indigo-300 bg-indigo-950/70 border border-indigo-500/40 px-2 py-0.5 rounded-full">
            <GitFork className="w-3 h-3 text-indigo-400" /> waiting deps
          </span>
        );
      default:
        return (
          <span className="text-[10px] font-semibold text-slate-400 bg-slate-900/80 border border-slate-800 px-2 py-0.5 rounded-full">
            pending
          </span>
        );
    }
  };

  return (
    <div className="space-y-3 text-xs">
      {/* QUICK PRESET TEST BANNER */}
      <div className="p-3 rounded-2xl glass-panel relative overflow-hidden group">
        <div className="absolute -right-6 -bottom-6 w-28 h-28 bg-gradient-to-tr from-cyan-500/20 to-purple-500/20 rounded-full blur-xl pointer-events-none group-hover:scale-125 transition-transform" />
        
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-cyan-500/30 to-indigo-500/30 border border-cyan-400/30 flex items-center justify-center text-cyan-300 shadow-md">
              <Wand2 className="w-4 h-4" />
            </div>
            <div>
              <div className="font-bold text-xs text-white flex items-center gap-1.5">
                Quick Test Preset: Realistic Stickman 2D
                <span className="text-[9px] bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 font-bold px-1.5 py-0.2 rounded-full">
                  READY
                </span>
              </div>
              <div className="text-[10px] text-slate-400">
                Instantly load 4 complete scenes with fluid physics, pencil texture & rim lights.
              </div>
            </div>
          </div>

          <button
            onClick={handleLoadStickmanPreset}
            disabled={isCreating}
            className="flex items-center gap-1 px-3 py-1.5 rounded-xl glass-btn-primary text-white font-bold text-xs whitespace-nowrap shadow-lg shrink-0"
          >
            <span>Load Test</span>
            <ArrowRight className="w-3 h-3" />
          </button>
        </div>
      </div>

      {/* TOP CREATIVE BRIEF PANEL */}
      <div className="p-3.5 rounded-2xl glass-panel space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="p-1.5 bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 rounded-lg">
              <Clapperboard className="w-4 h-4" />
            </div>
            <div>
              <div className="font-bold text-sm text-slate-100 flex items-center gap-2">
                AI Video Director
                <span className="text-[9px] bg-gradient-to-r from-indigo-500 to-purple-500 text-white font-bold px-1.5 py-0.2 rounded-full uppercase tracking-wider">
                  Autonomous
                </span>
              </div>
              <div className="text-[10px] text-slate-400">
                End-to-end multi-scene video production from a single creative instruction.
              </div>
            </div>
          </div>
        </div>

        {/* Input Area */}
        <div className="space-y-2 pt-1">
          <textarea
            value={brief}
            onChange={(e) => setBrief(e.target.value)}
            placeholder='Describe your creative vision, e.g.: "A realistic 2D stickman animated with fluid martial arts physics across textured paper with dramatic studio rim lighting."'
            rows={3}
            className="w-full glass-input rounded-xl p-2.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none transition-all resize-none leading-relaxed"
          />

          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-[10px] text-slate-400 font-semibold block mb-1">PROJECT TITLE</label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Realistic Stickman 2D"
                className="w-full glass-input rounded-xl px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none"
              />
            </div>

            <div>
              <label className="text-[10px] text-slate-400 font-semibold block mb-1">PRODUCTION MODE</label>
              <select
                value={mode}
                onChange={(e) => setMode(e.target.value as ProductionMode)}
                className="w-full glass-input rounded-xl px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none"
              >
                <option value="auto">🤖 Auto (Flow Agent / Direct)</option>
                <option value="direct">⚡ Direct Generation Mode</option>
                <option value="agent">🧠 Google Flow Agent Mode</option>
              </select>
            </div>
          </div>

          <div className="flex items-center justify-between pt-1">
            <label className="flex items-center gap-2 text-slate-300 text-[11px] cursor-pointer">
              <input
                type="checkbox"
                checked={autonomous}
                onChange={(e) => setAutonomous(e.target.checked)}
                className="rounded border-slate-700 bg-slate-950 text-indigo-500 focus:ring-0 w-3.5 h-3.5"
              />
              <span>Autonomous Mode (proceed without manual scene approvals)</span>
            </label>

            <button
              onClick={handleCreateProject}
              disabled={!brief.trim() || isCreating}
              className="flex items-center gap-1.5 glass-btn-primary disabled:opacity-40 text-white font-semibold text-xs px-3.5 py-1.5 rounded-xl transition-all shadow-md"
            >
              <Sparkles className="w-3.5 h-3.5" />
              {isCreating ? "Planning..." : "Plan Production"}
            </button>
          </div>
        </div>
      </div>

      {/* Project Selector (if multiple projects exist) */}
      {projects.length > 1 && (
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-none">
          <span className="text-[10px] uppercase font-bold text-slate-400 mr-1">Projects:</span>
          {projects.map((p) => (
            <button
              key={p.id}
              onClick={() => selectProject(p)}
              className={`px-2.5 py-1 rounded-lg text-[11px] font-medium whitespace-nowrap border transition-all ${
                activeProject?.id === p.id
                  ? "glass-card-active text-indigo-300"
                  : "glass-card text-slate-400 hover:text-slate-200"
              }`}
            >
              {p.title}
            </button>
          ))}
        </div>
      )}

      {/* ACTIVE PROJECT DASHBOARD */}
      {activeProject && (
        <div className="p-3.5 rounded-2xl glass-panel space-y-3">
          {/* Header & Controls */}
          <div className="flex items-start justify-between gap-2">
            <div>
              <div className="text-sm font-bold text-slate-100 flex items-center gap-2 flex-wrap">
                {activeProject.title}
                <span className="text-[9px] font-bold text-indigo-300 bg-indigo-950/60 border border-indigo-700/50 px-2 py-0.5 rounded-full">
                  {activeProject.mode.toUpperCase()}
                </span>
                {activeProject.autonomousMode && (
                  <span className="text-[9px] font-bold text-purple-300 bg-purple-950/60 border border-purple-700/50 px-2 py-0.5 rounded-full">
                    AUTONOMOUS
                  </span>
                )}
              </div>
              <div className="text-[11px] text-slate-400 line-clamp-1 mt-0.5 max-w-[340px]">
                {activeProject.brief}
              </div>
            </div>

            {/* Production Action Buttons */}
            <div className="flex items-center gap-1.5 shrink-0">
              {!isRunning ? (
                <button
                  onClick={handleStartProduction}
                  className="flex items-center gap-1 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold px-2.5 py-1 rounded-xl text-[11px] transition-colors shadow-lg"
                >
                  <Play className="w-3 h-3 fill-current" /> Start
                </button>
              ) : isPaused ? (
                <button
                  onClick={handleResumeProduction}
                  className="flex items-center gap-1 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold px-2.5 py-1 rounded-xl text-[11px] transition-colors shadow-lg"
                >
                  <Play className="w-3 h-3 fill-current" /> Resume
                </button>
              ) : (
                <button
                  onClick={handlePauseProduction}
                  className="flex items-center gap-1 bg-amber-600 hover:bg-amber-500 text-white font-semibold px-2.5 py-1 rounded-xl text-[11px] transition-colors shadow-lg"
                >
                  <Pause className="w-3 h-3 fill-current" /> Pause
                </button>
              )}

              {isRunning && (
                <button
                  onClick={handleStopProduction}
                  className="flex items-center gap-1 bg-red-600/80 hover:bg-red-500 text-white font-semibold px-2 py-1 rounded-xl text-[11px] transition-colors"
                >
                  <Square className="w-3 h-3 fill-current" />
                </button>
              )}
            </div>
          </div>

          {/* Progress Bar & Metric Counters */}
          <div className="space-y-1.5">
            <div className="flex justify-between text-[11px] text-slate-400">
              <span>{completed} of {total} scenes completed</span>
              <span className="font-bold text-indigo-400">{pct}%</span>
            </div>
            <div className="w-full bg-slate-950/80 rounded-full h-2 overflow-hidden border border-white/10 shadow-inner">
              <div
                className="bg-gradient-to-r from-indigo-500 via-purple-500 to-cyan-400 h-full rounded-full transition-all duration-300 shadow-[0_0_12px_rgba(99,102,241,0.5)]"
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>

          {/* Counters Grid */}
          <div className="grid grid-cols-4 gap-2 pt-1">
            <div className="glass-card p-2 rounded-xl text-center">
              <div className="text-[10px] text-slate-400 font-semibold uppercase">Done</div>
              <div className="text-sm font-bold text-emerald-400 flex items-center justify-center gap-1 mt-0.5">
                <CheckCircle2 className="w-3.5 h-3.5" /> {completed}
              </div>
            </div>
            <div className="glass-card p-2 rounded-xl text-center">
              <div className="text-[10px] text-slate-400 font-semibold uppercase">Active</div>
              <div className="text-sm font-bold text-amber-400 flex items-center justify-center gap-1 mt-0.5">
                <Sparkles className="w-3.5 h-3.5" /> {inProgress}
              </div>
            </div>
            <div className="glass-card p-2 rounded-xl text-center">
              <div className="text-[10px] text-slate-400 font-semibold uppercase">Failed</div>
              <div className="text-sm font-bold text-red-400 flex items-center justify-center gap-1 mt-0.5">
                <XCircle className="w-3.5 h-3.5" /> {failed}
              </div>
            </div>
            <div className="glass-card p-2 rounded-xl text-center">
              <div className="text-[10px] text-slate-400 font-semibold uppercase">Total</div>
              <div className="text-sm font-bold text-slate-200 mt-0.5">{total}</div>
            </div>
          </div>

          {/* Export & Assemble Actions */}
          <div className="flex items-center gap-2 pt-1">
            <button
              onClick={handleExportProject}
              className="flex-1 flex items-center justify-center gap-1.5 glass-btn-secondary text-slate-200 text-xs font-semibold py-2 rounded-xl transition-all"
            >
              <FolderDown className="w-3.5 h-3.5 text-indigo-400" /> Export Manifest
            </button>
            <button
              onClick={handleAssembleVideo}
              disabled={completed === 0}
              className="flex-1 flex items-center justify-center gap-1.5 glass-btn-primary disabled:opacity-40 text-white text-xs font-bold py-2 rounded-xl transition-all shadow-md"
            >
              <Film className="w-3.5 h-3.5 text-white" /> Assemble Movie (FFmpeg)
            </button>
          </div>

          {/* Sub Navigation */}
          <div className="flex border-b border-white/10 gap-4 pt-2">
            <button
              onClick={() => setActiveTab("scenes")}
              className={`pb-1 text-xs font-semibold transition-colors ${
                activeTab === "scenes"
                  ? "text-cyan-400 border-b-2 border-cyan-400"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Scenes ({scenes.length})
            </button>
            <button
              onClick={() => setActiveTab("dependencies")}
              className={`pb-1 text-xs font-semibold transition-colors ${
                activeTab === "dependencies"
                  ? "text-cyan-400 border-b-2 border-cyan-400"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Dependency Graph
            </button>
            <button
              onClick={() => setActiveTab("logs")}
              className={`pb-1 text-xs font-semibold transition-colors ${
                activeTab === "logs"
                  ? "text-cyan-400 border-b-2 border-cyan-400"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Log ({logs.length})
            </button>
          </div>

          {/* TAB 1: SCENES LIST */}
          {activeTab === "scenes" && (
            <div className="space-y-2 pt-1">
              {scenes.length === 0 ? (
                <div className="text-center py-6 text-slate-400 glass-card rounded-2xl border border-white/10 space-y-2">
                  <Film className="w-8 h-8 mx-auto text-slate-500" />
                  <p className="font-semibold text-slate-300">No scenes planned yet</p>
                  <p className="text-[11px] max-w-xs mx-auto text-slate-400">
                    Click <strong className="text-cyan-300">"Load Test"</strong> above to test the Realistic Stickman 2D figure, or ask Antigravity to generate the storyboard.
                  </p>
                </div>
              ) : (
                scenes.map((scene) => {
                  const isExpanded = !!expandedScenes[scene.id];
                  const isEditing = editingSceneId === scene.id;

                  return (
                    <div
                      key={scene.id}
                      className="glass-card rounded-xl overflow-hidden transition-all duration-200"
                    >
                      {/* Scene Card Header */}
                      <div
                        onClick={() => toggleExpand(scene.id)}
                        className="flex items-center justify-between p-2.5 cursor-pointer hover:bg-white/5 select-none"
                      >
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-[10px] font-bold text-slate-300 bg-white/10 border border-white/10 px-1.5 py-0.5 rounded">
                            {String(scene.sceneNumber).padStart(3, "0")}
                          </span>
                          <div>
                            <div className="font-semibold text-slate-100 text-xs">{scene.title}</div>
                            <div className="text-[10px] text-slate-400 flex items-center gap-2 mt-0.5">
                              <span>{scene.durationSeconds}s</span>
                              <span>•</span>
                              <span>{scene.aspectRatio}</span>
                              {scene.dependsOn && scene.dependsOn.length > 0 && (
                                <>
                                  <span>•</span>
                                  <span className="text-cyan-400 font-mono">
                                    dep: {scene.dependsOn.join(", ")}
                                  </span>
                                </>
                              )}
                            </div>
                          </div>
                        </div>

                        <div className="flex items-center gap-2">
                          {getStatusBadge(scene.status)}
                          {isExpanded ? (
                            <ChevronUp className="w-3.5 h-3.5 text-slate-400" />
                          ) : (
                            <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
                          )}
                        </div>
                      </div>

                      {/* Scene Details Expanded */}
                      {isExpanded && (
                        <div className="p-3 border-t border-white/10 bg-black/20 space-y-2.5 text-[11px]">
                          {/* Narrative purpose */}
                          {scene.narrativePurpose && (
                            <div className="text-slate-300 italic glass-input p-2 rounded-lg leading-relaxed">
                              "{scene.narrativePurpose}"
                            </div>
                          )}

                          {/* Image and Video Prompts */}
                          {isEditing ? (
                            <div className="space-y-2">
                              <div>
                                <label className="text-[10px] font-bold text-indigo-400 uppercase block mb-1">
                                  Image Prompt
                                </label>
                                <textarea
                                  value={editedImagePrompt}
                                  onChange={(e) => setEditedImagePrompt(e.target.value)}
                                  rows={2}
                                  className="w-full glass-input rounded-lg p-2 text-slate-200"
                                />
                              </div>
                              <div>
                                <label className="text-[10px] font-bold text-purple-400 uppercase block mb-1">
                                  Video Prompt
                                </label>
                                <textarea
                                  value={editedVideoPrompt}
                                  onChange={(e) => setEditedVideoPrompt(e.target.value)}
                                  rows={2}
                                  className="w-full glass-input rounded-lg p-2 text-slate-200"
                                />
                              </div>
                              <div className="flex gap-1.5">
                                <button
                                  onClick={() => handleSaveScenePrompt(scene.id)}
                                  className="px-2.5 py-1 glass-btn-primary text-white rounded-lg text-[10px] font-semibold"
                                >
                                  Save Prompts
                                </button>
                                <button
                                  onClick={() => setEditingSceneId(null)}
                                  className="px-2 py-1 glass-btn-secondary text-slate-300 rounded-lg text-[10px]"
                                >
                                  Cancel
                                </button>
                              </div>
                            </div>
                          ) : (
                            <div className="space-y-1.5">
                              <div>
                                <span className="text-[10px] font-bold text-indigo-400 uppercase mr-1">Image:</span>
                                <span className="text-slate-300 leading-relaxed">{scene.imagePrompt}</span>
                              </div>
                              <div>
                                <span className="text-[10px] font-bold text-purple-400 uppercase mr-1">Video:</span>
                                <span className="text-slate-300 leading-relaxed">{scene.videoPrompt}</span>
                              </div>
                              {scene.cameraInstructions && (
                                <div className="text-slate-400 text-[10px]">
                                  <span className="font-bold uppercase text-slate-500 mr-1">Camera:</span>
                                  {scene.cameraInstructions}
                                </div>
                              )}
                            </div>
                          )}

                          {/* Output Paths */}
                          <div className="space-y-1 pt-1 font-mono text-[10px]">
                            {scene.imageLocalPath && (
                              <div className="flex items-center gap-1.5 text-emerald-400 glass-input p-1.5 rounded">
                                <Check className="w-3 h-3" /> Image: {scene.imageLocalPath}
                              </div>
                            )}
                            {scene.videoLocalPath && (
                              <div className="flex items-center gap-1.5 text-emerald-400 glass-input p-1.5 rounded">
                                <Check className="w-3 h-3" /> Video: {scene.videoLocalPath}
                              </div>
                            )}
                            {scene.error && (
                              <div className="flex items-center gap-1.5 text-red-400 bg-red-950/40 p-1.5 rounded border border-red-800/40">
                                <AlertTriangle className="w-3 h-3" /> Error: {scene.error}
                              </div>
                            )}
                          </div>

                          {/* Action Buttons */}
                          <div className="flex items-center gap-1.5 pt-1.5 border-t border-white/10 flex-wrap">
                            <button
                              onClick={() => {
                                setEditingSceneId(scene.id);
                                setEditedImagePrompt(scene.imagePrompt);
                                setEditedVideoPrompt(scene.videoPrompt);
                              }}
                              className="px-2 py-1 glass-btn-secondary text-slate-300 rounded-lg text-[10px] flex items-center gap-1"
                            >
                              <Edit3 className="w-3 h-3" /> Edit
                            </button>
                            <button
                              onClick={() => handleRegenerateScene(scene.id, "image")}
                              className="px-2 py-1 glass-btn-secondary text-slate-300 rounded-lg text-[10px] flex items-center gap-1"
                            >
                              <RefreshCw className="w-3 h-3" /> Regen Image
                            </button>
                            <button
                              onClick={() => handleRegenerateScene(scene.id, "video")}
                              className="px-2 py-1 glass-btn-secondary text-slate-300 rounded-lg text-[10px] flex items-center gap-1"
                            >
                              <RefreshCw className="w-3 h-3" /> Regen Video
                            </button>
                            <button
                              onClick={() => handleApproveScene(scene.id)}
                              className="px-2.5 py-1 bg-emerald-950/80 hover:bg-emerald-900 text-emerald-300 border border-emerald-700/60 rounded-lg text-[10px] font-semibold flex items-center gap-1 shadow-sm"
                            >
                              <CheckCircle2 className="w-3 h-3" /> Approve
                            </button>
                            <button
                              onClick={() => handleSkipScene(scene.id)}
                              className="px-2 py-1 glass-btn-secondary text-slate-400 rounded-lg text-[10px]"
                            >
                              Skip
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          )}

          {/* TAB 2: DEPENDENCY GRAPH */}
          {activeTab === "dependencies" && (
            <div className="space-y-3 pt-1">
              {depGraph ? (
                <div className="space-y-3">
                  <div className="glass-card p-3 rounded-xl space-y-2">
                    <div className="font-bold text-slate-200 text-xs flex items-center gap-1.5">
                      <GitFork className="w-3.5 h-3.5 text-indigo-400" /> Execution Order (Topological)
                    </div>
                    <div className="flex items-center gap-1.5 flex-wrap">
                      {depGraph.executionOrder.map((id, idx) => {
                        const sc = scenes.find((s) => s.id === id);
                        return (
                          <div key={id} className="flex items-center gap-1">
                            <span className="font-mono text-[10px] bg-slate-900/80 border border-white/10 px-2 py-0.5 rounded text-cyan-300">
                              Scene {sc ? String(sc.sceneNumber).padStart(3, "0") : id}
                            </span>
                            {idx < depGraph.executionOrder.length - 1 && (
                              <span className="text-slate-500">→</span>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  <div className="glass-card p-3 rounded-xl space-y-2">
                    <div className="font-bold text-slate-200 text-xs">Concurrent Execution Batches</div>
                    <div className="space-y-1.5">
                      {depGraph.concurrentGroups.map((group, grpIdx) => (
                        <div key={grpIdx} className="flex items-center gap-2 text-[10px]">
                          <span className="font-bold text-slate-400 uppercase">Stage {grpIdx + 1}:</span>
                          <div className="flex gap-1 flex-wrap">
                            {group.map((id) => {
                              const sc = scenes.find((s) => s.id === id);
                              return (
                                <span
                                  key={id}
                                  className="glass-input text-cyan-300 px-2 py-0.5 rounded font-mono"
                                >
                                  {sc?.title || id}
                                </span>
                              );
                            })}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-slate-400 text-center py-4">No dependency edges defined yet.</div>
              )}
            </div>
          )}

          {/* TAB 3: PRODUCTION LOGS */}
          {activeTab === "logs" && (
            <div className="glass-card rounded-xl p-3 font-mono text-[10px] max-h-52 overflow-y-auto space-y-1 text-slate-300">
              {logs.length === 0 ? (
                <div>Awaiting production commands...</div>
              ) : (
                logs.map((line, idx) => <div key={idx}>{line}</div>)
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
