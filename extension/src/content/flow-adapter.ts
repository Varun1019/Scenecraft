import { queryDeep, queryAllDeep } from "./shadow-dom";

export interface AgentDetectionResult {
  isAgentMode: boolean;
  modeName: string;
  inputElement: HTMLElement | null;
  agentFound: boolean;
  reason?: string;
}

export class FlowAdapter {
  private lastGenerationDispatchedTime = 0;

  constructor() {
    window.addEventListener("message", (event) => {
      if (event.data?.type === "FLOW_GENERATION_DISPATCHED") {
        this.lastGenerationDispatchedTime = Date.now();
      }
    });
  }

  isFlowPage(): boolean {
    return (
      window.location.hostname === "flow.google.com" ||
      window.location.hostname.endsWith(".labs.google")
    );
  }

  isAuthenticated(): boolean {
    const accountEl = queryDeep([
      '.header-user-button',
      'a[aria-label*="Google Account" i]',
      'div[aria-label*="Account details" i]',
      '[data-testid*="user-profile"]'
    ]);
    return !!accountEl || document.cookie.includes("SID");
  }

  checkEditorReady(inputElement: HTMLElement | null): boolean {
    if (!inputElement || !inputElement.isConnected) return false;
    const isVisible = inputElement.offsetParent !== null || inputElement.getClientRects().length > 0;
    const isDisabled = (inputElement as any).disabled || inputElement.getAttribute("aria-disabled") === "true";
    return isVisible && !isDisabled;
  }

  detectAgentOrComposer(): AgentDetectionResult {
    // 1. Locate Composer Input (ProseMirror / Contenteditable)
    const composerInput = queryDeep([
      'div.ProseMirror[contenteditable="true"]',
      'div[contenteditable="true"][role="textbox"]',
      'div[contenteditable="true"][aria-label*="create" i]',
      'div[contenteditable="true"][aria-label*="prompt" i]',
      'div[contenteditable="true"][aria-label*="describe" i]',
      'div[contenteditable="true"][placeholder*="create" i]',
      'textarea[placeholder*="create" i]',
      'textarea[placeholder*="prompt" i]',
      'textarea[aria-label*="prompt" i]',
      'textarea[placeholder*="describe" i]',
      'textarea[placeholder*="type" i]',
      'flow-composer div.ProseMirror',
      'flow-prompt-editor div.ProseMirror'
    ]);

    // 2. Locate Agent mode toggle chip
    let agentChip = queryDeep([
      'button.agent-mode-chip',
      'flow-agent-mode-toggle-chip button',
      'button[aria-label*="Agent" i]',
      'button[aria-label*="agent" i]'
    ]) as HTMLElement | null;

    if (!agentChip) {
      const allButtons = queryAllDeep(["button", 'div[role="button"]', '[role="checkbox"]', '[role="switch"]']);
      agentChip = (allButtons.find((btn) => {
        const text = (btn.getAttribute("aria-label") || btn.innerText || btn.textContent || "").toLowerCase().trim();
        return text === "agent" || text.startsWith("agent ") || text.endsWith(" agent");
      }) as HTMLElement) || null;
    }

    if (agentChip) {
      const isChecked =
        agentChip.classList.contains("agent-mode-chip-checked") ||
        agentChip.getAttribute("aria-pressed") === "true";

      // Activate Agent mode if not already active
      if (!isChecked) {
        try {
          agentChip.click();
        } catch (_) {}
      }

      if (composerInput) {
        return {
          isAgentMode: true,
          modeName: "FLOW_AGENT_NATIVE",
          inputElement: composerInput,
          agentFound: true
        };
      }
    }

    if (composerInput) {
      return {
        isAgentMode: false,
        modeName: "FLOW_COMPOSER_PROSEMIRROR",
        inputElement: composerInput,
        agentFound: false,
        reason: "Flow Agent chip not active; using Director Composer"
      };
    }

    return {
      isAgentMode: false,
      modeName: "NONE",
      inputElement: null,
      agentFound: false,
      reason: "No prompt editor element located on Flow page"
    };
  }

  async ensureInProject(): Promise<boolean> {
    // 1. Check if gallery / modal / asset panel needs closing
    const closeOrBackBtn = queryAllDeep(["button", 'div[role="button"]']).find((btn) => {
      const label = (btn.getAttribute("aria-label") || btn.innerText || btn.textContent || "").trim().toLowerCase();
      return (
        label === "done" ||
        label === "close" ||
        label === "back" ||
        label === "arrow_back" ||
        label.includes("close")
      );
    });
    if (closeOrBackBtn) {
      try { (closeOrBackBtn as HTMLElement).click(); } catch (_) {}
      await new Promise((r) => setTimeout(r, 600));
    }

    let detection = this.detectAgentOrComposer();
    if (detection.inputElement) return true;

    // 2. Try Add media menu button to reveal composer
    const addMediaBtn = queryAllDeep(["button", 'div[role="button"]']).find((btn) => {
      const label = (btn.getAttribute("aria-label") || btn.innerText || btn.textContent || "").trim().toLowerCase();
      return label === "add media menu" || label === "add media" || label === "+ add";
    });
    if (addMediaBtn) {
      try { (addMediaBtn as HTMLElement).click(); } catch (_) {}
      await new Promise((r) => setTimeout(r, 600));
    }

    detection = this.detectAgentOrComposer();
    if (detection.inputElement) return true;

    // 3. Search for New Project button if on homepage
    const buttons = queryAllDeep([
      "button",
      "a",
      'div[role="button"]',
      '[data-testid*="create"]'
    ]);

    const newBtn = buttons.find((btn) => {
      const label = (btn.getAttribute("aria-label") || btn.innerText || "").trim().toLowerCase();
      return (
        label.includes("new project") ||
        label.includes("create project") ||
        label === "create" ||
        label === "+ new" ||
        label.includes("start project")
      );
    });

    if (newBtn) {
      newBtn.click();
      for (let i = 0; i < 20; i++) {
        await new Promise((r) => setTimeout(r, 500));
        if (this.detectAgentOrComposer().inputElement) return true;
      }
    }

    return Boolean(this.detectAgentOrComposer().inputElement);
  }

  /**
   * Sets text into ProseMirror or textarea with multi-strategy approach.
   * Dispatches via Main World, ClipboardEvent DataTransfer, and input events.
   */
  async insertScriptText(element: HTMLElement, text: string): Promise<boolean> {
    element.focus();
    await new Promise((r) => setTimeout(r, 100));

    // For standard Textarea / Input
    if (element instanceof HTMLTextAreaElement || element instanceof HTMLInputElement) {
      const proto = element instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
      const setter = Object.getOwnPropertyDescriptor(proto, "value")?.set;
      if (setter) {
        setter.call(element, text);
      } else {
        element.value = text;
      }
      element.dispatchEvent(new InputEvent("input", { bubbles: true, data: text, inputType: "insertText" }));
      element.dispatchEvent(new Event("change", { bubbles: true }));
      return (element.value || "").trim().length > 0;
    }

    // For ProseMirror / contenteditable
    if (element.isContentEditable) {
      const isRetained = () => (element.textContent || "").trim().length > 0;

      // 1. Post to Main World to insert text via ProseMirror EditorView
      try {
        const callId = "insert_" + Date.now();
        const mainRes = await new Promise<any>((resolve) => {
          const handler = (ev: MessageEvent) => {
            if (ev.data?.type === "FLOW_MAIN_INSERT_RESULT" && ev.data?.callId === callId) {
              window.removeEventListener("message", handler);
              resolve(ev.data);
            }
          };
          window.addEventListener("message", handler);
          window.postMessage({ type: "FLOW_MAIN_INSERT_TEXT", text, callId }, "*");
          setTimeout(() => {
            window.removeEventListener("message", handler);
            resolve(null);
          }, 800);
        });
        if (mainRes?.success || isRetained()) return true;
      } catch (_) {}

      // 2. Select Range inside ProseMirror
      const selectAll = () => {
        const sel = window.getSelection();
        const range = document.createRange();
        range.selectNodeContents(element);
        sel?.removeAllRanges();
        sel?.addRange(range);
        document.dispatchEvent(new Event("selectionchange"));
      };

      for (let attempt = 1; attempt <= 3; attempt++) {
        selectAll();

        // Try Paste event with DataTransfer
        try {
          const dt = new DataTransfer();
          dt.setData("text/plain", text);
          const pasteEvent = new ClipboardEvent("paste", {
            clipboardData: dt,
            bubbles: true,
            cancelable: true
          });
          element.dispatchEvent(pasteEvent);
          await new Promise((r) => setTimeout(r, 200));
          if (isRetained()) return true;
        } catch (_) {}

        // Try beforeinput event
        try {
          selectAll();
          const beforeInput = new InputEvent("beforeinput", {
            inputType: "insertText",
            data: text,
            bubbles: true,
            cancelable: true
          });
          element.dispatchEvent(beforeInput);
          await new Promise((r) => setTimeout(r, 200));
          if (isRetained()) return true;
        } catch (_) {}

        // Try execCommand
        try {
          selectAll();
          document.execCommand("insertText", false, text);
          await new Promise((r) => setTimeout(r, 200));
          if (isRetained()) return true;
        } catch (_) {}

        // Fallback: Direct textContent + input event
        try {
          element.textContent = text;
          element.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertText", data: text }));
          await new Promise((r) => setTimeout(r, 200));
          if (isRetained()) return true;
        } catch (_) {}

        element.focus();
        await new Promise((r) => setTimeout(r, 200 * attempt));
      }

      return isRetained();
    }

    return false;
  }

  /**
   * Helper: Validates if an element is genuinely the Generate / Submit button
   * and NOT a mode chip, Agent toggle, or other control.
   */
  isRealGenerateButton(b: HTMLElement): boolean {
    if (
      b.classList.contains("agent-mode-chip") ||
      b.classList.contains("agent-mode-toggle") ||
      b.tagName === "MAT-CHIP-OPTION" ||
      b.tagName === "MAT-CHIP" ||
      b.getAttribute("role") === "switch" ||
      b.getAttribute("role") === "checkbox"
    ) {
      return false;
    }
    const label = (b.getAttribute("aria-label") || b.innerText || b.textContent || "").toLowerCase().trim();
    const html = (b.innerHTML || "").toLowerCase();
    if (
      label === "agent" ||
      label.startsWith("agent ") ||
      label.endsWith(" agent") ||
      label.includes("create tool") ||
      label.includes("new project") ||
      label.includes("banana") ||
      label.includes("veo") ||
      label.includes("aspect") ||
      label.includes("16:9") ||
      label.includes("9:16") ||
      label.includes("1:1")
    ) {
      return false;
    }

    return (
      label.includes("start generation") ||
      label.includes("generate") ||
      label.includes("submit") ||
      label.includes("send") ||
      label === "arrow_forward" ||
      html.includes("arrow_forward") ||
      b.classList.contains("generate-icon-button")
    );
  }

  /**
   * Locates the active Generate button using accessible properties and UI structure.
   */
  findSubmitButton(): HTMLButtonElement | null {
    // 1. Exact generate button selector first
    const specificBtn = queryDeep([
      'button[aria-label="Start generation" i]',
      'button[aria-label*="Start generation" i]',
      'button[aria-label*="Generate" i]',
      'button.generate-icon-button',
      'flow-generate-icon-button button',
      'button[type="submit"]'
    ]) as HTMLButtonElement | null;

    if (specificBtn && this.isRealGenerateButton(specificBtn)) return specificBtn;

    // 2. Search outward from composer input
    const composer = queryDeep([
      'div.ProseMirror[contenteditable="true"]',
      'textarea[placeholder*="create" i]',
      'textarea[placeholder*="prompt" i]'
    ]);
    if (composer) {
      let curr: HTMLElement | null = composer;
      for (let i = 0; i < 7 && curr; i++) {
        const btns = Array.from(curr.querySelectorAll('button, div[role="button"]')) as HTMLButtonElement[];
        const match = btns.find((b) => this.isRealGenerateButton(b));
        if (match) return match;
        curr = curr.parentElement;
      }
    }

    // 3. Fallback across all buttons
    const allButtons = queryAllDeep(["button", 'div[role="button"]']);
    return (allButtons.find((btn) => this.isRealGenerateButton(btn)) as HTMLButtonElement | null) || null;
  }

  /**
   * Waits for Generate button to become genuinely enabled.
   */
  async waitForGenerateReady(timeoutMs = 5000): Promise<{
    ready: boolean;
    btn?: HTMLButtonElement;
    error?: string;
  }> {
    const startTime = Date.now();
    let btn: HTMLButtonElement | null = null;

    while (Date.now() - startTime < timeoutMs) {
      btn = this.findSubmitButton();
      if (btn) {
        const isDisabled = btn.disabled || btn.getAttribute("aria-disabled") === "true";
        if (!isDisabled) {
          return { ready: true, btn };
        }
      }
      await new Promise((r) => setTimeout(r, 150));
    }

    if (!btn) {
      return { ready: false, error: "GENERATE_BUTTON_NOT_FOUND" };
    }

    return { ready: false, btn, error: "GENERATE_BUTTON_DISABLED" };
  }

  /**
   * Triggers submission using trusted user-interaction and native main-world dispatch.
   */
  async triggerSubmit(btn: HTMLButtonElement, composer: HTMLElement, _scriptText: string): Promise<{ success: boolean; error?: string }> {
    try {
      btn.scrollIntoView({ block: "center", inline: "center", behavior: "instant" });
      btn.focus();
      await new Promise((r) => setTimeout(r, 60));

      const btnRect = btn.getBoundingClientRect();
      const composerRect = composer.getBoundingClientRect();

      const btnX = Math.round(btnRect.left + btnRect.width / 2);
      const btnY = Math.round(btnRect.top + btnRect.height / 2);
      const editorX = Math.round(composerRect.left + composerRect.width / 2);
      const editorY = Math.round(composerRect.top + composerRect.height / 2);

      // 1. Dispatch Main-World Submission via FLOW_MAIN_CLICK_GENERATE
      const callId = "click_" + Date.now();
      window.postMessage({ type: "FLOW_MAIN_CLICK_GENERATE", callId }, "*");

      // 2. Synthetic pointer and mouse event chain on button
      const eventOpts: any = {
        bubbles: true,
        cancelable: true,
        composed: true,
        clientX: btnX,
        clientY: btnY,
        button: 0,
        view: window
      };

      btn.dispatchEvent(new PointerEvent("pointerover", eventOpts));
      btn.dispatchEvent(new PointerEvent("pointerenter", eventOpts));
      btn.dispatchEvent(new PointerEvent("pointerdown", eventOpts));
      btn.dispatchEvent(new MouseEvent("mousedown", eventOpts));
      btn.dispatchEvent(new PointerEvent("pointerup", eventOpts));
      btn.dispatchEvent(new MouseEvent("mouseup", eventOpts));
      btn.dispatchEvent(new MouseEvent("click", eventOpts));
      btn.click();

      // Click inner icon or span
      const icon = btn.querySelector("mat-icon, span, svg");
      if (icon) {
        try { (icon as HTMLElement).click(); } catch (_) {}
      }

      // Enter key on composer
      composer.dispatchEvent(
        new KeyboardEvent("keydown", {
          key: "Enter",
          code: "Enter",
          keyCode: 13,
          which: 13,
          bubbles: true,
          cancelable: true,
          composed: true
        })
      );
      composer.dispatchEvent(
        new KeyboardEvent("keyup", {
          key: "Enter",
          code: "Enter",
          keyCode: 13,
          which: 13,
          bubbles: true,
          cancelable: true,
          composed: true
        })
      );

      // 3. Trusted Chrome Debugger Click (using verified button coordinates)
      try {
        await new Promise<any>((resolve) => {
          chrome.runtime.sendMessage(
            {
              action: "submit_trusted",
              btnX,
              btnY,
              editorX,
              editorY
            },
            (res) => resolve(res || { ok: !chrome.runtime.lastError })
          );
        });
      } catch (_) {}

      return { success: true };
    } catch (err: any) {
      return { success: false, error: err.message };
    }
  }

  /**
   * Verifies actual generation acceptance. Never reports success prematurely.
   */
  async verifySubmissionAccepted(timeoutMs = 9000): Promise<{
    accepted: boolean;
    evidence?: string;
  }> {
    const startTime = Date.now();
    const startDispatchedTime = this.lastGenerationDispatchedTime;

    const initialComposer = queryDeep(['div.ProseMirror[contenteditable="true"]', 'textarea']);
    const hadInitialText = ((initialComposer?.textContent || (initialComposer as any)?.value || "").trim().length > 0);

    while (Date.now() - startTime < timeoutMs) {
      // 1. Authoritative: Outgoing generation network request intercepted
      if (this.lastGenerationDispatchedTime > startDispatchedTime) {
        return { accepted: true, evidence: "NETWORK_GENERATION_DISPATCHED" };
      }

      // 2. Generate button disabled or changed to cancel/stop
      const btn = this.findSubmitButton();
      const isDisabled = btn?.disabled || btn?.getAttribute("aria-disabled") === "true";
      const btnLabel = (btn?.getAttribute("aria-label") || btn?.innerText || "").toLowerCase();
      if (isDisabled || btnLabel.includes("stop") || btnLabel.includes("cancel")) {
        return { accepted: true, evidence: "BUTTON_TRANSITION_DISABLED" };
      }

      // 3. Generation loading indicator / spinner in DOM
      const loading = queryDeep([
        'mat-spinner',
        'mat-progress-spinner',
        'mat-progress-bar',
        '.loading-spinner',
        '[role="progressbar"]',
        'div[aria-label*="loading" i]',
        'div[aria-label*="generating" i]'
      ]);
      if (loading) {
        return { accepted: true, evidence: "LOADING_SPINNER_DETECTED" };
      }

      // 4. Composer cleared by Flow after having text
      if (hadInitialText) {
        const composer = queryDeep(['div.ProseMirror[contenteditable="true"]', 'textarea']);
        if (composer) {
          const currentText = (composer.textContent || (composer as HTMLTextAreaElement).value || "").trim();
          if (currentText === "" && Date.now() - startTime > 400) {
            return { accepted: true, evidence: "COMPOSER_CLEARED_BY_FLOW" };
          }
        }
      }

      await new Promise((r) => setTimeout(r, 200));
    }

    return { accepted: false };
  }
}
