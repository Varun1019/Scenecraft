import { AspectRatio } from "./types";

export type ProjectStatus =
  | "draft"
  | "approved"
  | "running"
  | "paused"
  | "completed"
  | "failed";

export type SceneStatus =
  | "pending"
  | "waiting_deps"
  | "generating_image"
  | "generating_video"
  | "downloading"
  | "qc_check"
  | "completed"
  | "failed"
  | "skipped"
  | "approved";

export type ProductionMode = "agent" | "direct" | "auto";

export type AssetRole =
  | "character"
  | "vehicle"
  | "environment"
  | "lighting"
  | "style"
  | "scene_image"
  | "scene_video";

export interface ProductionPlan {
  concept: string;
  storyline: string;
  visualStyle: string;
  colorPalette: string;
  cameraStyle: string;
  totalDurationSeconds: number;
  sceneCount: number;
  createdAt: number;
}

export interface SceneAssetRef {
  assetId: string;
  role: AssetRole;
  name: string;
}

export interface Scene {
  id: string;               // "scene_{projectId}_{padded_number}"
  projectId: string;
  sceneNumber: number;      // 1-based
  title: string;
  narrativePurpose: string;
  description: string;
  durationSeconds: number;
  imagePrompt: string;
  videoPrompt: string;
  characterRefs: string[];  // asset IDs
  environmentRefs: string[];
  cameraInstructions: string;
  motionInstructions: string;
  aspectRatio: AspectRatio;
  model: string;
  dependsOn: string[];      // scene IDs
  status: SceneStatus;
  imageJobId?: string;
  videoJobId?: string;
  imageAssetId?: string;
  videoAssetId?: string;
  imageLocalPath?: string;
  videoLocalPath?: string;
  qcPassed?: boolean;
  qcNotes?: string;
  retryCount: number;
  maxRetries: number;
  error?: string;
  createdAt: number;
  updatedAt: number;
}

export interface VideoProject {
  id: string;               // "proj_{timestamp}_{random}"
  title: string;
  brief: string;
  productionPlan: ProductionPlan;
  mode: ProductionMode;
  autonomousMode: boolean;
  status: ProjectStatus;
  sceneIds: string[];
  downloadFolder: string;   // relative, e.g. "GoogleFlow/Projects/Futuristic_Tokyo"
  totalScenes: number;
  completedScenes: number;
  failedScenes: number;
  createdAt: number;
  updatedAt: number;
}

export interface VideoAsset {
  id: string;               // "vasset_{timestamp}_{random}"
  projectId: string;
  sceneId?: string;
  role: AssetRole;
  name: string;
  localPath: string;        // relative to downloads folder
  url?: string;
  fileSize?: number;
  mediaType: "image" | "video";
  createdAt: number;
}

export interface DependencyGraph {
  nodes: { id: string; sceneNumber: number; title: string; status: SceneStatus }[];
  edges: { from: string; to: string }[];
  executionOrder: string[]; // topologically sorted scene IDs
  concurrentGroups: string[][]; // groups of scenes that can run in parallel
}

export interface QCResult {
  sceneId: string;
  passed: boolean;
  checks: {
    hasImage: boolean;
    hasVideo: boolean;
    imageNonZero: boolean;
    videoNonZero: boolean;
    correctScene: boolean;
    noDuplicates: boolean;
  };
  notes: string;
}

export interface GenerationReport {
  projectId: string;
  projectTitle: string;
  generatedAt: number;
  totalScenes: number;
  completedScenes: number;
  failedScenes: number;
  skippedScenes: number;
  totalDurationSeconds: number;
  scenes: {
    sceneNumber: number;
    title: string;
    status: SceneStatus;
    imageLocalPath?: string;
    videoLocalPath?: string;
    qcPassed?: boolean;
    error?: string;
  }[];
}

export interface AssemblyOptions {
  fps: number;              // default 24
  resolution: string;       // default "1920x1080"
  musicPath?: string;       // user-supplied background music
  voiceoverPath?: string;
  subtitlesPath?: string;
  transitions: boolean;     // add crossfade between clips
  outputFilename?: string;
}
