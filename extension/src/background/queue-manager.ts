import { Job, JobStatus } from "../shared/types";
import {
  saveJob,
  getJob,
  getJobsByStatus,
  getAllJobs,
  getAllCharacters,
  getSettings,
  addLog
} from "../shared/db";
import { matchCharacters } from "../shared/character-matcher";
import { DownloadService } from "./download-service";

export class QueueManager {
  private isProcessing = false;
  private isPaused = false;
  private activeJob: Job | null = null;
  private downloadService = new DownloadService();
  private listeners: Array<() => void> = [];

  constructor() {
    this.recoverInterruptedJobs();
  }

  subscribe(listener: () => void): () => void {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter((l) => l !== listener);
    };
  }

  private notify() {
    this.listeners.forEach((l) => {
      try {
        l();
      } catch (_) {}
    });
  }

  async recoverInterruptedJobs(): Promise<void> {
    try {
      const all = await getAllJobs();
      for (const job of all) {
        if (job.status === "preparing" || job.status === "submitting") {
          job.status = "pending";
          job.updatedAt = Date.now();
          await saveJob(job);
        } else if (job.status === "generating") {
          // If browser restarted during generation, mark failed so user can choose to retry
          job.status = "failed";
          job.error = "Interrupted by browser or extension reload";
          job.updatedAt = Date.now();
          await saveJob(job);
        }
      }
      this.notify();
    } catch (err) {
      console.error("[QueueManager] Recovery error:", err);
    }
  }

  getActiveJob(): Job | null {
    return this.activeJob;
  }

  async addJob(job: Job): Promise<void> {
    job.status = "pending";
    job.createdAt = Date.now();
    job.updatedAt = Date.now();
    await saveJob(job);
    await addLog("info", `Enqueued job: ${job.prompt.slice(0, 30)}...`, { jobId: job.id });
    this.notify();

    if (!this.isPaused && !this.isProcessing) {
      this.processNext();
    }
  }

  async pause(): Promise<void> {
    this.isPaused = true;
    await addLog("info", "Queue paused by user");
    this.notify();
  }

  async resume(): Promise<void> {
    this.isPaused = false;
    await addLog("info", "Queue resumed");
    this.notify();
    this.processNext();
  }

  async cancelJob(id: string): Promise<void> {
    const job = await getJob(id);
    if (!job) return;

    job.status = "cancelled";
    job.updatedAt = Date.now();
    await saveJob(job);

    if (this.activeJob?.id === id) {
      this.activeJob = null;
    }

    await addLog("warn", `Cancelled job ${id}`);
    this.notify();
  }

  async retryJob(id: string): Promise<void> {
    const job = await getJob(id);
    if (!job) return;

    job.status = "pending";
    job.retryCount = 0;
    job.error = undefined;
    job.updatedAt = Date.now();
    await saveJob(job);
    await addLog("info", `Retrying job ${id}`);
    this.notify();

    if (!this.isPaused && !this.isProcessing) {
      this.processNext();
    }
  }

  async handleMediaIntercepted(mediaUrl: string): Promise<void> {
    if (!this.activeJob) return;

    const job = this.activeJob;
    job.status = "downloading";
    job.mediaUrl = mediaUrl;
    job.updatedAt = Date.now();
    await saveJob(job);
    this.notify();

    try {
      const savedPath = await this.downloadService.downloadJobMedia(job, mediaUrl);
      job.status = "completed";
      job.downloadPath = savedPath;
      job.updatedAt = Date.now();
      await saveJob(job);
      await addLog("info", `Job completed: ${job.id}`, { savedPath });
    } catch (err: any) {
      job.status = "failed";
      job.error = `Download failed: ${err.message}`;
      job.updatedAt = Date.now();
      await saveJob(job);
      await addLog("error", `Download step failed: ${err.message}`, { jobId: job.id });
    } finally {
      this.activeJob = null;
      this.notify();
      this.processNext();
    }
  }

  private async processNext(): Promise<void> {
    if (this.isPaused || this.isProcessing || this.activeJob) return;

    const pendingJobs = await getJobsByStatus("pending");
    if (pendingJobs.length === 0) return;

    this.isProcessing = true;
    const job = pendingJobs[0];
    this.activeJob = job;

    try {
      job.status = "preparing";
      job.updatedAt = Date.now();
      await saveJob(job);
      this.notify();

      // Resolve character references
      const characters = await getAllCharacters();
      const match = matchCharacters(job.prompt, characters);
      job.resolvedPrompt = match.resolvedPrompt;
      job.characterIds = match.matchedCharacters.map((c) => c.id);

      // Locate Flow Tab
      const tab = await this.findFlowTab();
      if (!tab || !tab.id) {
        throw new Error("No active Google Flow tab found. Open flow.google.com in Chrome.");
      }

      job.status = "submitting";
      job.updatedAt = Date.now();
      await saveJob(job);
      this.notify();

      // Dispatch to Content Script
      const response = await this.sendJobToTab(tab.id, job);
      if (!response.success) {
        throw new Error(response.error || "Submission rejected by Flow adapter");
      }

      job.status = "generating";
      job.updatedAt = Date.now();
      await saveJob(job);
      this.notify();

      // Timeout safety: 180s max per generation
      setTimeout(async () => {
        if (this.activeJob?.id === job.id && this.activeJob.status === "generating") {
          job.status = "failed";
          job.error = "Generation timed out waiting for media capture";
          job.updatedAt = Date.now();
          await saveJob(job);
          this.activeJob = null;
          this.notify();
          this.processNext();
        }
      }, 180000);
    } catch (err: any) {
      job.status = "failed";
      job.error = err.message;
      job.updatedAt = Date.now();
      await saveJob(job);
      await addLog("error", `Execution failed: ${err.message}`, { jobId: job.id });
      this.activeJob = null;
      this.notify();

      // Apply delay before next attempt
      const settings = await getSettings();
      await new Promise((r) => setTimeout(r, (settings.defaultDelaySeconds || 5) * 1000));
      this.processNext();
    } finally {
      this.isProcessing = false;
    }
  }

  private async findFlowTab(): Promise<chrome.tabs.Tab | null> {
    try {
      const allTabs = await chrome.tabs.query({});
      const flowTab = allTabs.find((t) => t.url && (t.url.includes("flow.google.com") || t.url.includes("labs.google")));
      if (flowTab) return flowTab;
    } catch (_) {}
    const tabs = await chrome.tabs.query({ url: "*://flow.google.com/*" });
    if (tabs && tabs.length > 0) return tabs[0];
    const labsTabs = await chrome.tabs.query({ url: "*://labs.google/*" });
    if (labsTabs && labsTabs.length > 0) return labsTabs[0];
    return null;
  }

  private async sendJobToTab(tabId: number, job: Job): Promise<{ success: boolean; error?: string }> {
    return new Promise((resolve) => {
      chrome.tabs.sendMessage(tabId, { action: "submit_job", job }, async (response) => {
        const err = chrome.runtime.lastError;
        if (err && err.message?.includes("Could not establish connection")) {
          // Auto-inject fallback
          try {
            await chrome.scripting.executeScript({
              target: { tabId },
              files: ["dist/content.js"]
            });
            await new Promise((r) => setTimeout(r, 500));
            chrome.tabs.sendMessage(tabId, { action: "submit_job", job }, (retryRes) => {
              if (chrome.runtime.lastError) {
                resolve({ success: false, error: chrome.runtime.lastError.message });
              } else {
                resolve(retryRes || { success: true });
              }
            });
          } catch (e: any) {
            resolve({ success: false, error: "Auto-injection failed: " + e.message });
          }
        } else {
          resolve(response || { success: !err, error: err?.message });
        }
      });
    });
  }
}
