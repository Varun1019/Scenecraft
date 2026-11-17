import React from "react";
import { Job, AssetItem, FlowStatus } from "../../shared/types";
import { Play, CheckCircle2, Clock, XCircle, Sparkles, Video, Layers, Image as ImageIcon } from "lucide-react";
import { NavTab } from "../components/Navbar";

interface Props {
  jobs: Job[];
  assets: AssetItem[];
  status: FlowStatus;
  onNavigate: (tab: NavTab) => void;
  onPause: () => void;
  onResume: () => void;
}

export const DashboardView: React.FC<Props> = ({
  jobs,
  assets,
  status,
  onNavigate
}) => {
  const pending = jobs.filter((j) => j.status === "pending" || j.status === "preparing");
  const generating = jobs.filter((j) => j.status === "generating" || j.status === "submitting");
  const completed = jobs.filter((j) => j.status === "completed");
  const failed = jobs.filter((j) => j.status === "failed");

  return (
    <div className="space-y-4">
      {/* Metrics Row */}
      <div className="grid grid-cols-4 gap-2">
        <div className="bg-slate-900/80 border border-slate-800 p-2.5 rounded-xl text-center">
          <div className="text-slate-400 text-[10px] uppercase font-semibold">Active</div>
          <div className="text-base font-bold text-amber-400 flex items-center justify-center gap-1 mt-0.5">
            <Play className="w-3.5 h-3.5 fill-amber-400" />
            {generating.length}
          </div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 p-2.5 rounded-xl text-center">
          <div className="text-slate-400 text-[10px] uppercase font-semibold">Queued</div>
          <div className="text-base font-bold text-indigo-400 flex items-center justify-center gap-1 mt-0.5">
            <Clock className="w-3.5 h-3.5" />
            {pending.length}
          </div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 p-2.5 rounded-xl text-center">
          <div className="text-slate-400 text-[10px] uppercase font-semibold">Completed</div>
          <div className="text-base font-bold text-emerald-400 flex items-center justify-center gap-1 mt-0.5">
            <CheckCircle2 className="w-3.5 h-3.5" />
            {completed.length}
          </div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 p-2.5 rounded-xl text-center">
          <div className="text-slate-400 text-[10px] uppercase font-semibold">Failed</div>
          <div className="text-base font-bold text-red-400 flex items-center justify-center gap-1 mt-0.5">
            <XCircle className="w-3.5 h-3.5" />
            {failed.length}
          </div>
        </div>
      </div>

      {/* Active Generating Job Card */}
      {status.activeJob && (
        <div className="p-3 bg-indigo-950/40 border border-indigo-500/40 rounded-xl space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="flex items-center gap-1.5 text-indigo-300 font-semibold">
              <Sparkles className="w-3.5 h-3.5 animate-pulse text-indigo-400" />
              Generating Now ({status.activeJob.type})
            </span>
            <span className="px-2 py-0.5 bg-indigo-500/20 text-indigo-200 text-[10px] rounded-full uppercase font-bold">
              {status.activeJob.status}
            </span>
          </div>
          <p className="text-xs text-slate-200 line-clamp-2 italic">
            "{status.activeJob.resolvedPrompt || status.activeJob.prompt}"
          </p>
        </div>
      )}

      {/* Quick Actions */}
      <div className="space-y-2">
        <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
          Quick Generation
        </div>
        <div className="grid grid-cols-3 gap-2">
          <button
            onClick={() => onNavigate("image")}
            className="flex flex-col items-center gap-1.5 p-3 rounded-xl bg-slate-900/70 border border-slate-800 hover:border-brand-500/50 hover:bg-slate-800/60 transition-all text-xs"
          >
            <ImageIcon className="w-5 h-5 text-indigo-400" />
            <span className="font-medium text-slate-200">Image</span>
          </button>

          <button
            onClick={() => onNavigate("video")}
            className="flex flex-col items-center gap-1.5 p-3 rounded-xl bg-slate-900/70 border border-slate-800 hover:border-brand-500/50 hover:bg-slate-800/60 transition-all text-xs"
          >
            <Video className="w-5 h-5 text-purple-400" />
            <span className="font-medium text-slate-200">Video</span>
          </button>

          <button
            onClick={() => onNavigate("batch")}
            className="flex flex-col items-center gap-1.5 p-3 rounded-xl bg-slate-900/70 border border-slate-800 hover:border-brand-500/50 hover:bg-slate-800/60 transition-all text-xs"
          >
            <Layers className="w-5 h-5 text-emerald-400" />
            <span className="font-medium text-slate-200">Batch</span>
          </button>
        </div>
      </div>

      {/* Recent Generations Gallery */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
            Recent Media ({assets.length})
          </span>
          {assets.length > 0 && (
            <button
              onClick={() => onNavigate("assets")}
              className="text-xs text-brand-400 hover:underline"
            >
              View all
            </button>
          )}
        </div>

        {assets.length === 0 ? (
          <div className="p-6 text-center border border-dashed border-slate-800 rounded-xl text-slate-500 text-xs">
            No media generated yet. Submit your first prompt to see outputs here.
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto pr-1">
            {assets.slice(0, 4).map((asset) => (
              <div
                key={asset.id}
                className="group relative bg-slate-900 rounded-lg overflow-hidden border border-slate-800"
              >
                {asset.mediaType === "video" ? (
                  <div className="w-full h-24 bg-slate-950 flex items-center justify-center text-slate-500">
                    <Video className="w-6 h-6 text-purple-400" />
                  </div>
                ) : (
                  <img
                    src={asset.url}
                    alt={asset.prompt}
                    className="w-full h-24 object-cover"
                    loading="lazy"
                  />
                )}
                <div className="p-1.5 text-[10px] text-slate-300 truncate" title={asset.prompt}>
                  {asset.prompt}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
