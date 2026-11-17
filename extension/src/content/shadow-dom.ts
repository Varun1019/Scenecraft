export function queryDeep(selectors: string[], root: Document | Element | ShadowRoot = document): HTMLElement | null {
  for (const sel of selectors) {
    const elements = Array.from(root.querySelectorAll(sel)) as HTMLElement[];
    for (const el of elements) {
      if (el && (el.offsetParent !== null || el.getClientRects().length > 0)) return el;
    }
  }

  const walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT);
  while (walker.nextNode()) {
    const node = walker.currentNode as HTMLElement;
    if (node.shadowRoot) {
      const found = queryDeep(selectors, node.shadowRoot);
      if (found) return found;
    }
  }
  return null;
}

export function queryAllDeep(selectors: string[], root: Document | Element | ShadowRoot = document): HTMLElement[] {
  const results: HTMLElement[] = [];
  for (const sel of selectors) {
    const elements = Array.from(root.querySelectorAll(sel)) as HTMLElement[];
    results.push(...elements);
  }

  const walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT);
  while (walker.nextNode()) {
    const node = walker.currentNode as HTMLElement;
    if (node.shadowRoot) {
      results.push(...queryAllDeep(selectors, node.shadowRoot));
    }
  }

  return Array.from(new Set(results));
}
