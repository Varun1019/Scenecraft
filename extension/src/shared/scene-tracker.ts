/**
 * Flow Connect 2.0 - Smart Scene Tracking and Manifest System
 * Tracks scenes independently, supports out-of-order generation,
 * validates media matching, and flags ambiguous outputs.
 */

export type GenerationStatus = "pending" | "submitting" | "generating" | "completed" | "failed";
export type DownloadStatus = "pending" | "downloading" | "downloaded" | "failed" | "unassigned";

export interface TrackedScene {
  projectId: string;
  sceneId: string;
  sceneNumber: number;
  sceneTitle: string;
  expectedOutput: "image" | "video" | "any";
  generationStatus: GenerationStatus;
  downloadStatus: DownloadStatus;
  actualOutputFilename: string;
  imagePrompt?: string;
  videoPrompt?: string;
  downloadId?: number;
  mediaUrl?: string;
  error?: string;
  matchedConfidence?: number;
  flagged?: boolean;
  flagReason?: string;
  submittedAt?: number;
  completedAt?: number;
}

export interface TrackedProject {
  projectId: string;
  projectTitle: string;
  fullScript: string;
  scenes: TrackedScene[];
  status: "queued" | "dispatched" | "processing" | "completed" | "failed";
  createdAt: number;
  updatedAt: number;
  completedAt?: number;
  error?: string;
  unassignedOutputs: Array<{
    url: string;
    filename: string;
    timestamp: number;
    reason: string;
  }>;
}

export interface MatchResult {
  matched: boolean;
  scene?: TrackedScene;
  confidence: number;
  flagged?: boolean;
  reason?: string;
  filename: string;
}

export class SceneTracker {
  private project: TrackedProject;

  constructor(payload: any) {
    this.project = this.normalizeProject(payload);
  }

  private sanitizeName(name: string): string {
    return (name || "untitled").replace(/[^a-zA-Z0-9_-]/g, "_").replace(/_+/g, "_").slice(0, 50);
  }

  private detectExtension(url: string, defaultExt: string = "png"): string {
    if (!url) return defaultExt;
    const cleanUrl = url.split("?")[0].toLowerCase();
    if (cleanUrl.endsWith(".mp4") || cleanUrl.includes("/video/")) return "mp4";
    if (cleanUrl.endsWith(".webm")) return "webm";
    if (cleanUrl.endsWith(".jpg") || cleanUrl.endsWith(".jpeg")) return "jpg";
    if (cleanUrl.endsWith(".webp")) return "webp";
    if (cleanUrl.endsWith(".png") || cleanUrl.includes("/image/")) return "png";
    return defaultExt;
  }

  public normalizeProject(payload: any): TrackedProject {
    const projectId = payload.project_id || payload.projectId || `proj_${Date.now()}`;
    const projectTitle = this.sanitizeName(payload.project_title || payload.title || payload.projectTitle || "Project");
    const fullScript = payload.full_script || payload.fullScript || "";
    const rawScenes = Array.isArray(payload.scenes) ? payload.scenes : [];

    const scenes: TrackedScene[] = rawScenes.map((s: any, idx: number) => {
      const sceneNum = Number(s.scene_number || s.sceneNumber || idx + 1);
      const sceneId = s.scene_id || s.sceneId || `scene_${projectId}_${String(sceneNum).padStart(3, "0")}`;
      const sceneTitle = this.sanitizeName(s.scene_title || s.title || s.sceneTitle || `Scene_${sceneNum}`);
      const isVideo = Boolean(s.video_prompt || s.videoPrompt) && !s.image_prompt && !s.imagePrompt;
      const ext = isVideo ? "mp4" : "png";
      const padNum = String(sceneNum).padStart(2, "0");
      const filename = `Generated/${projectTitle}/${padNum}_${sceneTitle}.${ext}`;

      return {
        projectId,
        sceneId,
        sceneNumber: sceneNum,
        sceneTitle,
        expectedOutput: isVideo ? "video" : "image",
        generationStatus: (s.generationStatus || s.status || "pending") as GenerationStatus,
        downloadStatus: (s.downloadStatus || "pending") as DownloadStatus,
        actualOutputFilename: filename,
        imagePrompt: s.image_prompt || s.imagePrompt || "",
        videoPrompt: s.video_prompt || s.videoPrompt || "",
        downloadId: s.downloadId,
        mediaUrl: s.mediaUrl,
        error: s.error,
        submittedAt: s.submittedAt,
        completedAt: s.completedAt
      };
    });

    return {
      projectId,
      projectTitle,
      fullScript,
      scenes,
      status: payload.status || "processing",
      createdAt: payload.createdAt || Date.now(),
      updatedAt: Date.now(),
      unassignedOutputs: payload.unassignedOutputs || []
    };
  }

  public getProject(): TrackedProject {
    return this.project;
  }

  public getScene(sceneNumberOrId: number | string): TrackedScene | undefined {
    if (typeof sceneNumberOrId === "number") {
      return this.project.scenes.find((s) => s.sceneNumber === sceneNumberOrId);
    }
    return this.project.scenes.find((s) => s.sceneId === sceneNumberOrId);
  }

  public markSceneSubmitting(sceneNumber: number) {
    const scene = this.getScene(sceneNumber);
    if (scene) {
      scene.generationStatus = "submitting";
      scene.submittedAt = Date.now();
      this.project.updatedAt = Date.now();
    }
  }

  public markSceneGenerating(sceneNumber: number) {
    const scene = this.getScene(sceneNumber);
    if (scene) {
      scene.generationStatus = "generating";
      this.project.updatedAt = Date.now();
    }
  }

  /**
   * Intelligently matches incoming media to a scene.
   * Handles out-of-order generations, explicit scene cues, and prompt keyword overlap.
   * Flags ambiguous outputs to prevent incorrect filename attribution.
   */
  public matchMediaToScene(
    mediaUrl: string,
    metadata?: {
      promptSnippet?: string;
      sceneNumberHint?: number;
      cardIndex?: number;
      mimeType?: string;
      explicitSceneId?: string;
    }
  ): MatchResult {
    const ext = this.detectExtension(mediaUrl);

    // 1. Explicit scene ID match
    if (metadata?.explicitSceneId) {
      const scene = this.project.scenes.find((s) => s.sceneId === metadata.explicitSceneId);
      if (scene) {
        scene.mediaUrl = mediaUrl;
        scene.generationStatus = "completed";
        scene.downloadStatus = "downloading";
        scene.matchedConfidence = 1.0;
        return {
          matched: true,
          scene,
          confidence: 1.0,
          filename: scene.actualOutputFilename
        };
      }
    }

    // 2. Explicit scene number hint
    if (metadata?.sceneNumberHint) {
      const scene = this.getScene(metadata.sceneNumberHint);
      if (scene && scene.downloadStatus !== "downloaded") {
        scene.mediaUrl = mediaUrl;
        scene.generationStatus = "completed";
        scene.downloadStatus = "downloading";
        scene.matchedConfidence = 0.95;
        return {
          matched: true,
          scene,
          confidence: 0.95,
          filename: scene.actualOutputFilename
        };
      }
    }

    // 3. Prompt semantic/keyword overlap matching
    if (metadata?.promptSnippet && metadata.promptSnippet.trim().length > 3) {
      const snippet = metadata.promptSnippet.toLowerCase();
      let bestScene: TrackedScene | null = null;
      let highestScore = 0;

      for (const scene of this.project.scenes) {
        if (scene.downloadStatus === "downloaded") continue;
        const targetText = `${scene.sceneTitle} ${scene.imagePrompt} ${scene.videoPrompt}`.toLowerCase();
        const score = this.calculateOverlapScore(snippet, targetText);
        if (score > highestScore) {
          highestScore = score;
          bestScene = scene;
        }
      }

      // Require at least 0.35 keyword overlap for confidence
      if (bestScene && highestScore >= 0.35) {
        bestScene.mediaUrl = mediaUrl;
        bestScene.generationStatus = "completed";
        bestScene.downloadStatus = "downloading";
        bestScene.matchedConfidence = highestScore;
        return {
          matched: true,
          scene: bestScene,
          confidence: highestScore,
          filename: bestScene.actualOutputFilename
        };
      }
    }

    // 4. Card Index match (if generated in canvas sequence)
    if (typeof metadata?.cardIndex === "number" && metadata.cardIndex < this.project.scenes.length) {
      const candidate = this.project.scenes[metadata.cardIndex];
      if (candidate && candidate.downloadStatus !== "downloaded") {
        candidate.mediaUrl = mediaUrl;
        candidate.generationStatus = "completed";
        candidate.downloadStatus = "downloading";
        candidate.matchedConfidence = 0.75;
        return {
          matched: true,
          scene: candidate,
          confidence: 0.75,
          filename: candidate.actualOutputFilename
        };
      }
    }

    // 5. In-flight single scene match (next pending/generating scene)
    const pendingScenes = this.project.scenes.filter((s) => s.downloadStatus !== "downloaded");
    const generatingScene = pendingScenes.find((s) => s.generationStatus === "generating") || pendingScenes[0];

    if (generatingScene && pendingScenes.length === 1) {
      generatingScene.mediaUrl = mediaUrl;
      generatingScene.generationStatus = "completed";
      generatingScene.downloadStatus = "downloading";
      generatingScene.matchedConfidence = 0.8;
      return {
        matched: true,
        scene: generatingScene,
        confidence: 0.8,
        filename: generatingScene.actualOutputFilename
      };
    } else if (generatingScene && generatingScene.generationStatus === "generating") {
      // In sequential mode, the currently generating scene gets first attribution
      generatingScene.mediaUrl = mediaUrl;
      generatingScene.generationStatus = "completed";
      generatingScene.downloadStatus = "downloading";
      generatingScene.matchedConfidence = 0.7;
      return {
        matched: true,
        scene: generatingScene,
        confidence: 0.7,
        filename: generatingScene.actualOutputFilename
      };
    }

    // 6. Ambiguous / Unmatched media: FLAG IT instead of misassigning!
    const timestamp = Date.now();
    const fallbackFilename = `Generated/${this.project.projectTitle}/_unassigned/unmatched_${timestamp}.${ext}`;
    this.project.unassignedOutputs.push({
      url: mediaUrl,
      filename: fallbackFilename,
      timestamp,
      reason: "Could not confidently match media to any pending scene"
    });

    return {
      matched: false,
      flagged: true,
      confidence: 0,
      reason: "Low confidence match: Media saved to _unassigned folder without overwriting scene files",
      filename: fallbackFilename
    };
  }

  private calculateOverlapScore(needle: string, haystack: string): number {
    const cleanWords = (text: string) =>
      text
        .replace(/[^a-z0-9\s]/gi, " ")
        .split(/\s+/)
        .filter((w) => w.length > 3);

    const needleWords = new Set(cleanWords(needle));
    if (needleWords.size === 0) return 0;

    const haystackWords = new Set(cleanWords(haystack));
    let matchCount = 0;
    for (const w of needleWords) {
      if (haystackWords.has(w)) matchCount++;
    }

    return matchCount / needleWords.size;
  }

  public markSceneDownloaded(sceneNumber: number, downloadId?: number, actualPath?: string) {
    const scene = this.getScene(sceneNumber);
    if (scene) {
      scene.downloadStatus = "downloaded";
      scene.generationStatus = "completed";
      scene.completedAt = Date.now();
      if (downloadId) scene.downloadId = downloadId;
      if (actualPath) scene.actualOutputFilename = actualPath;
      this.project.updatedAt = Date.now();

      if (this.isAllScenesDownloaded()) {
        this.project.status = "completed";
        this.project.completedAt = Date.now();
      }
    }
  }

  public markSceneFailed(sceneNumber: number, error: string) {
    const scene = this.getScene(sceneNumber);
    if (scene) {
      scene.generationStatus = "failed";
      scene.downloadStatus = "failed";
      scene.error = error;
      this.project.updatedAt = Date.now();
    }
  }

  public isAllScenesDownloaded(): boolean {
    return (
      this.project.scenes.length > 0 &&
      this.project.scenes.every((s) => s.downloadStatus === "downloaded")
    );
  }

  public getCompletedCount(): number {
    return this.project.scenes.filter((s) => s.downloadStatus === "downloaded").length;
  }

  public generateManifest(): Record<string, any> {
    return {
      projectId: this.project.projectId,
      projectTitle: this.project.projectTitle,
      status: this.project.status,
      totalScenes: this.project.scenes.length,
      completedScenes: this.getCompletedCount(),
      createdAt: this.project.createdAt,
      updatedAt: this.project.updatedAt,
      completedAt: this.project.completedAt,
      scenes: this.project.scenes.map((s) => ({
        sceneId: s.sceneId,
        sceneNumber: s.sceneNumber,
        sceneTitle: s.sceneTitle,
        expectedOutput: s.expectedOutput,
        generationStatus: s.generationStatus,
        downloadStatus: s.downloadStatus,
        filename: s.actualOutputFilename,
        mediaUrl: s.mediaUrl,
        imagePrompt: s.imagePrompt,
        videoPrompt: s.videoPrompt,
        completedAt: s.completedAt,
        error: s.error
      })),
      unassignedOutputs: this.project.unassignedOutputs
    };
  }
}
