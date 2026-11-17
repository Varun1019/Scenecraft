import { queryDeep, queryAllDeep } from "./shadow-dom";

export interface AgentCapabilities {
  available: boolean;
  hasAgentInput: boolean;
  hasAgentButton: boolean;
  detectedElements: string[];
}

export class FlowAgentAdapter {
  /** Detects whether the Google Flow Agent UI is currently available. */
  detectAgentMode(): AgentCapabilities {
    const detected: string[] = [];

    // Look for Agent-specific UI elements
    const agentSelectors = [
      '[aria-label*="agent" i]',
      '[data-testid*="agent"]',
      '[class*="agent"]',
      '[id*="agent"]',
      'button[aria-label*="Agent" i]',
      'div[role="button"][aria-label*="Agent" i]'
    ];

    const allButtons = queryAllDeep(["button", 'div[role="button"]', "a"]);
    const agentButton = allButtons.find((el) => {
      const label = (el.getAttribute("aria-label") || el.textContent || "").toLowerCase();
      return label.includes("agent") || label.includes("flow agent");
    });

    if (agentButton) detected.push("agent_button");

    // Look for agent-specific text inputs
    const agentInput = queryDeep([
      'textarea[placeholder*="agent" i]',
      'input[placeholder*="agent" i]',
      '[aria-label*="agent input" i]'
    ]);
    if (agentInput) detected.push("agent_input");

    // Check sidebar for Agent tab/section
    const sidebar = queryAllDeep(['nav a', 'nav button', '[role="tab"]', '[role="menuitem"]']);
    const agentTab = sidebar.find((el) => {
      const label = (el.textContent || el.getAttribute("aria-label") || "").toLowerCase();
      return label.trim() === "agent" || label.includes("flow agent");
    });
    if (agentTab) detected.push("agent_tab");

    return {
      available: detected.length > 0,
      hasAgentInput: detected.includes("agent_input"),
      hasAgentButton: detected.includes("agent_button"),
      detectedElements: detected
    };
  }

  /** Attempts to activate Agent mode by clicking the Agent tab/button. */
  async activateAgentMode(): Promise<boolean> {
    const allButtons = queryAllDeep(["button", 'div[role="button"]', "a", '[role="tab"]']);
    const agentBtn = allButtons.find((el) => {
      const label = (el.getAttribute("aria-label") || el.textContent || "").toLowerCase().trim();
      return label === "agent" || label.includes("flow agent");
    });

    if (!agentBtn) return false;
    (agentBtn as HTMLElement).click();
    await new Promise((r) => setTimeout(r, 1000));
    return true;
  }

  /** Submits a structured instruction to the Flow Agent. */
  async submitAgentInstruction(instruction: string): Promise<boolean> {
    // Try to find the agent input field after activation
    const agentInput = queryDeep([
      'textarea[placeholder*="agent" i]',
      'textarea[placeholder*="message" i]',
      '[contenteditable="true"]',
      'textarea'
    ]);

    if (!agentInput) return false;

    agentInput.focus();
    if (agentInput instanceof HTMLTextAreaElement) {
      agentInput.value = instruction;
      agentInput.dispatchEvent(new Event("input", { bubbles: true }));
      agentInput.dispatchEvent(new Event("change", { bubbles: true }));
    } else if ((agentInput as HTMLElement).isContentEditable) {
      (agentInput as HTMLElement).innerText = instruction;
      agentInput.dispatchEvent(new Event("input", { bubbles: true }));
    }

    await new Promise((r) => setTimeout(r, 400));

    // Try to submit
    const form = agentInput.closest("form");
    if (form) {
      const submitBtn = form.querySelector('button[type="submit"]') as HTMLButtonElement | null;
      if (submitBtn && !submitBtn.disabled) {
        submitBtn.click();
        return true;
      }
    }

    const allButtons = queryAllDeep(["button", 'div[role="button"]']);
    const sendBtn = allButtons.find((b) => {
      const label = (b.getAttribute("aria-label") || b.textContent || "").toLowerCase();
      return label.includes("send") || label.includes("submit") || label.includes("run");
    });
    if (sendBtn) {
      (sendBtn as HTMLElement).click();
      return true;
    }

    // Keyboard fallback
    agentInput.dispatchEvent(
      new KeyboardEvent("keydown", { bubbles: true, cancelable: true, key: "Enter", code: "Enter", keyCode: 13 })
    );
    return true;
  }

  /** Builds a structured scene instruction string for the Flow Agent. */
  buildSceneInstruction(scene: {
    sceneNumber: number;
    title: string;
    description: string;
    imagePrompt: string;
    videoPrompt: string;
    cameraInstructions: string;
    durationSeconds: number;
    aspectRatio: string;
  }): string {
    return `[Scene ${scene.sceneNumber}: ${scene.title}]

Description: ${scene.description}

Please generate:
1. A high-quality image: ${scene.imagePrompt}
2. A ${scene.durationSeconds}-second video: ${scene.videoPrompt}

Camera: ${scene.cameraInstructions}
Aspect ratio: ${scene.aspectRatio}

Maintain visual consistency with previous scenes. Use cinematic lighting and professional framing.`;
  }
}
