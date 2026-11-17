import { VideoProject, Scene } from "./video-types";

export function projectFolder(project: VideoProject): string {
  const safeName = project.title.replace(/[^a-zA-Z0-9_\- ]/g, "").replace(/\s+/g, "_").slice(0, 50);
  return `GoogleFlow/Projects/${safeName}`;
}

export function sceneImageFilename(scene: Scene): string {
  const pad = String(scene.sceneNumber).padStart(3, "0");
  const safeTitle = scene.title.replace(/[^a-zA-Z0-9_\- ]/g, "").replace(/\s+/g, "_").slice(0, 40);
  return `Scene_${pad}_${safeTitle}.png`;
}

export function sceneVideoFilename(scene: Scene): string {
  const pad = String(scene.sceneNumber).padStart(3, "0");
  const safeTitle = scene.title.replace(/[^a-zA-Z0-9_\- ]/g, "").replace(/\s+/g, "_").slice(0, 40);
  return `Scene_${pad}_${safeTitle}.mp4`;
}

export function sceneFinalFilename(scene: Scene): string {
  const pad = String(scene.sceneNumber).padStart(3, "0");
  const safeTitle = scene.title.replace(/[^a-zA-Z0-9_\- ]/g, "").replace(/\s+/g, "_").slice(0, 40);
  return `${pad}_Scene_${pad}_${safeTitle}.mp4`;
}

export function imageDownloadPath(project: VideoProject, scene: Scene): string {
  return `${projectFolder(project)}/02_Images/${sceneImageFilename(scene)}`;
}

export function videoDownloadPath(project: VideoProject, scene: Scene): string {
  return `${projectFolder(project)}/03_Videos/${sceneVideoFilename(scene)}`;
}

export function referenceDownloadPath(project: VideoProject, name: string, ext = "png"): string {
  const safeName = name.replace(/[^a-zA-Z0-9_\- ]/g, "").replace(/\s+/g, "_");
  return `${projectFolder(project)}/01_References/${safeName}.${ext}`;
}

export function finalSequencePath(project: VideoProject, scene: Scene): string {
  return `${projectFolder(project)}/04_Final_Sequence/${sceneFinalFilename(scene)}`;
}

export function reportPath(project: VideoProject, ext: "json" | "csv"): string {
  return `${projectFolder(project)}/05_Reports/generation_report.${ext}`;
}

export function storyboardPath(project: VideoProject): string {
  return `${projectFolder(project)}/00_Project/storyboard.json`;
}

export function scenesUniqueId(projectId: string, sceneNumber: number): string {
  return `scene_${projectId}_${String(sceneNumber).padStart(3, "0")}`;
}
