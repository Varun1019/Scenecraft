import { describe, it, expect } from "vitest";
import { formatDownloadFilename } from "../shared/filename-template";

describe("Filename Template Formatter", () => {
  it("should format clean filenames without special characters", () => {
    const filename = formatDownloadFilename({
      prompt: "A beautiful sunset: over mountains & lake!",
      jobId: "job_123",
      ext: "png"
    });

    expect(filename).toMatch(/^GoogleFlow\/A_beautiful_sunset_over_mountains_\d+\.png$/);
    expect(filename).not.toContain(":");
    expect(filename).not.toContain("&");
    expect(filename).not.toContain("!");
  });

  it("should organize under batch subfolders when batchName is provided", () => {
    const filename = formatDownloadFilename({
      prompt: "Portrait of a warrior",
      jobId: "job_456",
      batchName: "Batch_001",
      ext: "mp4"
    });

    expect(filename).toMatch(/^GoogleFlow\/Batch_001\/Portrait_of_a_warrior_\d+\.mp4$/);
  });

  it("should include index sequence if provided", () => {
    const filename = formatDownloadFilename({
      prompt: "Frame item",
      jobId: "job_789",
      index: 7,
      ext: "png"
    });

    expect(filename).toMatch(/^GoogleFlow\/007_Frame_item_\d+\.png$/);
  });
});
