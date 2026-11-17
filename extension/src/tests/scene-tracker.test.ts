import { describe, it, expect } from "vitest";
import { SceneTracker } from "../shared/scene-tracker";

describe("SceneTracker & Smart Scene Identification", () => {
  const sampleProject = {
    project_id: "proj_tokyo_001",
    project_title: "Tokyo_Cyberpunk",
    full_script: "Full script text...",
    scenes: [
      {
        scene_number: 1,
        scene_title: "Neon_Skyline",
        image_prompt: "Cinematic wide aerial shot of futuristic Tokyo skyline bathed in purple neon rain"
      },
      {
        scene_number: 2,
        scene_title: "Cyber_Supercar",
        image_prompt: "Low angle tracking shot of sleek chrome cyber vehicle accelerating through wet highway"
      },
      {
        scene_number: 3,
        scene_title: "Driver_Hero",
        image_prompt: "Interior cockpit view of futuristic driver in glowing augmented reality visor"
      },
      {
        scene_number: 4,
        scene_title: "Drone_Explosion",
        image_prompt: "High speed mid-air collision of surveillance drone exploding into bright orange sparks"
      }
    ]
  };

  it("normalizes project payload with unique IDs and structured filenames", () => {
    const tracker = new SceneTracker(sampleProject);
    const p = tracker.getProject();

    expect(p.projectId).toBe("proj_tokyo_001");
    expect(p.scenes.length).toBe(4);
    expect(p.scenes[0].sceneNumber).toBe(1);
    expect(p.scenes[0].sceneId).toBe("scene_proj_tokyo_001_001");
    expect(p.scenes[0].actualOutputFilename).toBe("Generated/Tokyo_Cyberpunk/01_Neon_Skyline.png");
    expect(p.scenes[3].sceneNumber).toBe(4);
    expect(p.scenes[3].actualOutputFilename).toBe("Generated/Tokyo_Cyberpunk/04_Drone_Explosion.png");
  });

  it("handles out-of-order generation correctly (Scene 4 before Scene 2)", () => {
    const tracker = new SceneTracker(sampleProject);

    // Media for Scene 4 arrives first with prompt snippet
    const match4 = tracker.matchMediaToScene("https://flow-content.google/image/drone_99182.png", {
      promptSnippet: "surveillance drone exploding into bright orange sparks"
    });

    expect(match4.matched).toBe(true);
    expect(match4.scene?.sceneNumber).toBe(4);
    expect(match4.filename).toBe("Generated/Tokyo_Cyberpunk/04_Drone_Explosion.png");
    expect(match4.scene?.mediaUrl).toBe("https://flow-content.google/image/drone_99182.png");

    tracker.markSceneDownloaded(4, 101, match4.filename);
    expect(tracker.getScene(4)?.downloadStatus).toBe("downloaded");
    expect(tracker.getScene(2)?.downloadStatus).toBe("pending");

    // Next media for Scene 2 arrives
    const match2 = tracker.matchMediaToScene("https://flow-content.google/image/car_123.png", {
      promptSnippet: "sleek chrome cyber vehicle accelerating"
    });

    expect(match2.matched).toBe(true);
    expect(match2.scene?.sceneNumber).toBe(2);
    expect(match2.filename).toBe("Generated/Tokyo_Cyberpunk/02_Cyber_Supercar.png");

    tracker.markSceneDownloaded(2, 102, match2.filename);
    expect(tracker.getCompletedCount()).toBe(2);
    expect(tracker.isAllScenesDownloaded()).toBe(false);
  });

  it("flags ambiguous or unrecognized media instead of assigning incorrect scene filename", () => {
    const tracker = new SceneTracker(sampleProject);

    // Some completely unrelated or ambiguous image arrives
    const ambiguousMatch = tracker.matchMediaToScene("https://flow-content.google/image/random_unknown_asset.png", {
      promptSnippet: "a bowl of fresh green apples on a white kitchen table"
    });

    expect(ambiguousMatch.matched).toBe(false);
    expect(ambiguousMatch.flagged).toBe(true);
    expect(ambiguousMatch.filename).toContain("Generated/Tokyo_Cyberpunk/_unassigned/unmatched_");

    // All original scenes should remain pending and not corrupted
    const p = tracker.getProject();
    expect(p.scenes.every((s) => s.downloadStatus === "pending")).toBe(true);
    expect(p.unassignedOutputs.length).toBe(1);
  });

  it("generates a complete manifest with all scene metadata and output paths", () => {
    const tracker = new SceneTracker(sampleProject);

    tracker.markSceneDownloaded(1, 201, "Generated/Tokyo_Cyberpunk/01_Neon_Skyline.png");
    tracker.markSceneDownloaded(2, 202, "Generated/Tokyo_Cyberpunk/02_Cyber_Supercar.png");
    tracker.markSceneDownloaded(3, 203, "Generated/Tokyo_Cyberpunk/03_Driver_Hero.png");
    tracker.markSceneDownloaded(4, 204, "Generated/Tokyo_Cyberpunk/04_Drone_Explosion.png");

    expect(tracker.isAllScenesDownloaded()).toBe(true);

    const manifest = tracker.generateManifest();
    expect(manifest.projectId).toBe("proj_tokyo_001");
    expect(manifest.status).toBe("completed");
    expect(manifest.totalScenes).toBe(4);
    expect(manifest.completedScenes).toBe(4);
    expect(manifest.scenes[0].filename).toBe("Generated/Tokyo_Cyberpunk/01_Neon_Skyline.png");
    expect(manifest.scenes[3].filename).toBe("Generated/Tokyo_Cyberpunk/04_Drone_Explosion.png");
  });
});
