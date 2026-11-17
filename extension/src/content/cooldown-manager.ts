export class CooldownManager {
  private isWaiting = false;

  detectUnusualActivity(): boolean {
    const text = document.body ? document.body.innerText || "" : "";
    return /unusual activity|too many requests|rate limit|temporarily blocked|slow down|quota exceeded/i.test(
      text
    );
  }

  get waiting(): boolean {
    return this.isWaiting;
  }

  async handleCooldown(seconds = 120, onProgress?: (remaining: number) => void): Promise<void> {
    if (this.isWaiting) return;
    this.isWaiting = true;

    chrome.runtime.sendMessage({
      action: "cooldown_started",
      seconds
    });

    for (let remaining = seconds; remaining > 0; remaining--) {
      if (onProgress) onProgress(remaining);
      await new Promise((r) => setTimeout(r, 1000));
    }

    this.isWaiting = false;
    chrome.runtime.sendMessage({
      action: "cooldown_ended"
    });
  }
}
