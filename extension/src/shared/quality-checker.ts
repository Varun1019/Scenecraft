import { Scene, QCResult } from "./video-types";

/** Runs QC rules on a completed scene. fileSize values come from download records. */
export function checkSceneQuality(
  scene: Scene,
  imageFileSize: number | undefined,
  videoFileSize: number | undefined,
  allScenes: Scene[]
): QCResult {
  const hasImage = !!scene.imageLocalPath;
  const hasVideo = !!scene.videoLocalPath;
  const imageNonZero = !!imageFileSize && imageFileSize > 0;
  const videoNonZero = !!videoFileSize && videoFileSize > 0;

  // Check for duplicates: no other completed scene should have same localPath
  const correctScene =
    hasImage &&
    hasVideo &&
    !allScenes.some(
      (s) =>
        s.id !== scene.id &&
        s.status === "completed" &&
        ((s.imageLocalPath && s.imageLocalPath === scene.imageLocalPath) ||
          (s.videoLocalPath && s.videoLocalPath === scene.videoLocalPath))
    );

  const noDuplicates = !allScenes.some(
    (s) =>
      s.id !== scene.id &&
      s.status === "completed" &&
      s.imageLocalPath === scene.imageLocalPath &&
      !!scene.imageLocalPath
  );

  const passed = hasImage && hasVideo && imageNonZero && videoNonZero && correctScene && noDuplicates;

  const notes: string[] = [];
  if (!hasImage) notes.push("Missing image output");
  if (!hasVideo) notes.push("Missing video output");
  if (!imageNonZero) notes.push("Image file is zero-size or missing");
  if (!videoNonZero) notes.push("Video file is zero-size or missing");
  if (!noDuplicates) notes.push("Duplicate file path detected");

  return {
    sceneId: scene.id,
    passed,
    checks: { hasImage, hasVideo, imageNonZero, videoNonZero, correctScene, noDuplicates },
    notes: notes.join("; ") || "All checks passed"
  };
}

/** Generates a CSV-compatible report string. */
export function buildReportCSV(scenes: Scene[]): string {
  const header = "sceneNumber,title,status,imageLocalPath,videoLocalPath,qcPassed,error";
  const rows = scenes.map((s) =>
    [
      s.sceneNumber,
      `"${s.title.replace(/"/g, '""')}"`,
      s.status,
      s.imageLocalPath ?? "",
      s.videoLocalPath ?? "",
      s.qcPassed ?? "",
      `"${(s.error ?? "").replace(/"/g, '""')}"`
    ].join(",")
  );
  return [header, ...rows].join("\n");
}
