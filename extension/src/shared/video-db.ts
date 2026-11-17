import { openDB, DBSchema, IDBPDatabase } from "idb";
import { VideoProject, Scene, VideoAsset, ProjectStatus, SceneStatus } from "./video-types";

interface FlowDirectorDB extends DBSchema {
  projects: {
    key: string;
    value: VideoProject;
    indexes: {
      "by-status": string;
      "by-created": number;
    };
  };
  scenes: {
    key: string;
    value: Scene;
    indexes: {
      "by-project": string;
      "by-status": string;
      "by-created": number;
    };
  };
  video_assets: {
    key: string;
    value: VideoAsset;
    indexes: {
      "by-project": string;
      "by-scene": string;
      "by-role": string;
    };
  };
}

let dbPromise: Promise<IDBPDatabase<FlowDirectorDB>> | null = null;

export function getDirectorDB(): Promise<IDBPDatabase<FlowDirectorDB>> {
  if (!dbPromise) {
    dbPromise = openDB<FlowDirectorDB>("FlowDirectorDB", 1, {
      upgrade(db) {
        const projStore = db.createObjectStore("projects", { keyPath: "id" });
        projStore.createIndex("by-status", "status");
        projStore.createIndex("by-created", "createdAt");

        const sceneStore = db.createObjectStore("scenes", { keyPath: "id" });
        sceneStore.createIndex("by-project", "projectId");
        sceneStore.createIndex("by-status", "status");
        sceneStore.createIndex("by-created", "createdAt");

        const assetStore = db.createObjectStore("video_assets", { keyPath: "id" });
        assetStore.createIndex("by-project", "projectId");
        assetStore.createIndex("by-scene", "sceneId");
        assetStore.createIndex("by-role", "role");
      }
    });
  }
  return dbPromise;
}

// Project operations
export async function saveProject(project: VideoProject): Promise<void> {
  const db = await getDirectorDB();
  await db.put("projects", project);
}

export async function getProject(id: string): Promise<VideoProject | undefined> {
  const db = await getDirectorDB();
  return db.get("projects", id);
}

export async function getAllProjects(): Promise<VideoProject[]> {
  const db = await getDirectorDB();
  return db.getAllFromIndex("projects", "by-created");
}

export async function getProjectsByStatus(status: ProjectStatus): Promise<VideoProject[]> {
  const db = await getDirectorDB();
  return db.getAllFromIndex("projects", "by-status", status);
}

export async function deleteProject(id: string): Promise<void> {
  const db = await getDirectorDB();
  await db.delete("projects", id);
}

export async function updateProject(id: string, updates: Partial<VideoProject>): Promise<VideoProject | null> {
  const db = await getDirectorDB();
  const project = await db.get("projects", id);
  if (!project) return null;
  const updated = { ...project, ...updates, updatedAt: Date.now() };
  await db.put("projects", updated);
  return updated;
}

// Scene operations
export async function saveScene(scene: Scene): Promise<void> {
  const db = await getDirectorDB();
  await db.put("scenes", scene);
}

export async function getScene(id: string): Promise<Scene | undefined> {
  const db = await getDirectorDB();
  return db.get("scenes", id);
}

export async function getScenesForProject(projectId: string): Promise<Scene[]> {
  const db = await getDirectorDB();
  const scenes = await db.getAllFromIndex("scenes", "by-project", projectId);
  return scenes.sort((a, b) => a.sceneNumber - b.sceneNumber);
}

export async function getScenesByStatus(status: SceneStatus): Promise<Scene[]> {
  const db = await getDirectorDB();
  return db.getAllFromIndex("scenes", "by-status", status);
}

export async function updateScene(id: string, updates: Partial<Scene>): Promise<Scene | null> {
  const db = await getDirectorDB();
  const scene = await db.get("scenes", id);
  if (!scene) return null;
  const updated = { ...scene, ...updates, updatedAt: Date.now() };
  await db.put("scenes", updated);
  return updated;
}

export async function deleteScene(id: string): Promise<void> {
  const db = await getDirectorDB();
  await db.delete("scenes", id);
}

// VideoAsset operations
export async function saveVideoAsset(asset: VideoAsset): Promise<void> {
  const db = await getDirectorDB();
  await db.put("video_assets", asset);
}

export async function getVideoAsset(id: string): Promise<VideoAsset | undefined> {
  const db = await getDirectorDB();
  return db.get("video_assets", id);
}

export async function getAssetsForProject(projectId: string): Promise<VideoAsset[]> {
  const db = await getDirectorDB();
  return db.getAllFromIndex("video_assets", "by-project", projectId);
}

export async function getAssetsForScene(sceneId: string): Promise<VideoAsset[]> {
  const db = await getDirectorDB();
  return db.getAllFromIndex("video_assets", "by-scene", sceneId);
}

export async function deleteVideoAsset(id: string): Promise<void> {
  const db = await getDirectorDB();
  await db.delete("video_assets", id);
}
