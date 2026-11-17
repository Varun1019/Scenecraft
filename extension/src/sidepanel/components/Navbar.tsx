import React from "react";
import {
  LayoutDashboard,
  Clapperboard,
  Image,
  Video,
  Layers,
  Users,
  BookOpen,
  FolderArchive,
  Bot,
  Settings,
  Terminal
} from "lucide-react";

export type NavTab =
  | "dashboard"
  | "director"
  | "image"
  | "video"
  | "batch"
  | "characters"
  | "prompts"
  | "assets"
  | "agent"
  | "settings"
  | "logs";

interface Props {
  currentTab: NavTab;
  onTabChange: (tab: NavTab) => void;
  pendingCount?: number;
}

export const Navbar: React.FC<Props> = ({ currentTab, onTabChange, pendingCount = 0 }) => {
  const tabs = [
    { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
    { id: "director", label: "AI Director", icon: Clapperboard },
    { id: "image", label: "Image", icon: Image },
    { id: "video", label: "Video", icon: Video },
    { id: "batch", label: "Batch", icon: Layers, badge: pendingCount > 0 ? pendingCount : undefined },
    { id: "characters", label: "Characters", icon: Users },
    { id: "prompts", label: "Library", icon: BookOpen },
    { id: "assets", label: "Gallery", icon: FolderArchive },
    { id: "agent", label: "Agent", icon: Bot },
    { id: "settings", label: "Settings", icon: Settings },
    { id: "logs", label: "Logs", icon: Terminal }
  ];

  return (
    <div className="flex items-center gap-1 overflow-x-auto p-1.5 rounded-xl glass-panel scrollbar-none mb-3">
      {tabs.map((tab) => {
        const Icon = tab.icon;
        const isActive = currentTab === tab.id;
        return (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id as NavTab)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all duration-200 ${
              isActive
                ? "glass-btn-primary text-white shadow-lg"
                : "text-slate-400 hover:text-slate-100 hover:bg-slate-800/40"
            }`}
          >
            <Icon className="w-3.5 h-3.5" />
            <span>{tab.label}</span>
            {tab.badge !== undefined && (
              <span className="px-1.5 py-0.2 bg-indigo-400 text-slate-950 font-bold rounded-full text-[10px]">
                {tab.badge}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
};
