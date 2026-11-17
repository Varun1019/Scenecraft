import React, { useState } from "react";
import { AssetItem } from "../../shared/types";
import { Search, Video, Image as ImageIcon, Trash2, ExternalLink } from "lucide-react";

interface Props {
  assets: AssetItem[];
  onDeleteAsset: (id: string) => Promise<void>;
}

export const AssetLibraryView: React.FC<Props> = ({ assets, onDeleteAsset }) => {
  const [search, setSearch] = useState("");
  const [filterType, setFilterType] = useState<"all" | "image" | "video">("all");

  const filtered = assets.filter((a) => {
    const matchesSearch = a.prompt.toLowerCase().includes(search.toLowerCase());
    const matchesType = filterType === "all" || a.mediaType === filterType;
    return matchesSearch && matchesType;
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xs font-semibold text-slate-200">Asset Gallery</h3>
          <p className="text-[11px] text-slate-400">All captured media downloaded to your machine.</p>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-500" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by prompt..."
            className="w-full pl-8 pr-3 py-1.5 bg-slate-900 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-brand-500"
          />
        </div>

        <div className="flex gap-1 bg-slate-900 border border-slate-800 p-1 rounded-lg text-xs">
          {(["all", "image", "video"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setFilterType(t)}
              className={`px-2 py-0.5 rounded capitalize ${
                filterType === t
                  ? "bg-brand-600 text-white font-medium"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Media Grid */}
      {filtered.length === 0 ? (
        <div className="p-8 text-center border border-dashed border-slate-800 rounded-xl text-slate-500 text-xs">
          No matching media found.
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-2 max-h-[460px] overflow-y-auto pr-1">
          {filtered.map((asset) => (
            <div
              key={asset.id}
              className="group relative bg-slate-900 border border-slate-800 rounded-xl overflow-hidden flex flex-col"
            >
              {asset.mediaType === "video" ? (
                <div className="w-full h-28 bg-slate-950 flex flex-col items-center justify-center text-slate-500">
                  <Video className="w-8 h-8 text-purple-400 mb-1" />
                  <span className="text-[10px] text-purple-300">Video File</span>
                </div>
              ) : (
                <img
                  src={asset.url}
                  alt={asset.prompt}
                  className="w-full h-28 object-cover bg-slate-950"
                  loading="lazy"
                />
              )}

              <div className="p-2 flex-1 flex flex-col justify-between">
                <div>
                  <p className="text-[11px] text-slate-200 line-clamp-2" title={asset.prompt}>
                    {asset.prompt}
                  </p>
                  <p className="text-[10px] text-slate-500 truncate mt-1" title={asset.localPath}>
                    📁 {asset.localPath}
                  </p>
                </div>

                <div className="flex items-center justify-between mt-2 pt-1 border-t border-slate-800">
                  <span className="text-[10px] text-slate-500">
                    {new Date(asset.createdAt).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit"
                    })}
                  </span>
                  <div className="flex items-center gap-1">
                    <a
                      href={asset.url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-slate-400 hover:text-brand-300 p-1"
                      title="Open source URL"
                    >
                      <ExternalLink className="w-3 h-3" />
                    </a>
                    <button
                      onClick={() => onDeleteAsset(asset.id)}
                      className="text-slate-500 hover:text-red-400 p-1"
                      title="Remove from history"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
