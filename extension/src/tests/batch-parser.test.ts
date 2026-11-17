import { describe, it, expect } from "vitest";
import { parseBatchText } from "../shared/batch-parser";

describe("Batch Parser", () => {
  it("should parse line-delimited TXT files", () => {
    const txt = `
      # Comments should be ignored
      A sleek sports car
      A quiet library with sunlight streaming in

      Neon city street
    `;
    const result = parseBatchText(txt, "prompts.txt");
    expect(result).toHaveLength(3);
    expect(result[0].prompt).toBe("A sleek sports car");
    expect(result[1].prompt).toBe("A quiet library with sunlight streaming in");
    expect(result[2].prompt).toBe("Neon city street");
  });

  it("should parse CSV files with columns", () => {
    const csv = `prompt,aspectRatio,type,model\n"Cyberpunk alley, rain",16:9,text-to-image,nano-banana-pro\n"Space station exterior",9:16,text-to-video,veo-3.1-quality`;
    const result = parseBatchText(csv, "batch.csv");
    expect(result).toHaveLength(2);
    expect(result[0].prompt).toBe("Cyberpunk alley, rain");
    expect(result[0].aspectRatio).toBe("16:9");
    expect(result[0].type).toBe("text-to-image");
    expect(result[0].model).toBe("nano-banana-pro");
    expect(result[1].prompt).toBe("Space station exterior");
    expect(result[1].aspectRatio).toBe("9:16");
  });

  it("should parse JSON array of strings or objects", () => {
    const json = JSON.stringify([
      "Prompt one",
      { prompt: "Prompt two", aspectRatio: "1:1", type: "text-to-image" }
    ]);
    const result = parseBatchText(json, "jobs.json");
    expect(result).toHaveLength(2);
    expect(result[0].prompt).toBe("Prompt one");
    expect(result[1].prompt).toBe("Prompt two");
    expect(result[1].aspectRatio).toBe("1:1");
  });
});
