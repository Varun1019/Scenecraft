import React, { useState } from "react";
import { Job, AspectRatio } from "../../shared/types";
import { parseBatchText } from "../../shared/batch-parser";
import { Play, Pause, Trash2, RotateCcw, Upload, FileText, CheckCircle2 } from "lucide-react";

interface Props {
  jobs: Job[];
  onAddBatchJobs: (items: any[], delaySeconds: number) => Promise<void>;
  onPause: () => void;
  onResume: () => void;
  onClear: () => void;
  onRetryFailed: () => void;
  onCancelJob: (id: string) => void;
}

export const BatchGeneratorView: React.FC<Props> = ({
  jobs,
  onAddBatchJobs,
  onPause,
  onResume,
  onClear,
  onRetryFailed,
  onCancelJob
}) => {
  const [manualText, setManualText] = useState("");
  const [delay, setDelay] = useState(5);
  const [aspectRatio, setAspectRatio] = useState<AspectRatio>("16:9");
  const [isImporting, setIsImporting] = useState(false);

  const pending = jobs.filter((j) => j.status === "pending" || j.status === "preparing");
  const failed = jobs.filter((j) => j.status === "failed");

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = async (event) => {
      const text = event.target?.result as string;
      if (text) {
        setIsImporting(true);
        try {
          const parsed = parseBatchText(text, file.name);
          const mapped = parsed.map((item) => ({
            ...item,
            aspectRatio: item.aspectRatio || aspectRatio
          }));
          await onAddBatchJobs(mapped, delay);
        } finally {
          setIsImporting(false);
          e.target.value = "";
        }
      }
    };
    reader.readAsText(file);
  };

  const handleManualAdd = async () => {
    if (!manualText.trim()) return;
    const lines = manualText
      .split(/\r?\n/)
      .map((l) => l.trim())
      .filter((l) => l.length > 0);

    const items = lines.map((p) => ({ prompt: p, aspectRatio }));
    await onAddBatchJobs(items, delay);
    setManualText("");
  };

  return (
    <div className="space-y-4">
      {/* Import Box */}
      <div className="p-3 bg-slate-900 border border-slate-800 rounded-xl space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-slate-300">Import Prompt Batch</span>
          <label className="flex items-center gap-1.5 px-2.5 py-1 bg-brand-600/20 text-brand-300 border border-brand-500/30 rounded-lg text-xs cursor-pointer hover:bg-brand-600/30">
            <Upload className="w-3.5 h-3.5" />
            <span>Upload File (.txt, .csv, .json)</span>
            <input
              type="file"
              accept=".txt,.csv,.json"
              onChange={handleFileUpload}
              className="hidden"
            />
          </label>
        </div>

        <textarea
          value={manualText}
          onChange={(e) => setManualText(e.target.value)}
          placeholder="Or paste multiple prompts here (one per line)..."
          className="w-full h-20 p-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-brand-500 resize-y"
        />

        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <span>Delay (s):</span>
            <input
              type="number"
              min="1"
              max="60"
              value={delay}
              onChange={(e) => setDelay(Number(e.target.value))}
              className="w-14 p-1 bg-slate-950 border border-slate-800 rounded text-center text-slate-200"
            />
          </div>

          <button
            onClick={handleManualAdd}
            disabled={!manualText.trim() || isImporting}
            className="px-3 py-1.5 bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white rounded-lg text-xs font-medium"
          >
            Add to Queue
          </button>
        </div>
      </div>

      {/* Queue Controls */}
      <div className="flex items-center justify-between p-2 bg-slate-900/60 border border-slate-800 rounded-xl">
        <div className="flex items-center gap-1.5">
          <button
            onClick={onResume}
            className="p-1.5 bg-emerald-600/20 text-emerald-300 border border-emerald-500/30 hover:bg-emerald-600/30 rounded-lg"
            title="Resume Queue"
          >
            <Play className="w-4 h-4 fill-emerald-300" />
          </button>
          <button
            onClick={onPause}
            className="p-1.5 bg-amber-600/20 text-amber-300 border border-amber-500/30 hover:bg-amber-600/30 rounded-lg"
            title="Pause Queue"
          >
            <Pause className="w-4 h-4 fill-amber-300" />
          </button>
          {failed.length > 0 && (
            <button
              onClick={onRetryFailed}
              className="flex items-center gap-1 px-2 py-1 bg-red-600/20 text-red-300 border border-red-500/30 rounded-lg text-xs"
              title="Retry Failed Jobs"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Retry ({failed.length})</span>
            </button>
          )}
        </div>

        <button
          onClick={onClear}
          className="flex items-center gap-1 px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs"
        >
          <Trash2 className="w-3.5 h-3.5" />
          <span>Clear All</span>
        </button>
      </div>

      {/* Queue List */}
      <div className="space-y-1.5">
        <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex justify-between">
          <span>Active Queue ({jobs.length})</span>
          <span>{pending.length} Pending</span>
        </div>

        {jobs.length === 0 ? (
          <div className="p-8 text-center border border-dashed border-slate-800 rounded-xl text-slate-500 text-xs">
            Queue is empty. Add or import prompts above.
          </div>
        ) : (
          <div className="max-h-60 overflow-y-auto space-y-1.5 pr-1">
            {jobs.map((job, idx) => (
              <div
                key={job.id}
                className="flex items-center justify-between p-2 bg-slate-900 border border-slate-800 rounded-lg text-xs"
              >
                <div className="flex items-center gap-2 truncate pr-2">
                  <span className="text-[10px] text-slate-500 font-mono">#{idx + 1}</span>
                  <span className="truncate text-slate-200" title={job.prompt}>
                    {job.prompt}
                  </span>
                </div>

                <div className="flex items-center gap-1.5 shrink-0">
                  <span
                    className={`px-1.5 py-0.5 rounded text-[10px] uppercase font-bold ${
                      job.status === "completed"
                        ? "bg-emerald-500/20 text-emerald-300"
                        : job.status === "failed"
                        ? "bg-red-500/20 text-red-300"
                        : job.status === "generating"
                        ? "bg-brand-500/20 text-brand-300 animate-pulse"
                        : "bg-slate-800 text-slate-400"
                    }`}
                  >
                    {job.status}
                  </span>

                  {job.status !== "completed" && (
                    <button
                      onClick={() => onCancelJob(job.id)}
                      className="text-slate-500 hover:text-red-400"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
