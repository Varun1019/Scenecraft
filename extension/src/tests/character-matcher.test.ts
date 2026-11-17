import { describe, it, expect } from "vitest";
import { matchCharacters } from "../shared/character-matcher";
import { Character } from "../shared/types";

describe("Character Matcher", () => {
  const characters: Character[] = [
    {
      id: "char_1",
      name: "Alex",
      trigger: "@Alex",
      description: "Protagonist engineer",
      referenceImages: ["https://example.com/alex1.jpg", "https://example.com/alex2.jpg"],
      createdAt: 1000
    },
    {
      id: "char_2",
      name: "Luna",
      trigger: "Luna",
      description: "Mystic traveler",
      referenceImages: ["https://example.com/luna.jpg"],
      createdAt: 2000
    }
  ];

  it("should match explicit @Alex trigger and resolve prompt", () => {
    const prompt = "Photo of @Alex standing in a futuristic command center";
    const result = matchCharacters(prompt, characters);

    expect(result.matchedCharacters).toHaveLength(1);
    expect(result.matchedCharacters[0].name).toBe("Alex");
    expect(result.referenceImages).toEqual([
      "https://example.com/alex1.jpg",
      "https://example.com/alex2.jpg"
    ]);
    expect(result.resolvedPrompt).toBe("Photo of Alex standing in a futuristic command center");
  });

  it("should match by name without @", () => {
    const prompt = "Portrait of Luna under moonlight";
    const result = matchCharacters(prompt, characters);

    expect(result.matchedCharacters).toHaveLength(1);
    expect(result.matchedCharacters[0].name).toBe("Luna");
    expect(result.referenceImages).toEqual(["https://example.com/luna.jpg"]);
  });

  it("should handle multiple character references", () => {
    const prompt = "Action shot of @Alex and Luna fighting side by side";
    const result = matchCharacters(prompt, characters);

    expect(result.matchedCharacters).toHaveLength(2);
    expect(result.referenceImages).toHaveLength(3);
  });

  it("should return untouched prompt when no match", () => {
    const prompt = "A serene mountain lake at sunrise";
    const result = matchCharacters(prompt, characters);

    expect(result.matchedCharacters).toHaveLength(0);
    expect(result.referenceImages).toHaveLength(0);
    expect(result.resolvedPrompt).toBe(prompt);
  });
});
