import { Character } from "./types";

export interface MatchResult {
  originalPrompt: string;
  resolvedPrompt: string;
  matchedCharacters: Character[];
  referenceImages: string[];
}

export function matchCharacters(prompt: string, characters: Character[]): MatchResult {
  if (!prompt || !characters || characters.length === 0) {
    return {
      originalPrompt: prompt,
      resolvedPrompt: prompt,
      matchedCharacters: [],
      referenceImages: []
    };
  }

  const matched = new Map<string, Character>();
  let cleanPrompt = prompt;

  for (const char of characters) {
    // Check for explicit trigger (e.g. @Alex or Alex)
    const triggerPattern = char.trigger.startsWith("@") ? char.trigger : `@${char.trigger}`;
    const namePattern = new RegExp(`\\b${char.name}\\b`, "i");
    const explicitRegex = new RegExp(escapeRegExp(triggerPattern), "gi");

    if (explicitRegex.test(prompt) || namePattern.test(prompt)) {
      matched.set(char.id, char);
      // Remove @ from the final prompt to keep prompt natural for Google Flow
      cleanPrompt = cleanPrompt.replace(explicitRegex, char.name);
    }
  }

  const matchedList = Array.from(matched.values());
  const images = matchedList.flatMap((c) => c.referenceImages || []).filter(Boolean);

  return {
    originalPrompt: prompt,
    resolvedPrompt: cleanPrompt.trim(),
    matchedCharacters: matchedList,
    referenceImages: images
  };
}

function escapeRegExp(string: string) {
  return string.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
