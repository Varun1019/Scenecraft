import React, { useState } from "react";
import { AspectRatio, Character } from "../../shared/types";
import { IMAGE_MODELS, ASPECT_RATIOS } from "../../shared/constants";
import { Sparkles } from "lucide-react";

interface Props {
  characters: Character[];
  onSubmitJob: (jobData: any) => Promise<void>;
}

export const ImageGeneratorView: React.FC<Props> = ({ characters, onSubmitJob }) => {
  const [prompt, setPrompt] = useState("");
  const [aspectRatio, setAspectRatio] = useState<AspectRatio>("16:9");
  const [model, setModel] = useState(IMAGE_MODELS[0].id);
  const [outputs] = useState(1);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const styleChips = [
    { label: "🎬 Cinematic", text: "cinematic lighting, photorealistic 8k, shot on 35mm" },
    { label: "🎨 Anime", text: "detailed anime illustration, Makoto Shinkai style, vibrant" },
    { label: "📸 Portrait", text: "studio portrait, soft lighting, 85mm f/1.4 lens, sharp focus" },
    { label: "🌆 Cyberpunk", text: "cyberpunk neon lights, rainy street, volumetric fog, dark atmosphere" }
  ];

  const handleAddStyle = (styleText: string) => {
    setPrompt((prev) => (prev ? `${prev.trim()}, ${styleText}` : styleText));
  };

  const handleInsertCharacter = (char: Character) => {
    const trigger = char.trigger.startsWith("@") ? char.trigger : `@${char.trigger}`;
    setPrompt((prev) => (prev ? `${prev} ${trigger}` : trigger));
  };

  const handleGenerate = async () => {
    if (!prompt.trim() || isSubmitting) return;

    setIsSubmitting(true);
    try {
      await onSubmitJob({
        id: "job_" + Date.now() + "_" + Math.random().toString(36).slice(2, 6),
        prompt: prompt.trim(),
        type: "text-to-image",
        aspectRatio,
        model,
        outputs,
        source: "ui"
      });
      setPrompt("");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs">
          <label className="font-semibold text-slate-300">Prompt</label>
          <span className="text-[10px] text-slate-500">{prompt.length} chars</span>
        </div>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Describe the image you want to generate. Use @Name to include saved characters..."
          className="w-full h-24 p-2.5 bg-slate-900 border border-slate-800 rounded-xl text-xs text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-all resize-y"
        />
      </div>

      {/* Characters Hint Chips */}
      {characters.length > 0 && (
        <div className="space-y-1">
          <span className="text-[10px] text-slate-500 uppercase font-semibold">Available Characters:</span>
          <div className="flex gap-1.5 flex-wrap">
            {characters.map((char) => (
              <button
                key={char.id}
                type="button"
                onClick={() => handleInsertCharacter(char)}
                className="px-2 py-0.5 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 text-[10px] hover:bg-indigo-500/20"
              >
                @{char.name}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Quick Style Chips */}
      <div className="flex gap-1.5 overflow-x-auto pb-1 scrollbar-none">
        {styleChips.map((chip) => (
          <button
            key={chip.label}
            type="button"
            onClick={() => handleAddStyle(chip.text)}
            className="px-2.5 py-1 rounded-full bg-slate-900 border border-slate-800 text-[11px] text-slate-300 hover:border-slate-700 hover:bg-slate-800 whitespace-nowrap"
          >
            {chip.label}
          </button>
        ))}
      </div>

      {/* Model Selection */}
      <div className="space-y-1.5">
        <label className="text-xs font-semibold text-slate-300">Image Model</label>
        <select
          value={model}
          onChange={(e) => setModel(e.target.value)}
          className="w-full p-2 bg-slate-900 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-brand-500"
        >
          {IMAGE_MODELS.map((m) => (
            <option key={m.id} value={m.id}>
              {m.name}
            </option>
          ))}
        </select>
      </div>

      {/* Aspect Ratio Selector */}
      <div className="space-y-1.5">
        <label className="text-xs font-semibold text-slate-300">Aspect Ratio</label>
        <div className="grid grid-cols-4 gap-1.5">
          {ASPECT_RATIOS.map((ratio) => (
            <button
              key={ratio.id}
              type="button"
              onClick={() => setAspectRatio(ratio.id as AspectRatio)}
              className={`py-1.5 text-xs rounded-lg border text-center transition-all ${
                aspectRatio === ratio.id
                  ? "bg-brand-600 border-brand-500 text-white font-semibold"
                  : "bg-slate-900 border-slate-800 text-slate-400 hover:border-slate-700"
              }`}
            >
              {ratio.id}
            </button>
          ))}
        </div>
      </div>

      {/* Generate Action Button */}
      <button
        onClick={handleGenerate}
        disabled={!prompt.trim() || isSubmitting}
        className="w-full py-2.5 px-4 bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white font-semibold rounded-xl text-xs flex items-center justify-center gap-2 shadow-lg glow-brand transition-all"
      >
        <Sparkles className="w-4 h-4" />
        <span>{isSubmitting ? "Submitting to Queue..." : "Generate Image"}</span>
      </button>
    </div>
  );
};
