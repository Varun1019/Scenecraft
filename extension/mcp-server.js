#!/usr/bin/env node

/**
 * Antigravity MCP Server for Google Flow Chrome Extension.
 * Communicates via JSON-RPC 2.0 on stdio.
 */

const http = require("http");
const readline = require("readline");
const { spawn } = require("child_process");
const path = require("path");

const BRIDGE_PORT = 8792;
const BRIDGE_URL = `http://127.0.0.1:${BRIDGE_PORT}`;

// Ensure bridge is running
function ensureBridgeRunning() {
  const req = http.get(`${BRIDGE_URL}/health`, (res) => {});
  req.on("error", () => {
    const bridgePath = path.join(__dirname, "bridge.js");
    const child = spawn(process.execPath, [bridgePath], {
      detached: true,
      stdio: "ignore"
    });
    child.unref();
  });
}
ensureBridgeRunning();

function makeRequest(method, endpoint, data = null) {
  return new Promise((resolve, reject) => {
    const url = new URL(endpoint, BRIDGE_URL);
    const options = {
      method: method,
      hostname: url.hostname,
      port: url.port,
      path: url.pathname,
      headers: {
        "Content-Type": "application/json"
      }
    };

    const req = http.request(options, (res) => {
      let body = "";
      res.on("data", (chunk) => (body += chunk));
      res.on("end", () => {
        try {
          resolve(JSON.parse(body || "{}"));
        } catch (e) {
          resolve({ raw: body });
        }
      });
    });

    req.on("error", (err) => reject(err));
    if (data) {
      req.write(JSON.stringify(data));
    }
    req.end();
  });
}

const TOOLS = [
  {
    name: "flow_generate_image",
    description: "Generate an image on flow.google.com using the Flow Chrome Extension and download to Downloads folder.",
    inputSchema: {
      type: "object",
      properties: {
        prompt: {
          type: "string",
          description: "Visual prompt description for image generation"
        },
        aspect_ratio: {
          type: "string",
          enum: ["16:9", "1:1", "9:16"],
          description: "Aspect ratio for generated image (default: 16:9)"
        }
      },
      required: ["prompt"]
    }
  },
  {
    name: "flow_get_status",
    description: "Check connection status between Antigravity, local bridge, and Flow Chrome extension.",
    inputSchema: {
      type: "object",
      properties: {}
    }
  },
  {
    name: "create_video_project",
    description: "Create a new AI Video Director project. Returns a projectId to use in all subsequent scene operations.",
    inputSchema: {
      type: "object",
      properties: {
        title: { type: "string", description: "Project title, e.g. 'Futuristic Tokyo'" },
        brief: { type: "string", description: "Full creative brief / user instruction" },
        mode: { type: "string", enum: ["agent", "direct", "auto"], description: "Production mode (default: auto)" },
        autonomous: { type: "boolean", description: "Skip approval gates and run fully autonomous" }
      },
      required: ["brief"]
    }
  },
  {
    name: "create_storyboard",
    description: "Submit a complete scene-by-scene storyboard for a project. Each scene becomes a production unit.",
    inputSchema: {
      type: "object",
      properties: {
        projectId: { type: "string" },
        scenes: {
          type: "array",
          description: "Array of scene objects",
          items: {
            type: "object",
            properties: {
              sceneNumber: { type: "number" },
              title: { type: "string" },
              narrativePurpose: { type: "string" },
              description: { type: "string" },
              durationSeconds: { type: "number" },
              imagePrompt: { type: "string" },
              videoPrompt: { type: "string" },
              characterRefs: { type: "array", items: { type: "string" } },
              environmentRefs: { type: "array", items: { type: "string" } },
              cameraInstructions: { type: "string" },
              motionInstructions: { type: "string" },
              aspectRatio: { type: "string", enum: ["16:9", "1:1", "9:16", "4:3"] },
              model: { type: "string" },
              dependsOn: { type: "array", items: { type: "string" }, description: "Scene IDs that must complete before this scene" }
            },
            required: ["sceneNumber", "title", "imagePrompt", "videoPrompt"]
          }
        }
      },
      required: ["projectId", "scenes"]
    }
  },
  {
    name: "generate_scene_image",
    description: "Start image generation for a specific scene. Returns when image is downloaded.",
    inputSchema: {
      type: "object",
      properties: {
        projectId: { type: "string" },
        sceneId: { type: "string" }
      },
      required: ["projectId", "sceneId"]
    }
  },
  {
    name: "generate_scene_video",
    description: "Start video generation for a specific scene (uses the scene's generated image as reference). Returns when video is downloaded.",
    inputSchema: {
      type: "object",
      properties: {
        projectId: { type: "string" },
        sceneId: { type: "string" },
        videoModel: { type: "string", description: "Override video model, e.g. veo-3.1-quality" }
      },
      required: ["projectId", "sceneId"]
    }
  },
  {
    name: "submit_scene_to_flow_agent",
    description: "Submit a scene to the Google Flow Agent interface for AI-driven generation.",
    inputSchema: {
      type: "object",
      properties: {
        projectId: { type: "string" },
        sceneId: { type: "string" },
        instructions: { type: "string", description: "Full scene instructions for Flow Agent" }
      },
      required: ["projectId", "sceneId", "instructions"]
    }
  },
  {
    name: "get_scene_status",
    description: "Get the current generation status of a specific scene.",
    inputSchema: {
      type: "object",
      properties: {
        projectId: { type: "string" },
        sceneId: { type: "string" }
      },
      required: ["projectId", "sceneId"]
    }
  },
  {
    name: "get_project_status",
    description: "Get full project status including all scene statuses and progress.",
    inputSchema: {
      type: "object",
      properties: {
        projectId: { type: "string" }
      },
      required: ["projectId"]
    }
  },
  {
    name: "get_scene_dependencies",
    description: "Get the dependency graph for a project's scenes.",
    inputSchema: {
      type: "object",
      properties: {
        projectId: { type: "string" }
      },
      required: ["projectId"]
    }
  },
  {
    name: "approve_scene",
    description: "Mark a scene as approved after review.",
    inputSchema: {
      type: "object",
      properties: {
        projectId: { type: "string" },
        sceneId: { type: "string" }
      },
      required: ["projectId", "sceneId"]
    }
  },
  {
    name: "regenerate_scene",
    description: "Regenerate a scene's image, video, or both.",
    inputSchema: {
      type: "object",
      properties: {
        projectId: { type: "string" },
        sceneId: { type: "string" },
        type: { type: "string", enum: ["image", "video", "full"], description: "What to regenerate (default: full)" }
      },
      required: ["projectId", "sceneId"]
    }
  },
  {
    name: "export_project",
    description: "Export the project manifest, storyboard and generation report.",
    inputSchema: {
      type: "object",
      properties: {
        projectId: { type: "string" }
      },
      required: ["projectId"]
    }
  },
  {
    name: "assemble_final_video",
    description: "Assemble all completed scene videos into a final movie using FFmpeg (must be installed locally).",
    inputSchema: {
      type: "object",
      properties: {
        projectId: { type: "string" },
        options: {
          type: "object",
          properties: {
            fps: { type: "number", description: "Output frame rate (default 24)" },
            resolution: { type: "string", description: "Output resolution e.g. 1920x1080" },
            musicPath: { type: "string", description: "Absolute path to background music file" },
            voiceoverPath: { type: "string" },
            subtitlesPath: { type: "string" },
            transitions: { type: "boolean" },
            outputFilename: { type: "string" }
          }
        }
      },
      required: ["projectId"]
    }
  },
  {
    name: "update_scene",
    description: "Update a scene's prompt, model, duration, or other fields.",
    inputSchema: {
      type: "object",
      properties: {
        projectId: { type: "string" },
        sceneId: { type: "string" },
        fields: { type: "object", description: "Fields to update on the scene" }
      },
      required: ["projectId", "sceneId", "fields"]
    }
  },
  {
    name: "create_scene",
    description: "Add a single new scene to an existing project.",
    inputSchema: {
      type: "object",
      properties: {
        projectId: { type: "string" },
        sceneNumber: { type: "number" },
        title: { type: "string" },
        imagePrompt: { type: "string" },
        videoPrompt: { type: "string" },
        durationSeconds: { type: "number" },
        aspectRatio: { type: "string" },
        model: { type: "string" },
        dependsOn: { type: "array", items: { type: "string" } }
      },
      required: ["projectId", "sceneNumber", "title", "imagePrompt", "videoPrompt"]
    }
  }
];

async function handleToolCall(name, args) {
  if (name === "flow_get_status") {
    try {
      const status = await makeRequest("GET", "/health");
      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(status, null, 2)
          }
        ]
      };
    } catch (err) {
      return {
        isError: true,
        content: [{ type: "text", text: `Bridge connection error: ${err.message}` }]
      };
    }
  }

  if (name === "flow_generate_image") {
    try {
      const result = await makeRequest("POST", "/api/generate", {
        prompt: args.prompt,
        aspectRatio: args.aspect_ratio || "16:9"
      });

      if (result.error) {
        return {
          isError: true,
          content: [{ type: "text", text: `Flow Generation Error: ${result.error}` }]
        };
      }

      return {
        content: [
          {
            type: "text",
            text: `Successfully generated and downloaded!\nFilename: ${result.filename || "In Downloads folder"}\nMedia URL: ${result.url || "N/A"}`
          }
        ]
      };
    } catch (err) {
      return {
        isError: true,
        content: [{ type: "text", text: `Generation request failed: ${err.message}` }]
      };
    }
  }

  if (name === "create_video_project") {
    const result = await makeRequest("POST", "/api/director/project/create", {
      title: args.title,
      brief: args.brief,
      mode: args.mode || "auto",
      autonomousMode: args.autonomous || false
    });
    return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
  }

  if (name === "create_storyboard") {
    const result = await makeRequest("POST", "/api/director/storyboard/create", {
      projectId: args.projectId,
      scenes: args.scenes
    });
    return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
  }

  if (name === "generate_scene_image") {
    const result = await makeRequest("POST", "/api/director/scene/generate-image", {
      projectId: args.projectId,
      sceneId: args.sceneId
    });
    return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
  }

  if (name === "generate_scene_video") {
    const result = await makeRequest("POST", "/api/director/scene/generate-video", {
      projectId: args.projectId,
      sceneId: args.sceneId,
      videoModel: args.videoModel
    });
    return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
  }

  if (name === "submit_scene_to_flow_agent") {
    const result = await makeRequest("POST", "/api/director/scene/flow-agent", {
      projectId: args.projectId,
      sceneId: args.sceneId,
      instructions: args.instructions
    });
    return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
  }

  if (name === "get_scene_status") {
    const result = await makeRequest("GET", `/api/director/scene/${args.sceneId}/status`);
    return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
  }

  if (name === "get_project_status") {
    const result = await makeRequest("GET", `/api/director/project/${args.projectId}/status`);
    return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
  }

  if (name === "get_scene_dependencies") {
    const result = await makeRequest("GET", `/api/director/project/${args.projectId}/dependencies`);
    return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
  }

  if (name === "approve_scene") {
    const result = await makeRequest("POST", "/api/director/scene/approve", {
      projectId: args.projectId,
      sceneId: args.sceneId
    });
    return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
  }

  if (name === "regenerate_scene") {
    const result = await makeRequest("POST", "/api/director/scene/regenerate", {
      projectId: args.projectId,
      sceneId: args.sceneId,
      type: args.type || "full"
    });
    return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
  }

  if (name === "export_project") {
    const result = await makeRequest("POST", "/api/director/project/export", {
      projectId: args.projectId
    });
    return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
  }

  if (name === "assemble_final_video") {
    const result = await makeRequest("POST", "/api/director/project/assemble", {
      projectId: args.projectId,
      options: args.options || {}
    });
    return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
  }

  if (name === "update_scene") {
    const result = await makeRequest("POST", "/api/director/scene/update", {
      projectId: args.projectId,
      sceneId: args.sceneId,
      fields: args.fields
    });
    return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
  }

  if (name === "create_scene") {
    const result = await makeRequest("POST", "/api/director/scene/create", {
      projectId: args.projectId,
      sceneNumber: args.sceneNumber,
      title: args.title,
      imagePrompt: args.imagePrompt,
      videoPrompt: args.videoPrompt,
      durationSeconds: args.durationSeconds || 8,
      aspectRatio: args.aspectRatio || "16:9",
      model: args.model || "nano-banana-pro",
      dependsOn: args.dependsOn || []
    });
    return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
  }

  throw new Error(`Unknown tool: ${name}`);
}

function sendResponse(id, result, error = null) {
  const payload = { jsonrpc: "2.0", id };
  if (error) {
    payload.error = error;
  } else {
    payload.result = result;
  }
  process.stdout.write(JSON.stringify(payload) + "\n");
}

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
  terminal: false
});

rl.on("line", async (line) => {
  if (!line.trim()) return;

  try {
    const msg = JSON.parse(line);
    const { id, method, params } = msg;

    if (method === "initialize") {
      sendResponse(id, {
        protocolVersion: "2024-11-05",
        capabilities: {
          tools: {}
        },
        serverInfo: {
          name: "flow-antigravity-mcp",
          version: "1.0.0"
        }
      });
      return;
    }

    if (method === "notifications/initialized") {
      return;
    }

    if (method === "tools/list") {
      sendResponse(id, { tools: TOOLS });
      return;
    }

    if (method === "tools/call") {
      try {
        const toolResult = await handleToolCall(params.name, params.arguments || {});
        sendResponse(id, toolResult);
      } catch (err) {
        sendResponse(id, null, {
          code: -32603,
          message: err.message
        });
      }
      return;
    }

    // Ping / generic
    if (method === "ping") {
      sendResponse(id, {});
      return;
    }

    if (id !== undefined) {
      sendResponse(id, null, {
        code: -32601,
        message: `Method not found: ${method}`
      });
    }
  } catch (err) {
    // Malformed JSON
  }
});
