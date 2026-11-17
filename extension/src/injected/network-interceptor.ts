// Flow Connect 2.0 - Fast & Lightweight Page-World Network Interceptor & Native Submitter
(function () {
  const MEDIA_REGEX = /https:\/\/(?:flow-content\.google\/(?:image|video)\/|(?:video|content)\.googleusercontent\.com\/(?:image|video)\/)[^"',\s<>]+/g;
  const REDIRECT_REGEX = /\/media\.getMediaUrlRedirect(?:\?|$)/i;
  const API_ENDPOINT_FILTER = /(?:flow\.google\.com|labs\.google|\/api\/|\/media|\/generate|\/predict|\/stream)/i;
  const GENERATION_DISPATCH_FILTER = /(?:\/generate|\/predict|\/stream|\/batch|\/run|\/createTool)/i;
  const seenUrls = new Set<string>();

  function isIgnoredUrl(url: string): boolean {
    if (!url) return true;
    return (
      url.includes("/ogw/") ||
      url.includes("profile") ||
      url.includes("account") ||
      url.includes("avatar") ||
      url.includes("icon") ||
      url.includes("=s32") ||
      url.includes("=s64") ||
      url.includes("=s128")
    );
  }

  function extractContextualMedia(text: string): Array<{ url: string; promptSnippet?: string }> {
    if (!text || typeof text !== "string" || text.length < 20) return [];

    const results: Array<{ url: string; promptSnippet?: string }> = [];
    try {
      if (text.startsWith("{") || text.startsWith("[")) {
        try {
          const parsed = JSON.parse(text);
          findMediaInObject(parsed, results);
          if (results.length > 0) return results;
        } catch (_) {}
      }

      const unescaped = text
        .replace(/\\u([0-9a-fA-F]{4})/g, (_, r) => String.fromCharCode(parseInt(r, 16)))
        .split("\\")
        .join("");
      const matches = unescaped.match(MEDIA_REGEX);
      if (matches) {
        for (const url of Array.from(new Set(matches))) {
          if (!isIgnoredUrl(url)) {
            results.push({ url });
          }
        }
      }
    } catch (_) {}

    return results;
  }

  function findMediaInObject(obj: any, results: Array<{ url: string; promptSnippet?: string }>, depth = 0) {
    if (!obj || depth > 8 || typeof obj !== "object") return;

    if (Array.isArray(obj)) {
      for (const item of obj) {
        findMediaInObject(item, results, depth + 1);
      }
      return;
    }

    let localPrompt: string | undefined;
    for (const key of ["prompt", "text", "caption", "label", "sceneTitle", "description"]) {
      if (typeof obj[key] === "string" && obj[key].length > 3) {
        localPrompt = obj[key].slice(0, 150);
        break;
      }
    }

    for (const key in obj) {
      const val = obj[key];
      if (typeof val === "string" && (val.includes("flow-content.google") || val.includes("googleusercontent.com"))) {
        if (!isIgnoredUrl(val) && !seenUrls.has(val)) {
          results.push({ url: val, promptSnippet: localPrompt });
        }
      } else if (typeof val === "object") {
        findMediaInObject(val, results, depth + 1);
      }
    }
  }

  function notifyMedia(item: { url: string; promptSnippet?: string }) {
    if (!item.url || seenUrls.has(item.url) || isIgnoredUrl(item.url)) return;
    seenUrls.add(item.url);

    window.postMessage(
      {
        type: "FLOW_MEDIA_READY",
        url: item.url,
        metadata: {
          promptSnippet: item.promptSnippet,
          source: "network"
        }
      },
      window.location.origin
    );
  }

  function notifyGenerationDispatched(url: string) {
    window.postMessage(
      {
        type: "FLOW_GENERATION_DISPATCHED",
        url,
        timestamp: Date.now()
      },
      window.location.origin
    );
  }

  // Intercept Fetch API
  const origFetch = window.fetch;
  window.fetch = async function (...args) {
    const reqUrl = typeof args[0] === "string" ? args[0] : (args[0] as Request)?.url || "";
    if (GENERATION_DISPATCH_FILTER.test(reqUrl)) {
      notifyGenerationDispatched(reqUrl);
    }

    const response = await origFetch.apply(this, args);
    try {
      if (REDIRECT_REGEX.test(reqUrl) && response.status === 200) {
        notifyMedia({ url: response.url || reqUrl });
      }

      if (API_ENDPOINT_FILTER.test(reqUrl)) {
        const clone = response.clone();
        clone
          .text()
          .then((text) => {
            const items = extractContextualMedia(text);
            items.forEach(notifyMedia);
          })
          .catch(() => {});
      }
    } catch (_) {}
    return response;
  };

  // Intercept XMLHttpRequest
  const origOpen = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function (...args: any[]) {
    const url = String(args[1] || "");
    if (GENERATION_DISPATCH_FILTER.test(url)) {
      notifyGenerationDispatched(url);
    }

    if (API_ENDPOINT_FILTER.test(url) || REDIRECT_REGEX.test(url)) {
      this.addEventListener("load", function () {
        try {
          if (REDIRECT_REGEX.test(url) && this.status === 200) {
            notifyMedia({ url: this.responseURL || url });
          }
          const items = extractContextualMedia(this.responseText);
          items.forEach(notifyMedia);
        } catch (_) {}
      });
    }
    return origOpen.apply(this, args as any);
  };

  // Helper: Find Generate Button in Main World
  function isGenerateButtonElement(b: HTMLElement): boolean {
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
      label.includes("banana") ||
      label.includes("veo") ||
      label.includes("aspect") ||
      label.includes("16:9") ||
      label.includes("9:16") ||
      label.includes("1:1") ||
      label.includes("create tool") ||
      label.includes("new project")
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

  function findMainGenerateButton(): HTMLButtonElement | null {
    const composer = (document.querySelector('div.ProseMirror[contenteditable="true"]') ||
      document.querySelector('div[contenteditable="true"]') ||
      document.querySelector("textarea")) as HTMLElement | null;

    if (composer) {
      let curr: HTMLElement | null = composer;
      for (let i = 0; i < 7 && curr; i++) {
        const btns = Array.from(curr.querySelectorAll('button, div[role="button"]')) as HTMLButtonElement[];
        const found = btns.find(isGenerateButtonElement);
        if (found) return found;
        curr = curr.parentElement;
      }
    }

    const allButtons = Array.from(document.querySelectorAll('button, div[role="button"]')) as HTMLButtonElement[];
    return allButtons.find(isGenerateButtonElement) || null;
  }

  function executeInsertText(composer: HTMLElement, text: string): boolean {
    composer.focus();
    let inserted = false;

    // 1. Direct ProseMirror EditorView Transaction with Multiline Paragraphs
    const pmView = (composer as any).pmViewDesc?.view;
    if (pmView && pmView.state && pmView.dispatch) {
      try {
        const schema = pmView.state.schema;
        if (!text.includes("\n")) {
          const tr = pmView.state.tr.replaceWith(0, pmView.state.doc.content.size, schema.text(text));
          pmView.dispatch(tr);
          inserted = true;
        } else {
          const lines = text.split(/\r?\n/);
          const pType = schema.nodes.paragraph || Object.values(schema.nodes).find((n: any) => n?.isBlock && n?.name !== "doc");
          const nodes: any[] = [];
          for (const l of lines) {
            if (l.length > 0) {
              nodes.push(pType ? (pType as any).create(null, schema.text(l)) : schema.text(l));
            } else if (pType) {
              nodes.push((pType as any).create());
            }
          }
          if (nodes.length > 0) {
            const tr = pmView.state.tr.replaceWith(0, pmView.state.doc.content.size, nodes);
            pmView.dispatch(tr);
            inserted = true;
          }
        }
      } catch (pmErr) {
        console.warn("[Flow Main] ProseMirror dispatch fallback:", pmErr);
      }
    }

    // 2. Main-World Clipboard Paste (Secondary)
    if (!inserted) {
      try {
        const sel = window.getSelection();
        const range = document.createRange();
        range.selectNodeContents(composer);
        sel?.removeAllRanges();
        sel?.addRange(range);

        const dt = new DataTransfer();
        dt.setData("text/plain", text);
        const pasteEvent = new ClipboardEvent("paste", { clipboardData: dt, bubbles: true, cancelable: true });
        composer.dispatchEvent(pasteEvent);
        inserted = (composer.textContent || "").trim().length > 0;
      } catch (_) {}
    }

    // 3. Fallback execCommand
    if (!inserted) {
      try {
        document.execCommand("selectAll", false, undefined);
        document.execCommand("insertText", false, text);
        inserted = (composer.textContent || "").trim().length > 0;
      } catch (_) {}
    }

    // 4. Fallback direct textContent
    if (!inserted && (composer.textContent || "").trim().length === 0) {
      composer.textContent = text;
      inserted = true;
    }

    // Dispatch DOM Input & Change events to notify Angular / React listeners
    try {
      composer.dispatchEvent(new InputEvent("beforeinput", { bubbles: true, cancelable: true, composed: true, inputType: "insertText", data: text }));
      composer.dispatchEvent(new InputEvent("input", { bubbles: true, composed: true, inputType: "insertText", data: text }));
      composer.dispatchEvent(new Event("change", { bubbles: true, composed: true }));
    } catch (_) {}

    // Trigger Angular Zone change detection if present
    try {
      if ((window as any).Zone?.current?.run) {
        (window as any).Zone.current.run(() => {});
      }
    } catch (_) {}

    return (composer.textContent || "").trim().length > 0;
  }

  function executeClickGenerate(): { success: boolean; error?: string; coords?: { x: number; y: number } } {
    const btn = findMainGenerateButton();
    if (!btn) {
      return { success: false, error: "GENERATE_BUTTON_NOT_FOUND" };
    }

    const isDisabled = btn.disabled || btn.getAttribute("aria-disabled") === "true";
    if (isDisabled) {
      return { success: false, error: "GENERATE_BUTTON_DISABLED" };
    }

    btn.scrollIntoView({ block: "center", inline: "center", behavior: "instant" });
    btn.focus();

    const rect = btn.getBoundingClientRect();
    const clickOpts: any = {
      bubbles: true,
      cancelable: true,
      composed: true,
      view: window,
      clientX: Math.round(rect.left + rect.width / 2),
      clientY: Math.round(rect.top + rect.height / 2),
      button: 0
    };

    btn.dispatchEvent(new PointerEvent("pointerover", clickOpts));
    btn.dispatchEvent(new PointerEvent("pointerenter", clickOpts));
    btn.dispatchEvent(new PointerEvent("pointerdown", clickOpts));
    btn.dispatchEvent(new MouseEvent("mousedown", clickOpts));
    btn.dispatchEvent(new PointerEvent("pointerup", clickOpts));
    btn.dispatchEvent(new MouseEvent("mouseup", clickOpts));
    btn.dispatchEvent(new MouseEvent("click", clickOpts));
    btn.click();

    // Click inner icon or span if present
    const icon = btn.querySelector("mat-icon, span, svg");
    if (icon) {
      try { (icon as HTMLElement).click(); } catch (_) {}
    }

    // Also trigger Enter on composer
    const composer = (document.querySelector('div.ProseMirror[contenteditable="true"]') ||
      document.querySelector('div[contenteditable="true"]') ||
      document.querySelector("textarea")) as HTMLElement | null;
    if (composer) {
      composer.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", code: "Enter", keyCode: 13, which: 13, bubbles: true, composed: true }));
      composer.dispatchEvent(new KeyboardEvent("keyup", { key: "Enter", code: "Enter", keyCode: 13, which: 13, bubbles: true, composed: true }));
    }

    // Trigger Angular Zone change detection
    try {
      if ((window as any).Zone?.current?.run) {
        (window as any).Zone.current.run(() => {});
      }
    } catch (_) {}

    return {
      success: true,
      coords: { x: clickOpts.clientX, y: clickOpts.clientY }
    };
  }

  // Main-World Native Editor & Button Controller
  window.addEventListener("message", (event) => {
    if (event.source !== window) return;

    // 1. Dedicated Text Insertion
    if (event.data?.type === "FLOW_MAIN_INSERT_TEXT") {
      const { text, callId } = event.data;
      const composer = (document.querySelector('div.ProseMirror[contenteditable="true"]') ||
        document.querySelector('div[contenteditable="true"]') ||
        document.querySelector("textarea")) as HTMLElement | null;

      if (!composer) {
        window.postMessage({ type: "FLOW_MAIN_INSERT_RESULT", callId, success: false, error: "EDITOR_NOT_FOUND" }, window.location.origin);
        return;
      }

      const ok = executeInsertText(composer, text);
      const len = (composer.textContent || "").trim().length;
      window.postMessage({ type: "FLOW_MAIN_INSERT_RESULT", callId, success: ok, length: len }, window.location.origin);
      return;
    }

    // 2. Dedicated Generate Button Click
    if (event.data?.type === "FLOW_MAIN_CLICK_GENERATE") {
      const { callId } = event.data;
      const result = executeClickGenerate();
      window.postMessage({ type: "FLOW_MAIN_CLICK_RESULT", callId, ...result }, window.location.origin);
      return;
    }

    // 3. Combined Submit (Legacy fallback)
    if (event.data?.type === "FLOW_MAIN_SUBMIT") {
      const { text, callId } = event.data;
      try {
        const composer = (document.querySelector('div.ProseMirror[contenteditable="true"]') ||
          document.querySelector('div[contenteditable="true"]') ||
          document.querySelector("textarea")) as HTMLElement | null;

        if (!composer) {
          window.postMessage({ type: "FLOW_MAIN_SUBMIT_RESULT", callId, success: false, error: "EDITOR_NOT_FOUND" }, window.location.origin);
          return;
        }

        executeInsertText(composer, text);
        const clickRes = executeClickGenerate();
        window.postMessage({ type: "FLOW_MAIN_SUBMIT_RESULT", callId, ...clickRes }, window.location.origin);
      } catch (err: any) {
        window.postMessage({ type: "FLOW_MAIN_SUBMIT_RESULT", callId, success: false, error: err.message }, window.location.origin);
      }
      return;
    }
  });

  console.log("[Flow Automation] Lightweight network media interceptor active.");
})();
