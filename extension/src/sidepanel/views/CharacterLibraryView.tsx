import React, { useState } from "react";
import { Character } from "../../shared/types";
import { Plus, Trash2, User, Sparkles } from "lucide-react";

interface Props {
  characters: Character[];
  onSaveCharacter: (char: Character) => Promise<void>;
  onDeleteCharacter: (id: string) => Promise<void>;
}

export const CharacterLibraryView: React.FC<Props> = ({
  characters,
  onSaveCharacter,
  onDeleteCharacter
}) => {
  const [isAdding, setIsAdding] = useState(false);
  const [name, setName] = useState("");
  const [trigger, setTrigger] = useState("");
  const [description, setDescription] = useState("");
  const [imageUrls, setImageUrls] = useState("");

  const handleCreate = async () => {
    if (!name.trim()) return;

    const charTrigger = trigger.trim() || `@${name.trim()}`;
    const cleanTrigger = charTrigger.startsWith("@") ? charTrigger : `@${charTrigger}`;
    const images = imageUrls
      .split(/\r?\n/)
      .map((l) => l.trim())
      .filter((l) => l.length > 0);

    await onSaveCharacter({
      id: "char_" + Date.now() + "_" + Math.random().toString(36).slice(2, 6),
      name: name.trim(),
      trigger: cleanTrigger,
      description: description.trim(),
      referenceImages: images,
      createdAt: Date.now()
    });

    setName("");
    setTrigger("");
    setDescription("");
    setImageUrls("");
    setIsAdding(false);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xs font-semibold text-slate-200">Character Library</h3>
          <p className="text-[11px] text-slate-400">
            Saved characters automatically bind into prompts via @Name syntax.
          </p>
        </div>

        <button
          onClick={() => setIsAdding(!isAdding)}
          className="flex items-center gap-1 px-2.5 py-1.5 bg-brand-600 hover:bg-brand-500 text-white rounded-lg text-xs font-medium"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>{isAdding ? "Cancel" : "Add Character"}</span>
        </button>
      </div>

      {/* Add Form */}
      {isAdding && (
        <div className="p-3 bg-slate-900 border border-slate-800 rounded-xl space-y-2.5 text-xs">
          <div>
            <label className="text-slate-400">Character Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Alex"
              className="w-full mt-1 p-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200"
            />
          </div>

          <div>
            <label className="text-slate-400">Trigger Mention</label>
            <input
              type="text"
              value={trigger}
              onChange={(e) => setTrigger(e.target.value)}
              placeholder="e.g. @Alex"
              className="w-full mt-1 p-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200"
            />
          </div>

          <div>
            <label className="text-slate-400">Description</label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="e.g. 25yo cybernetics engineer with neon blue hair"
              className="w-full mt-1 p-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200"
            />
          </div>

          <div>
            <label className="text-slate-400">Reference Image URLs (one per line)</label>
            <textarea
              value={imageUrls}
              onChange={(e) => setImageUrls(e.target.value)}
              placeholder="https://... (or Google Flow asset link)"
              className="w-full mt-1 h-16 p-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200"
            />
          </div>

          <button
            onClick={handleCreate}
            disabled={!name.trim()}
            className="w-full py-2 bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white font-medium rounded-lg"
          >
            Save Character
          </button>
        </div>
      )}

      {/* Characters List */}
      {characters.length === 0 ? (
        <div className="p-8 text-center border border-dashed border-slate-800 rounded-xl text-slate-500 text-xs">
          No characters saved yet. Create a character profile to maintain visual consistency across generations.
        </div>
      ) : (
        <div className="space-y-2">
          {characters.map((char) => (
            <div
              key={char.id}
              className="flex items-start justify-between p-3 bg-slate-900 border border-slate-800 rounded-xl text-xs"
            >
              <div className="flex items-start gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center text-indigo-300 shrink-0">
                  <User className="w-4 h-4" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-slate-200">{char.name}</span>
                    <span className="text-[10px] px-1.5 py-0.2 bg-brand-500/20 text-brand-300 rounded font-mono">
                      {char.trigger}
                    </span>
                  </div>
                  {char.description && (
                    <p className="text-slate-400 text-[11px] mt-0.5 line-clamp-2">
                      {char.description}
                    </p>
                  )}
                  {char.referenceImages.length > 0 && (
                    <span className="text-[10px] text-slate-500 mt-1 block">
                      {char.referenceImages.length} reference image(s) attached
                    </span>
                  )}
                </div>
              </div>

              <button
                onClick={() => onDeleteCharacter(char.id)}
                className="text-slate-500 hover:text-red-400 p-1"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
