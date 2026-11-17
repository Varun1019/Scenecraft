import React, { useState } from "react";
import { AspectRatio } from "../../shared/types";
import { VIDEO_MODELS } from "../../shared/constants";
import { Video } from "lucide-react";

interface Props {
  onSubmitJob: (jobData: any) => Promise<void>;
}

export const VideoGeneratorView: React.FC<Props> = ({ onSubmitJob }) => {
  const [prompt, setPrompt] = useState("");
  const [aspectRatio, setAspectRatio] = useState<AspectRatio>("16:9");
  const [model, setModel] = useState(VIDEO_MODELS[0].id);
  const [duration, setDuration] = useState(4);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleGenerate = async () => {
    if (!prompt.trim() || isSubmitting) return;

    setIsSubmitting(true);
    try {
      await onSubmitJob({
        id: "job_" + Date.now() + "_" + Math.random().toString(36).slice(2, 6),
        prompt: prompt.trim(),
        type: "text-to-video",
        aspectRatio,
        model,
        duration,
        outputs: 1,
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
          <label className="font-semibold text-slate-300">Video Prompt</label>
          <span className="text-[10px] text-slate-500">{prompt.length} chars</span>
        </div>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Describe motion, camera movement, and visual action (e.g., Drone shot tracking a speeding car along a coastal cliff)..."
          className="w-full h-24 p-2.5 bg-slate-900 border border-slate-800 rounded-xl text-xs text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-brand-500 transition-all resize-y"
        />
      </div>

      {/* Model Selection */}
      <div className="space-y-1.5">
        <label className="text-xs font-semibold text-slate-300">Video Model</label>
        <select
          value={model}
          onChange={(e) => setModel(e.target.value)}
          className="w-full p-2 bg-slate-900 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-brand-500"
        >
          {VIDEO_MODELS.map((m) => (
            <option key={m.id} value={m.id}>
              {m.name}
            </option>
          ))}
        </select>
      </div>

      {/* Duration Control */}
      <div className="space-y-1.5">
        <label className="text-xs font-semibold text-slate-300">Duration</label>
        <div className="grid grid-cols-2 gap-2">
          {[4, 8].map((sec) => (
            <button
              key={sec}
              type="button"
              onClick={() => setDuration(sec)}
              className={`py-1.5 text-xs rounded-lg border text-center transition-all ${
                duration === sec
                  ? "bg-purple-600 border-purple-500 text-white font-semibold"
                  : "bg-slate-900 border-slate-800 text-slate-400 hover:border-slate-700"
              }`}
            >
              {sec} Seconds
            </button>
          ))}
        </div>
      </div>

      {/* Aspect Ratio Control */}
      <div className="space-y-1.5">
        <label className="text-xs font-semibold text-slate-300">Aspect Ratio</label>
        <div className="grid grid-cols-2 gap-2">
          {(["16:9", "9:16"] as AspectRatio[]).map((ratio) => (
            <button
              key={ratio}
              type="button"
              onClick={() => setAspectRatio(ratio)}
              className={`py-1.5 text-xs rounded-lg border text-center transition-all ${
                aspectRatio === ratio
                  ? "bg-purple-600 border-purple-500 text-white font-semibold"
                  : "bg-slate-900 border-slate-800 text-slate-400 hover:border-slate-700"
              }`}
            >
              {ratio}
            </button>
          ))}
        </div>
      </div>

      {/* Generate Video Action Button */}
      <button
        onClick={handleGenerate}
        disabled={!prompt.trim() || isSubmitting}
        className="w-full py-2.5 px-4 bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white font-semibold rounded-xl text-xs flex items-center justify-center gap-2 shadow-lg transition-all"
      >
        <Video className="w-4 h-4" />
        <span>{isSubmitting ? "Queueing Video..." : "Generate Video"}</span>
      </button>
    </div>
  );
};
