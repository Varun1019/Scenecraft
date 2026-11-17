import { openDB, DBSchema, IDBPDatabase } from "idb";
import { Job, Batch, Character, PromptItem, AssetItem, Settings, LogEntry } from "./types";
import { DEFAULT_SETTINGS } from "./constants";

interface FlowStudioDB extends DBSchema {
  jobs: {
    key: string;
    value: Job;
    indexes: {
      "by-status": string;
      "by-batch": string;
      "by-created": number;
    };
  };
  batches: {
    key: string;
    value: Batch;
    indexes: {
      "by-created": number;
    };
  };
  characters: {
    key: string;
    value: Character;
    indexes: {
      "by-trigger": string;
    };
  };
  prompts: {
    key: string;
    value: PromptItem;
    indexes: {
      "by-category": string;
      "by-favorite": number;
    };
  };
  assets: {
    key: string;
    value: AssetItem;
    indexes: {
      "by-created": number;
      "by-job": string;
    };
  };
  settings: {
    key: string;
    value: Settings;
  };
  logs: {
    key: string;
    value: LogEntry;
    indexes: {
      "by-timestamp": number;
    };
  };
}

let dbPromise: Promise<IDBPDatabase<FlowStudioDB>> | null = null;

export function getDB(): Promise<IDBPDatabase<FlowStudioDB>> {
  if (!dbPromise) {
    dbPromise = openDB<FlowStudioDB>("FlowStudioDB", 1, {
      upgrade(db) {
        // Jobs Store
        const jobStore = db.createObjectStore("jobs", { keyPath: "id" });
        jobStore.createIndex("by-status", "status");
        jobStore.createIndex("by-batch", "batchId");
        jobStore.createIndex("by-created", "createdAt");

        // Batches Store
        const batchStore = db.createObjectStore("batches", { keyPath: "id" });
        batchStore.createIndex("by-created", "createdAt");

        // Characters Store
        const charStore = db.createObjectStore("characters", { keyPath: "id" });
        charStore.createIndex("by-trigger", "trigger");

        // Prompts Store
        const promptStore = db.createObjectStore("prompts", { keyPath: "id" });
        promptStore.createIndex("by-category", "category");
        promptStore.createIndex("by-favorite", "favorite");

        // Assets Store
        const assetStore = db.createObjectStore("assets", { keyPath: "id" });
        assetStore.createIndex("by-created", "createdAt");
        assetStore.createIndex("by-job", "jobId");

        // Settings Store
        db.createObjectStore("settings");

        // Logs Store
        const logStore = db.createObjectStore("logs", { keyPath: "id" });
        logStore.createIndex("by-timestamp", "timestamp");
      }
    });
  }
  return dbPromise;
}

// Job Operations
export async function saveJob(job: Job): Promise<void> {
  const db = await getDB();
  await db.put("jobs", job);
}

export async function getJob(id: string): Promise<Job | undefined> {
  const db = await getDB();
  return db.get("jobs", id);
}

export async function getAllJobs(): Promise<Job[]> {
  const db = await getDB();
  return db.getAllFromIndex("jobs", "by-created");
}

export async function getJobsByStatus(status: Job["status"]): Promise<Job[]> {
  const db = await getDB();
  return db.getAllFromIndex("jobs", "by-status", status);
}

export async function deleteJob(id: string): Promise<void> {
  const db = await getDB();
  await db.delete("jobs", id);
}

export async function clearJobs(): Promise<void> {
  const db = await getDB();
  await db.clear("jobs");
}

// Batch Operations
export async function saveBatch(batch: Batch): Promise<void> {
  const db = await getDB();
  await db.put("batches", batch);
}

export async function getBatch(id: string): Promise<Batch | undefined> {
  const db = await getDB();
  return db.get("batches", id);
}

export async function getAllBatches(): Promise<Batch[]> {
  const db = await getDB();
  return db.getAllFromIndex("batches", "by-created");
}

// Character Operations
export async function saveCharacter(char: Character): Promise<void> {
  const db = await getDB();
  await db.put("characters", char);
}

export async function getAllCharacters(): Promise<Character[]> {
  const db = await getDB();
  return db.getAll("characters");
}

export async function deleteCharacter(id: string): Promise<void> {
  const db = await getDB();
  await db.delete("characters", id);
}

// Prompt Operations
export async function savePrompt(prompt: PromptItem): Promise<void> {
  const db = await getDB();
  await db.put("prompts", prompt);
}

export async function getAllPrompts(): Promise<PromptItem[]> {
  const db = await getDB();
  return db.getAll("prompts");
}

export async function deletePrompt(id: string): Promise<void> {
  const db = await getDB();
  await db.delete("prompts", id);
}

// Asset Operations
export async function saveAsset(asset: AssetItem): Promise<void> {
  const db = await getDB();
  await db.put("assets", asset);
}

export async function getAllAssets(): Promise<AssetItem[]> {
  const db = await getDB();
  return db.getAllFromIndex("assets", "by-created");
}

export async function deleteAsset(id: string): Promise<void> {
  const db = await getDB();
  await db.delete("assets", id);
}

// Settings Operations
export async function getSettings(): Promise<Settings> {
  const db = await getDB();
  const settings = await db.get("settings", "global");
  return settings || DEFAULT_SETTINGS;
}

export async function saveSettings(settings: Settings): Promise<void> {
  const db = await getDB();
  await db.put("settings", settings, "global");
}

// Log Operations
export async function addLog(level: LogEntry["level"], message: string, context?: Record<string, unknown>): Promise<void> {
  try {
    const db = await getDB();
    const entry: LogEntry = {
      id: "log_" + Date.now() + "_" + Math.random().toString(36).slice(2, 6),
      timestamp: Date.now(),
      level,
      message,
      context
    };
    await db.put("logs", entry);
  } catch (_) {}
}

export async function getAllLogs(limit = 100): Promise<LogEntry[]> {
  const db = await getDB();
  const logs = await db.getAllFromIndex("logs", "by-timestamp");
  return logs.slice(-limit);
}
