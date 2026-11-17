import { AspectRatio, GenerationType } from "./types";

export interface ParsedBatchItem {
  prompt: string;
  type?: GenerationType;
  aspectRatio?: AspectRatio;
  model?: string;
  duration?: number;
}

export function parseBatchText(content: string, filename = "import.txt"): ParsedBatchItem[] {
  const ext = filename.split(".").pop()?.toLowerCase();

  if (ext === "json") {
    try {
      const data = JSON.parse(content);
      if (Array.isArray(data)) {
        const items: ParsedBatchItem[] = [];
        for (const item of data) {
          if (typeof item === "string" && item.trim()) {
            items.push({ prompt: item.trim() });
          } else if (item && typeof item === "object" && typeof item.prompt === "string" && item.prompt.trim()) {
            items.push({
              prompt: item.prompt.trim(),
              type: item.type,
              aspectRatio: item.aspectRatio,
              model: item.model,
              duration: item.duration
            });
          }
        }
        return items;
      }
    } catch (_) {}
  }

  if (ext === "csv") {
    const lines = content.split(/\r?\n/).filter((l) => l.trim().length > 0);
    if (lines.length === 0) return [];

    const firstLine = lines[0].toLowerCase();
    const hasHeader = firstLine.includes("prompt");
    const startIndex = hasHeader ? 1 : 0;

    const items: ParsedBatchItem[] = [];
    for (let i = startIndex; i < lines.length; i++) {
      const row = parseCsvLine(lines[i]);
      if (row.length > 0 && row[0].trim()) {
        items.push({
          prompt: row[0].trim(),
          aspectRatio: (row[1]?.trim() as AspectRatio) || undefined,
          type: (row[2]?.trim() as GenerationType) || undefined,
          model: row[3]?.trim() || undefined
        });
      }
    }
    return items;
  }

  // Plain TXT / Fallback: One prompt per line
  return content
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0 && !line.startsWith("#"))
    .map((prompt) => ({ prompt }));
}

function parseCsvLine(line: string): string[] {
  const result: string[] = [];
  let current = "";
  let inQuotes = false;

  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    if (char === '"') {
      if (inQuotes && line[i + 1] === '"') {
        current += '"';
        i++;
      } else {
        inQuotes = !inQuotes;
      }
    } else if (char === "," && !inQuotes) {
      result.push(current);
      current = "";
    } else {
      current += char;
    }
  }
  result.push(current);
  return result;
}
