import React, { useState } from "react";
import { LogEntry } from "../../shared/types";
import { Trash2, Copy, Check } from "lucide-react";

interface Props {
  logs: LogEntry[];
  onClearLogs: () => void;
}

export const LogsView: React.FC<Props> = ({ logs, onClearLogs }) => {
  const [filter, setFilter] = useState<"all" | "info" | "warn" | "error">("all");
  const [copied, setCopied] = useState(false);

  const filtered = logs.filter((l) => filter === "all" || l.level === filter);

  const handleCopyLogs = () => {
    const text = filtered
      .map(
        (l) =>
          `[${new Date(l.timestamp).toISOString()}] [${l.level.toUpperCase()}] ${l.message} ${
            l.context ? JSON.stringify(l.context) : ""
          }`
      )
      .join("\n");

    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-3 text-xs">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-slate-200">Diagnostics Log</h3>
          <p className="text-[11px] text-slate-400">Real-time automation logs and network traces.</p>
        </div>

        <div className="flex items-center gap-1.5">
          <button
            onClick={handleCopyLogs}
            className="flex items-center gap-1 px-2.5 py-1 bg-slate-900 border border-slate-800 text-slate-300 rounded hover:bg-slate-800 text-[11px]"
          >
            {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
            <span>{copied ? "Copied" : "Copy"}</span>
          </button>

          <button
            onClick={onClearLogs}
            className="flex items-center gap-1 px-2.5 py-1 bg-slate-900 border border-slate-800 text-slate-400 hover:text-red-400 rounded text-[11px]"
          >
            <Trash2 className="w-3 h-3" />
            <span>Clear</span>
          </button>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-1 bg-slate-900 p-1 border border-slate-800 rounded-lg text-xs">
        {(["all", "info", "warn", "error"] as const).map((lvl) => (
          <button
            key={lvl}
            onClick={() => setFilter(lvl)}
            className={`flex-1 py-1 rounded capitalize text-center ${
              filter === lvl
                ? "bg-brand-600 text-white font-medium"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            {lvl}
          </button>
        ))}
      </div>

      {/* Logs Window */}
      <div className="p-2.5 bg-slate-950 border border-slate-800 rounded-xl max-h-[460px] overflow-y-auto font-mono text-[11px] space-y-1.5">
        {filtered.length === 0 ? (
          <div className="text-center text-slate-600 py-6">No log entries recorded.</div>
        ) : (
          filtered.map((log) => (
            <div key={log.id} className="leading-tight">
              <span className="text-slate-600 mr-1.5">
                {new Date(log.timestamp).toLocaleTimeString()}
              </span>
              <span
                className={`uppercase font-bold mr-1.5 ${
                  log.level === "error"
                    ? "text-red-400"
                    : log.level === "warn"
                    ? "text-amber-400"
                    : "text-indigo-400"
                }`}
              >
                [{log.level}]
              </span>
              <span className="text-slate-300">{log.message}</span>
              {log.context && (
                <pre className="text-[10px] text-slate-500 overflow-x-auto mt-0.5 ml-4">
                  {JSON.stringify(log.context)}
                </pre>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};
