import { Job } from "../shared/types";
import { formatDownloadFilename } from "../shared/filename-template";
import { getSettings, saveAsset, addLog } from "../shared/db";

export class DownloadService {
  async downloadJobMedia(job: Job, mediaUrl: string): Promise<string> {
    const settings = await getSettings();
    if (!settings.autoDownload) {
      await addLog("info", "Auto-download disabled in settings", { jobId: job.id });
      return mediaUrl;
    }

    const isVideo = mediaUrl.includes("/video/") || job.type.includes("video");
    const ext = isVideo ? "mp4" : "png";

    const filename = formatDownloadFilename({
      prompt: job.prompt,
      jobId: job.id,
      model: job.model,
      aspectRatio: job.aspectRatio,
      folder: settings.downloadFolder,
      batchName: job.batchId ? `Batch_${job.batchId.slice(0, 6)}` : undefined,
      ext
    });

    return new Promise((resolve, reject) => {
      chrome.downloads.download(
        {
          url: mediaUrl,
          filename: filename,
          saveAs: false
        },
        async (downloadId) => {
          if (chrome.runtime.lastError || !downloadId) {
            const err = chrome.runtime.lastError?.message || "Download initiation failed";
            await addLog("error", `Download failed: ${err}`, { jobId: job.id, url: mediaUrl });
            reject(new Error(err));
          } else {
            await addLog("info", `Media downloaded successfully`, {
              jobId: job.id,
              filename,
              downloadId
            });

            // Save into Asset Library
            await saveAsset({
              id: "asset_" + Date.now() + "_" + Math.random().toString(36).slice(2, 6),
              jobId: job.id,
              prompt: job.prompt,
              url: mediaUrl,
              localPath: filename,
              mediaType: isVideo ? "video" : "image",
              createdAt: Date.now()
            });

            resolve(filename);
          }
        }
      );
    });
  }
}
