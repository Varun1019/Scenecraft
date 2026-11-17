import React from "react";
import { FlowStatus } from "../../shared/types";
import { Globe, Server, AlertTriangle } from "lucide-react";

interface Props {
  status: FlowStatus;
  bridgeConnected: boolean;
}

export const StatusBadge: React.FC<Props> = ({ status, bridgeConnected }) => {
  return (
    <div className="space-y-2 mb-3">
      {status.isCooldown && (
        <div className="flex items-center gap-2 p-2 bg-amber-500/15 border border-amber-500/30 rounded-lg text-amber-200 text-xs">
          <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
          <span>
            <strong>Unusual Activity Paused:</strong> Resuming in {status.cooldownSeconds || 120}s...
          </span>
        </div>
      )}

      <div className="grid grid-cols-2 gap-2 text-xs">
        <div
          className={`flex items-center gap-2 px-2.5 py-1.5 rounded-xl border glass-panel transition-all ${
            status.connected
              ? "border-emerald-500/40 text-emerald-300 shadow-[0_0_12px_rgba(16,185,129,0.15)]"
              : "border-red-500/30 text-red-300"
          }`}
        >
          <span className={`w-2 h-2 rounded-full ${status.connected ? "bg-emerald-400 animate-pulse" : "bg-red-400"}`} />
          <Globe className="w-3.5 h-3.5 shrink-0" />
          <span className="truncate font-medium">
            {status.connected ? (status.inProject ? "Flow: Ready" : "Flow: Open") : "Flow: Offline"}
          </span>
        </div>

        <div
          className={`flex items-center gap-2 px-2.5 py-1.5 rounded-xl border glass-panel transition-all ${
            bridgeConnected
              ? "border-indigo-500/40 text-indigo-300 shadow-[0_0_12px_rgba(99,102,241,0.2)]"
              : "border-slate-800 text-slate-400"
          }`}
        >
          <span className={`w-2 h-2 rounded-full ${bridgeConnected ? "bg-indigo-400 animate-pulse" : "bg-slate-500"}`} />
          <Server className="w-3.5 h-3.5 shrink-0" />
          <span className="truncate font-medium">{bridgeConnected ? "Bridge: Online" : "Bridge: Offline"}</span>
        </div>
      </div>
    </div>
  );
};
