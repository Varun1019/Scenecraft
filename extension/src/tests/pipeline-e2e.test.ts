import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { SceneTracker } from "../shared/scene-tracker";
import http from "http";

describe("Flow Connect 2.0 - Core Pipeline & Validation Suite", () => {
  // Test 1: Two-Scene Project Pipeline (Requirement 10.1)
  it("Test 1: Two-scene project pipeline executes with full acknowledgments and correct scene filenames", () => {
    const projectPayload = {
      project_id: "test_proj_2scenes_001",
      project_title: "Stickman_Artist_Studio",
      full_script: "PROJECT: Stickman Artist Studio\n\n[SCENE 1: Stickman Awakening]\n2B pencil stickman awakens on paper.\n\n[SCENE 2: Stickman Portal]\nStickman draws glowing archway.",
      scenes: [
        {
          scene_number: 1,
          scene_title: "Stickman_Awakening",
          image_prompt: "Macro shot of rough watercolor paper. Athletic 2D stickman drawn in dark graphite pencil sitting up."
        },
        {
          scene_number: 2,
          scene_title: "Stickman_Portal",
          image_prompt: "Stickman holding glowing pencil tip, drawing radiant archway portal on parchment."
        }
      ]
    };

    const tracker = new SceneTracker(projectPayload);
    const p = tracker.getProject();

    // Verification: Initial state
    expect(p.scenes.length).toBe(2);
    expect(p.scenes[0].actualOutputFilename).toBe("Generated/Stickman_Artist_Studio/01_Stickman_Awakening.png");
    expect(p.scenes[1].actualOutputFilename).toBe("Generated/Stickman_Artist_Studio/02_Stickman_Portal.png");

    // Stage 1: Submission
    tracker.markSceneSubmitting(1);
    expect(tracker.getScene(1)?.generationStatus).toBe("submitting");

    tracker.markSceneGenerating(1);
    expect(tracker.getScene(1)?.generationStatus).toBe("generating");

    // Stage 2: Media Intercepted & Matched for Scene 1
    const match1 = tracker.matchMediaToScene("https://flow-content.google/image/stickman_01.png", {
      promptSnippet: "athletic 2d stickman drawn in dark graphite pencil"
    });
    expect(match1.matched).toBe(true);
    expect(match1.scene?.sceneNumber).toBe(1);
    expect(match1.filename).toBe("Generated/Stickman_Artist_Studio/01_Stickman_Awakening.png");

    // Stage 3: Download Complete
    tracker.markSceneDownloaded(1, 1001, match1.filename);
    expect(tracker.getScene(1)?.downloadStatus).toBe("downloaded");
    expect(tracker.isAllScenesDownloaded()).toBe(false);

    // Stage 4: Scene 2 execution
    tracker.markSceneGenerating(2);
    const match2 = tracker.matchMediaToScene("https://flow-content.google/image/portal_02.png", {
      promptSnippet: "stickman holding glowing pencil tip drawing radiant archway"
    });
    expect(match2.matched).toBe(true);
    expect(match2.scene?.sceneNumber).toBe(2);
    expect(match2.filename).toBe("Generated/Stickman_Artist_Studio/02_Stickman_Portal.png");

    tracker.markSceneDownloaded(2, 1002, match2.filename);
    expect(tracker.isAllScenesDownloaded()).toBe(true);

    // Stage 5: Manifest Verification
    const manifest = tracker.generateManifest();
    expect(manifest.status).toBe("completed");
    expect(manifest.completedScenes).toBe(2);
    expect(manifest.scenes[0].filename).toBe("Generated/Stickman_Artist_Studio/01_Stickman_Awakening.png");
    expect(manifest.scenes[1].filename).toBe("Generated/Stickman_Artist_Studio/02_Stickman_Portal.png");
  });

  // Test 2: Five-Scene Project Pipeline (Requirement 10.2)
  it("Test 2: Five-scene project pipeline maintains independent scene states and full manifest integrity", () => {
    const projectPayload = {
      project_id: "test_proj_5scenes_002",
      project_title: "Cyberpunk_Metropolis_5_Scenes",
      full_script: "5 scene cyberpunk production",
      scenes: [
        { scene_number: 1, scene_title: "Neon_Skyline", image_prompt: "Futuristic Tokyo neon rain" },
        { scene_number: 2, scene_title: "Chrome_Interceptor", image_prompt: "Hover vehicle acceleration" },
        { scene_number: 3, scene_title: "Cybernetic_Pilot", image_prompt: "Visor reflections in cockpit" },
        { scene_number: 4, scene_title: "Drone_Ambush", image_prompt: "Security drones descending" },
        { scene_number: 5, scene_title: "Safe_Haven", image_prompt: "Subterranean amber garage" }
      ]
    };

    const tracker = new SceneTracker(projectPayload);

    for (let i = 1; i <= 5; i++) {
      tracker.markSceneGenerating(i);
      const match = tracker.matchMediaToScene(`https://flow-content.google/image/scene_${i}_render.png`, {
        sceneNumberHint: i
      });
      expect(match.matched).toBe(true);
      expect(match.scene?.sceneNumber).toBe(i);
      tracker.markSceneDownloaded(i, 2000 + i, match.filename);
    }

    expect(tracker.isAllScenesDownloaded()).toBe(true);
    const manifest = tracker.generateManifest();
    expect(manifest.totalScenes).toBe(5);
    expect(manifest.completedScenes).toBe(5);
    expect(manifest.scenes[4].filename).toBe("Generated/Cyberpunk_Metropolis_5_Scenes/05_Safe_Haven.png");
  });

  // Test 3: Delayed & Out-of-Order Downloads (Requirement 10.3)
  it("Test 3: Out-of-order downloads (Scene 4, then Scene 1, then Scene 3, then Scene 2) correctly resolve to their intended filenames", () => {
    const projectPayload = {
      project_id: "test_proj_ooo_003",
      project_title: "Deep_Space_Mission",
      full_script: "Deep space mission scenes",
      scenes: [
        { scene_number: 1, scene_title: "Launch", image_prompt: "Massive carrier vessel launching from orbital shipyard" },
        { scene_number: 2, scene_title: "Asteroid_Field", image_prompt: "Navigating through dense frozen icy comets" },
        { scene_number: 3, scene_title: "Wormhole_Entry", image_prompt: "Gravitational lensing around swirling vortex" },
        { scene_number: 4, scene_title: "Alien_Station", image_prompt: "Gigantic derelict biomechanical megastructure" }
      ]
    };

    const tracker = new SceneTracker(projectPayload);

    // 1. Scene 4 arrives FIRST
    const match4 = tracker.matchMediaToScene("https://flow-content.google/image/biomech_station.png", {
      promptSnippet: "gigantic derelict biomechanical megastructure"
    });
    expect(match4.matched).toBe(true);
    expect(match4.scene?.sceneNumber).toBe(4);
    expect(match4.filename).toBe("Generated/Deep_Space_Mission/04_Alien_Station.png");
    tracker.markSceneDownloaded(4, 3004, match4.filename);

    // 2. Scene 1 arrives SECOND
    const match1 = tracker.matchMediaToScene("https://flow-content.google/image/shipyard_launch.png", {
      promptSnippet: "massive carrier vessel launching from orbital shipyard"
    });
    expect(match1.matched).toBe(true);
    expect(match1.scene?.sceneNumber).toBe(1);
    expect(match1.filename).toBe("Generated/Deep_Space_Mission/01_Launch.png");
    tracker.markSceneDownloaded(1, 3001, match1.filename);

    // 3. Ambiguous asset arrives THIRD: must NOT mislabel Scene 2 or 3!
    const ambiguous = tracker.matchMediaToScene("https://flow-content.google/image/cute_puppy.png", {
      promptSnippet: "golden retriever playing with ball on grass"
    });
    expect(ambiguous.matched).toBe(false);
    expect(ambiguous.flagged).toBe(true);
    expect(ambiguous.filename).toContain("Generated/Deep_Space_Mission/_unassigned/unmatched_");

    // 4. Scene 3 arrives FOURTH
    const match3 = tracker.matchMediaToScene("https://flow-content.google/image/wormhole_swirl.png", {
      promptSnippet: "gravitational lensing around swirling vortex"
    });
    expect(match3.matched).toBe(true);
    expect(match3.scene?.sceneNumber).toBe(3);
    expect(match3.filename).toBe("Generated/Deep_Space_Mission/03_Wormhole_Entry.png");
    tracker.markSceneDownloaded(3, 3003, match3.filename);

    // 5. Scene 2 arrives LAST
    const match2 = tracker.matchMediaToScene("https://flow-content.google/image/asteroid_drift.png", {
      promptSnippet: "navigating through dense frozen icy comets"
    });
    expect(match2.matched).toBe(true);
    expect(match2.scene?.sceneNumber).toBe(2);
    expect(match2.filename).toBe("Generated/Deep_Space_Mission/02_Asteroid_Field.png");
    tracker.markSceneDownloaded(2, 3002, match2.filename);

    // All 4 scenes must be correctly downloaded with untouched filenames
    expect(tracker.isAllScenesDownloaded()).toBe(true);
    const manifest = tracker.generateManifest();
    expect(manifest.completedScenes).toBe(4);
    expect(manifest.unassignedOutputs.length).toBe(1);
    expect(tracker.getScene(1)?.actualOutputFilename).toBe("Generated/Deep_Space_Mission/01_Launch.png");
    expect(tracker.getScene(2)?.actualOutputFilename).toBe("Generated/Deep_Space_Mission/02_Asteroid_Field.png");
    expect(tracker.getScene(3)?.actualOutputFilename).toBe("Generated/Deep_Space_Mission/03_Wormhole_Entry.png");
    expect(tracker.getScene(4)?.actualOutputFilename).toBe("Generated/Deep_Space_Mission/04_Alien_Station.png");
  });
});
