export type JobStatus =
  | "pending"
  | "preparing"
  | "submitting"
  | "generating"
  | "downloading"
  | "completed"
  | "failed"
  | "paused"
  | "cancelled";

export type GenerationType =
  | "text-to-image"
  | "image-to-image"
  | "text-to-video"
  | "image-to-video"
  | "frames-to-video";

export type AspectRatio = "16:9" | "1:1" | "9:16" | "4:3";

export interface Job {
  id: string;
  batchId?: string;
  prompt: string;
  resolvedPrompt: string;
  type: GenerationType;
  status: JobStatus;
  aspectRatio: AspectRatio;
  model?: string;
  duration?: number;
  outputs: number;
  referenceImages?: string[];
  characterIds?: string[];
  customFolder?: string;
  mediaUrl?: string;
  downloadPath?: string;
  downloadId?: number;
  createdAt: number;
  updatedAt: number;
  retryCount: number;
  maxRetries: number;
  error?: string;
  source: "ui" | "batch" | "agent";
}

export interface Batch {
  id: string;
  name: string;
  totalJobs: number;
  completedJobs: number;
  failedJobs: number;
  status: "idle" | "running" | "paused" | "completed" | "cancelled";
  createdAt: number;
  delayBetweenJobs: number; // in seconds
}

export interface Character {
  id: string;
  name: string;
  trigger: string; // e.g., "@Alex" or "Alex"
  description: string;
  referenceImages: string[];
  createdAt: number;
}

export interface PromptItem {
  id: string;
  title: string;
  prompt: string;
  category: string;
  tags: string[];
  type: GenerationType;
  settings?: {
    aspectRatio?: AspectRatio;
    model?: string;
    duration?: number;
  };
  favorite: boolean;
  createdAt: number;
}

export interface AssetItem {
  id: string;
  jobId: string;
  prompt: string;
  url: string;
  localPath: string;
  mediaType: "image" | "video";
  fileSize?: number;
  dimensions?: string;
  createdAt: number;
}

export interface Settings {
  downloadFolder: string;
  autoDownload: boolean;
  defaultAspectRatio: AspectRatio;
  defaultImageModel: string;
  defaultVideoModel: string;
  defaultDelaySeconds: number;
  maxRetries: number;
  unusualActivityCooldown: number;
  agentBridgePort: number;
  agentBridgeToken: string;
  theme: "dark" | "system";
  notifications: boolean;
}

export interface LogEntry {
  id: string;
  timestamp: number;
  level: "info" | "warn" | "error" | "debug";
  message: string;
  context?: Record<string, unknown>;
}

export interface FlowStatus {
  connected: boolean;
  inProject: boolean;
  tabId?: number;
  url?: string;
  isGenerating: boolean;
  isCooldown: boolean;
  cooldownSeconds: number;
  activeJob?: Job | null;
}
