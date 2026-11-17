import React, { useState } from "react";
import { Server, CheckCircle2, XCircle, Terminal, Play, Copy, Check } from "lucide-react";

interface Props {
  bridgeConnected: boolean;
  onTestPrompt: (prompt: string) => Promise<void>;
}

export const AgentConnectorView: React.FC<Props> = ({ bridgeConnected, onTestPrompt }) => {
  const [copied, setCopied] = useState(false);
  const [isTesting, setIsTesting] = useState(false);

  const mcpConfigSnippet = JSON.stringify(
    {
      mcpServers: {
        "flow-studio-pro": {
          command: "node",
          args: ["./extension/server/mcp-server.cjs"]
        }
      }
    },
    null,
    2
  );

  const handleCopy = () => {
    navigator.clipboard.writeText(mcpConfigSnippet);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleRunTest = async () => {
    setIsTesting(true);
    try {
      await onTestPrompt("Studio photo of a futuristic crystal orb glowing softly");
    } finally {
      setIsTesting(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Bridge Status Card */}
      <div className="p-3 bg-slate-900 border border-slate-800 rounded-xl space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-slate-300">Local Bridge Daemon</span>
          <span
            className={`flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
              bridgeConnected
                ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                : "bg-red-500/20 text-red-300 border border-red-500/30"
            }`}
          >
            {bridgeConnected ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
            {bridgeConnected ? "Active (Port 8795)" : "Offline"}
          </span>
        </div>

        <p className="text-[11px] text-slate-400">
          The custom bridge runs on loopback `127.0.0.1:8795`. Completely isolated from official Flow Connector (8791).
        </p>

        <button
          onClick={handleRunTest}
          disabled={!bridgeConnected || isTesting}
          className="w-full py-2 bg-indigo-600/30 hover:bg-indigo-600/40 text-indigo-200 border border-indigo-500/40 rounded-lg text-xs font-medium flex items-center justify-center gap-2"
        >
          <Play className="w-3 h-3 fill-indigo-200" />
          <span>{isTesting ? "Executing Test..." : "Dispatch Test Prompt to Flow"}</span>
        </button>
      </div>

      {/* MCP Configuration Snippet */}
      <div className="p-3 bg-slate-900 border border-slate-800 rounded-xl space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-300">
            <Terminal className="w-3.5 h-3.5 text-brand-400" />
            <span>Agent MCP Configuration</span>
          </div>

          <button
            onClick={handleCopy}
            className="flex items-center gap-1 text-[11px] text-brand-300 hover:text-white"
          >
            {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
            <span>{copied ? "Copied" : "Copy"}</span>
          </button>
        </div>

        <pre className="p-2.5 bg-slate-950 border border-slate-800 rounded-lg text-[10px] text-slate-300 font-mono overflow-x-auto">
          {mcpConfigSnippet}
        </pre>
      </div>

      {/* Tools List */}
      <div className="space-y-1.5 text-xs">
        <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
          Exposed MCP Tools
        </span>
        <div className="space-y-1">
          {[
            { name: "flow_status", desc: "Check Google Flow & extension connection" },
            { name: "flow_generate_image", desc: "Generate image and auto-download" },
            { name: "flow_generate_video", desc: "Generate video and auto-download" },
            { name: "flow_submit_batch", desc: "Submit batch array of prompts" },
            { name: "flow_get_job", desc: "Check status and filename of job" },
            { name: "flow_get_history", desc: "Retrieve recent generations" }
          ].map((tool) => (
            <div
              key={tool.name}
              className="p-2 bg-slate-900 border border-slate-800 rounded-lg flex items-center justify-between text-[11px]"
            >
              <code className="text-brand-300 font-mono">{tool.name}</code>
              <span className="text-slate-400 text-[10px]">{tool.desc}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
