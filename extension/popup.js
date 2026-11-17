const promptInput = document.getElementById("promptInput");
const charCount = document.getElementById("charCount");
const generateBtn = document.getElementById("generateBtn");
const btnText = document.getElementById("btnText");
const btnIcon = document.getElementById("btnIcon");
const activityText = document.getElementById("activityText");
const bridgeDot = document.getElementById("bridgeDot");
const bridgeText = document.getElementById("bridgeText");
const flowDot = document.getElementById("flowDot");
const flowText = document.getElementById("flowText");
const historyList = document.getElementById("historyList");
const aspectOptions = document.querySelectorAll(".aspect-option");
const styleChips = document.querySelectorAll(".chip");

let selectedAspect = "16:9";

aspectOptions.forEach((opt) => {
  opt.addEventListener("click", () => {
    aspectOptions.forEach((o) => o.classList.remove("active"));
    opt.classList.add("active");
    selectedAspect = opt.dataset.aspect;
  });
});

styleChips.forEach((chip) => {
  chip.addEventListener("click", () => {
    const current = promptInput.value.trim();
    const style = chip.dataset.style;
    if (current) {
      promptInput.value = `${current}, ${style}`;
    } else {
      promptInput.value = style;
    }
    updateCharCount();
  });
});

promptInput.addEventListener("input", updateCharCount);
function updateCharCount() {
  charCount.textContent = promptInput.value.length;
}

async function checkStatus() {
  chrome.runtime.sendMessage({ action: "get_status" }, (res) => {
    if (chrome.runtime.lastError) return;

    if (res && res.bridgeConnected) {
      bridgeDot.className = "status-dot active";
      bridgeText.textContent = "Bridge: Connected";
    } else {
      bridgeDot.className = "status-dot";
      bridgeText.textContent = "Bridge: Offline (8792)";
    }

    if (res && res.extensionStatus) {
      if (res.activeJob) {
        activityText.textContent = `Antigravity: "${res.activeJob.prompt.slice(0, 25)}..."`;
      } else if (res.extensionStatus.message) {
        activityText.textContent = res.extensionStatus.message;
      }
    }
  });

  const tabs = await chrome.tabs.query({ url: "*://flow.google.com/*" });
  const labsTabs = await chrome.tabs.query({ url: "*://labs.google/*" });
  if ((tabs && tabs.length > 0) || (labsTabs && labsTabs.length > 0)) {
    flowDot.className = "status-dot active";
    flowText.textContent = "Flow Tab: Ready";
  } else {
    flowDot.className = "status-dot error";
    flowText.textContent = "Flow Tab: Not Found";
  }
}

async function renderHistory() {
  const { history = [] } = await chrome.storage.local.get("history");
  if (!history || history.length === 0) {
    historyList.innerHTML = `<div style="color: var(--text-muted); font-size: 11px; text-align: center; padding: 10px;">No recent generations yet</div>`;
    return;
  }

  historyList.innerHTML = history
    .map(
      (item) => `
    <div class="history-item">
      <span class="history-prompt" title="${item.prompt}">${item.prompt}</span>
      <span class="history-time">${item.timestamp}</span>
    </div>
  `
    )
    .join("");
}

generateBtn.addEventListener("click", async () => {
  const prompt = promptInput.value.trim();
  if (!prompt) {
    activityText.textContent = "Error: Please write a prompt first.";
    return;
  }

  generateBtn.disabled = true;
  btnIcon.textContent = "⏳";
  btnText.textContent = "Sending to Flow...";
  activityText.textContent = "Locating Flow composer...";

  chrome.runtime.sendMessage(
    {
      action: "send_prompt_to_tab",
      prompt: prompt,
      aspectRatio: selectedAspect
    },
    (res) => {
      if (chrome.runtime.lastError || !res?.success) {
        generateBtn.disabled = false;
        btnIcon.textContent = "⚡";
        btnText.textContent = "Generate & Auto-Download";
        activityText.textContent =
          "Error: " + (chrome.runtime.lastError?.message || res?.error || "Submission failed");
      } else {
        btnText.textContent = "Generating in Flow...";
        activityText.textContent = "Prompt submitted! Intercepting media & download...";

        setTimeout(() => {
          generateBtn.disabled = false;
          btnIcon.textContent = "⚡";
          btnText.textContent = "Generate & Auto-Download";
          renderHistory();
        }, 12000);
      }
    }
  );
});

chrome.storage.onChanged.addListener(() => {
  renderHistory();
  checkStatus();
});

checkStatus();
renderHistory();
setInterval(checkStatus, 3000);
