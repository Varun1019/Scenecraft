import React, { useState } from "react";
import { Settings } from "../../shared/types";
import { IMAGE_MODELS, VIDEO_MODELS, ASPECT_RATIOS } from "../../shared/constants";
import { Save, Download, Upload, RotateCcw } from "lucide-react";

interface Props {
  settings: Settings;
  onSaveSettings: (settings: Settings) => Promise<void>;
  onExportData: () => Promise<void>;
  onResetSettings: () => Promise<void>;
}

export const SettingsView: React.FC<Props> = ({
  settings: initialSettings,
  onSaveSettings,
  onExportData,
  onResetSettings
}) => {
  const [form, setForm] = useState<Settings>({ ...initialSettings });
  const [isSaved, setIsSaved] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onSaveSettings(form);
    setIsSaved(true);
    setTimeout(() => setIsSaved(false), 2000);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4 text-xs">
      {/* Downloads Section */}
      <div className="p-3 bg-slate-900 border border-slate-800 rounded-xl space-y-3">
        <h4 className="font-semibold text-slate-200">Storage & Downloads</h4>

        <div>
          <label className="text-slate-400 block mb-1">Download Subfolder</label>
          <input
            type="text"
            value={form.downloadFolder}
            onChange={(e) => setForm({ ...form, downloadFolder: e.target.value })}
            className="w-full p-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200"
            placeholder="GoogleFlow"
          />
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="font-medium text-slate-300">Automatic Downloading</div>
            <div className="text-[10px] text-slate-500">
              Save intercepted media immediately to disk
            </div>
          </div>
          <input
            type="checkbox"
            checked={form.autoDownload}
            onChange={(e) => setForm({ ...form, autoDownload: e.target.checked })}
            className="w-4 h-4 rounded bg-slate-950 border-slate-800 text-brand-600 focus:ring-brand-500"
          />
        </div>
      </div>

      {/* Model & Generation Defaults */}
      <div className="p-3 bg-slate-900 border border-slate-800 rounded-xl space-y-3">
        <h4 className="font-semibold text-slate-200">Default Generation Settings</h4>

        <div>
          <label className="text-slate-400 block mb-1">Default Image Model</label>
          <select
            value={form.defaultImageModel}
            onChange={(e) => setForm({ ...form, defaultImageModel: e.target.value })}
            className="w-full p-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200"
          >
            {IMAGE_MODELS.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="text-slate-400 block mb-1">Default Video Model</label>
          <select
            value={form.defaultVideoModel}
            onChange={(e) => setForm({ ...form, defaultVideoModel: e.target.value })}
            className="w-full p-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200"
          >
            {VIDEO_MODELS.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="text-slate-400 block mb-1">Default Aspect Ratio</label>
          <select
            value={form.defaultAspectRatio}
            onChange={(e) => setForm({ ...form, defaultAspectRatio: e.target.value as any })}
            className="w-full p-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200"
          >
            {ASPECT_RATIOS.map((r) => (
              <option key={r.id} value={r.id}>
                {r.label}
              </option>
            ))}
          </select>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="text-slate-400 block mb-1">Batch Delay (seconds)</label>
            <input
              type="number"
              min="1"
              max="60"
              value={form.defaultDelaySeconds}
              onChange={(e) => setForm({ ...form, defaultDelaySeconds: Number(e.target.value) })}
              className="w-full p-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200"
            />
          </div>

          <div>
            <label className="text-slate-400 block mb-1">Max Retries</label>
            <input
              type="number"
              min="0"
              max="10"
              value={form.maxRetries}
              onChange={(e) => setForm({ ...form, maxRetries: Number(e.target.value) })}
              className="w-full p-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200"
            />
          </div>
        </div>
      </div>

      {/* Save Button */}
      <button
        type="submit"
        className="w-full py-2.5 px-4 bg-brand-600 hover:bg-brand-500 text-white font-semibold rounded-xl flex items-center justify-center gap-2"
      >
        <Save className="w-4 h-4" />
        <span>{isSaved ? "Settings Saved!" : "Save Settings"}</span>
      </button>

      {/* Backup & Data */}
      <div className="pt-2 flex items-center justify-between border-t border-slate-800">
        <button
          type="button"
          onClick={onExportData}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 border border-slate-800 text-slate-300 rounded-lg hover:bg-slate-800"
        >
          <Download className="w-3.5 h-3.5" />
          <span>Export Data</span>
        </button>

        <button
          type="button"
          onClick={onResetSettings}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-red-950/30 border border-red-500/30 text-red-300 rounded-lg hover:bg-red-900/30"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>Reset Defaults</span>
        </button>
      </div>
    </form>
  );
};
