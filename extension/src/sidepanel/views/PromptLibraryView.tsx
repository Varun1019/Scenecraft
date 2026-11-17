import React, { useState } from "react";
import { PromptItem } from "../../shared/types";
import { Plus, Trash2, Search, ArrowRight, Star } from "lucide-react";

interface Props {
  prompts: PromptItem[];
  onSavePrompt: (prompt: PromptItem) => Promise<void>;
  onDeletePrompt: (id: string) => Promise<void>;
  onUsePrompt: (promptText: string) => void;
}

export const PromptLibraryView: React.FC<Props> = ({
  prompts,
  onSavePrompt,
  onDeletePrompt,
  onUsePrompt
}) => {
  const [search, setSearch] = useState("");
  const [isAdding, setIsAdding] = useState(false);
  const [title, setTitle] = useState("");
  const [promptText, setPromptText] = useState("");
  const [category, setCategory] = useState("General");

  const filtered = prompts.filter(
    (p) =>
      p.title.toLowerCase().includes(search.toLowerCase()) ||
      p.prompt.toLowerCase().includes(search.toLowerCase()) ||
      p.category.toLowerCase().includes(search.toLowerCase())
  );

  const handleCreate = async () => {
    if (!title.trim() || !promptText.trim()) return;

    await onSavePrompt({
      id: "prompt_" + Date.now() + "_" + Math.random().toString(36).slice(2, 6),
      title: title.trim(),
      prompt: promptText.trim(),
      category: category.trim() || "General",
      tags: [],
      type: "text-to-image",
      favorite: false,
      createdAt: Date.now()
    });

    setTitle("");
    setPromptText("");
    setIsAdding(false);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xs font-semibold text-slate-200">Prompt Library</h3>
          <p className="text-[11px] text-slate-400">Save and organize reusable creative templates.</p>
        </div>

        <button
          onClick={() => setIsAdding(!isAdding)}
          className="flex items-center gap-1 px-2.5 py-1.5 bg-brand-600 hover:bg-brand-500 text-white rounded-lg text-xs font-medium"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>{isAdding ? "Cancel" : "New Prompt"}</span>
        </button>
      </div>

      {/* Add Form */}
      {isAdding && (
        <div className="p-3 bg-slate-900 border border-slate-800 rounded-xl space-y-2.5 text-xs">
          <div>
            <label className="text-slate-400">Title</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Atmospheric Cyberpunk Cityscape"
              className="w-full mt-1 p-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200"
            />
          </div>

          <div>
            <label className="text-slate-400">Category</label>
            <input
              type="text"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              placeholder="e.g. Sci-Fi, Landscapes, Portraits"
              className="w-full mt-1 p-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200"
            />
          </div>

          <div>
            <label className="text-slate-400">Prompt Template</label>
            <textarea
              value={promptText}
              onChange={(e) => setPromptText(e.target.value)}
              placeholder="Write the full prompt template..."
              className="w-full mt-1 h-20 p-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 resize-y"
            />
          </div>

          <button
            onClick={handleCreate}
            disabled={!title.trim() || !promptText.trim()}
            className="w-full py-2 bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white font-medium rounded-lg"
          >
            Save to Library
          </button>
        </div>
      )}

      {/* Search Bar */}
      <div className="relative">
        <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-500" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search prompts or categories..."
          className="w-full pl-8 pr-3 py-1.5 bg-slate-900 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-brand-500"
        />
      </div>

      {/* Prompts List */}
      {filtered.length === 0 ? (
        <div className="p-8 text-center border border-dashed border-slate-800 rounded-xl text-slate-500 text-xs">
          No prompts found. Save frequent prompts here for rapid reuse.
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((item) => (
            <div
              key={item.id}
              className="p-3 bg-slate-900 border border-slate-800 rounded-xl space-y-1.5 text-xs"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <span className="font-semibold text-slate-200">{item.title}</span>
                  <span className="text-[10px] px-1.5 py-0.2 bg-slate-800 text-slate-400 rounded">
                    {item.category}
                  </span>
                </div>

                <div className="flex items-center gap-1">
                  <button
                    onClick={() => onUsePrompt(item.prompt)}
                    className="flex items-center gap-1 px-2 py-1 bg-brand-600/20 text-brand-300 hover:bg-brand-600/30 rounded text-[11px]"
                  >
                    <span>Use</span>
                    <ArrowRight className="w-3 h-3" />
                  </button>
                  <button
                    onClick={() => onDeletePrompt(item.id)}
                    className="text-slate-500 hover:text-red-400 p-1"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                </div>
              </div>

              <p className="text-slate-400 text-[11px] line-clamp-2 italic">"{item.prompt}"</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
