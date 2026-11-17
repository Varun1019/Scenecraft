import { QueueManager } from "./queue-manager";
import { Job } from "../shared/types";
import { getSettings, addLog } from "../shared/db";

export class AgentBridgeClient {
  private queueManager: QueueManager;
  private bridgeUrl = "http://127.0.0.1:8795";
  private isConnected = false;
  private agentJobMap = new Map<string, string>(); // internalJobId -> agentJobId

  constructor(queueManager: QueueManager) {
    this.queueManager = queueManager;
    this.init();
  }

  get connected(): boolean {
    return this.isConnected;
  }

  private async init() {
    const settings = await getSettings();
    this.bridgeUrl = `http://127.0.0.1:${settings.agentBridgePort || 8795}`;

    // Periodic heartbeat
    setInterval(() => this.heartbeat(), 5000);
    this.heartbeat();

    // Start polling loop
    this.pollLoop();

    // Listen for queue updates
    this.queueManager.subscribe(() => this.checkCompletedJobs());
  }

  private async heartbeat() {
    try {
      const res = await fetch(`${this.bridgeUrl}/api/heartbeat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" }
      });
      this.isConnected = res.ok;
    } catch (_) {
      this.isConnected = false;
    }
  }

  private async pollLoop() {
    while (true) {
      try {
        const res = await fetch(`${this.bridgeUrl}/api/jobs/next`);
        if (res.ok) {
          this.isConnected = true;
          const data = await res.json();
          if (data && data.job) {
            await this.handleIncomingAgentJob(data.job);
          }
        }
      } catch (_) {
        this.isConnected = false;
        await new Promise((r) => setTimeout(r, 4000));
      }
    }
  }

  private async handleIncomingAgentJob(agentJob: any) {
    const internalId = "job_agent_" + Date.now() + "_" + Math.random().toString(36).slice(2, 6);
    this.agentJobMap.set(internalId, agentJob.id);

    const job: Job = {
      id: internalId,
      prompt: agentJob.prompt,
      resolvedPrompt: agentJob.prompt,
      type: agentJob.type || "text-to-image",
      status: "pending",
      aspectRatio: agentJob.aspectRatio || "16:9",
      model: agentJob.model,
      duration: agentJob.duration,
      outputs: agentJob.outputs || 1,
      createdAt: Date.now(),
      updatedAt: Date.now(),
      retryCount: 0,
      maxRetries: 3,
      source: "agent"
    };

    await addLog("info", `Received Agent Job: ${agentJob.prompt.slice(0, 30)}...`, {
      agentJobId: agentJob.id
    });
    await this.queueManager.addJob(job);
  }

  private async checkCompletedJobs() {
    // When a job finishes, notify bridge
    for (const [internalId, agentJobId] of this.agentJobMap.entries()) {
      const job = await import("../shared/db").then((m) => m.getJob(internalId));
      if (job && (job.status === "completed" || job.status === "failed" || job.status === "cancelled")) {
        this.agentJobMap.delete(internalId);
        try {
          await fetch(`${this.bridgeUrl}/api/jobs/complete`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              id: agentJobId,
              success: job.status === "completed",
              filename: job.downloadPath,
              url: job.mediaUrl,
              error: job.error
            })
          });
        } catch (err) {
          console.error("[AgentBridge] Failed to report complete:", err);
        }
      }
    }
  }
}
