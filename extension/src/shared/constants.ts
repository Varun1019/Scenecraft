import { Settings } from "./types";

export const DEFAULT_SETTINGS: Settings = {
  downloadFolder: "GoogleFlow",
  autoDownload: true,
  defaultAspectRatio: "16:9",
  defaultImageModel: "nano-banana-pro",
  defaultVideoModel: "veo-3.1-quality",
  defaultDelaySeconds: 5,
  maxRetries: 3,
  unusualActivityCooldown: 120, // 2 minutes
  agentBridgePort: 8795,
  agentBridgeToken: "",
  theme: "dark",
  notifications: true
};

export const IMAGE_MODELS = [
  { id: "nano-banana-pro", name: "Nano Banana Pro (Best Quality, 2K Support)", maxImages: 4 },
  { id: "nano-banana-2", name: "Nano Banana 2 (Balanced)", maxImages: 4 },
  { id: "nano-banana-lite", name: "Nano Banana Lite (Fastest)", maxImages: 4 }
];

export const VIDEO_MODELS = [
  { id: "veo-3.1-quality", name: "Veo 3.1 Quality (1080p, Cinematic)", durations: [4, 8] },
  { id: "veo-3.1-fast", name: "Veo 3.1 Fast (720p, High Speed)", durations: [4, 8] },
  { id: "omni-flash", name: "Omni Flash Video", durations: [4] }
];

export const ASPECT_RATIOS = [
  { id: "16:9", label: "16:9 Landscape" },
  { id: "1:1", label: "1:1 Square" },
  { id: "9:16", label: "9:16 Portrait" },
  { id: "4:3", label: "4:3 Classic" }
];
