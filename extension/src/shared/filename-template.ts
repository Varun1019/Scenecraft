export interface FormatParams {
  prompt: string;
  jobId: string;
  index?: number;
  batchName?: string;
  model?: string;
  aspectRatio?: string;
  ext?: string;
  folder?: string;
}

export function formatDownloadFilename(params: FormatParams): string {
  const ext = params.ext || "png";
  const cleanPrompt = params.prompt
    .slice(0, 35)
    .replace(/[^a-zA-Z0-9_-]/g, "_")
    .replace(/_+/g, "_")
    .replace(/^_|_$/g, "");

  const safePrompt = cleanPrompt || "flow_output";
  const idx = params.index !== undefined ? String(params.index).padStart(3, "0") : "";
  const folder = params.folder || "GoogleFlow";
  const subFolder = params.batchName ? `${params.batchName}` : "";

  const filename = `${idx ? `${idx}_` : ""}${safePrompt}_${Date.now()}.${ext}`;

  if (subFolder) {
    return `${folder}/${subFolder}/${filename}`;
  }
  return `${folder}/${filename}`;
}
