"use client";

import { usePathname } from "next/navigation";
import { Menu, Plus, Activity, Wifi } from "lucide-react";
import { Button } from "@/components/ui/button";

const PAGE_TITLES: Record<string, string> = {
  "/chat": "Chat",
  "/dashboard": "Dashboard",
  "/tools": "Tools",
  "/learnings": "Learnings",
  "/settings": "Settings",
};

interface HeaderProps {
  onMenuClick: () => void;
  onNewChat?: () => void;
}

export function Header({ onMenuClick, onNewChat }: HeaderProps) {
  const pathname = usePathname();
  const title = PAGE_TITLES[pathname] || "Jarvis";

  return (
    <header className="flex h-14 items-center justify-between border-b border-white/5 bg-background/80 backdrop-blur-xl px-4">
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="icon"
          onClick={onMenuClick}
          className="h-8 w-8 lg:hidden"
        >
          <Menu className="h-4 w-4" />
        </Button>
        <h2 className="text-sm font-semibold">{title}</h2>
      </div>
      <div className="flex items-center gap-2">
        {/* Online indicator */}
        <div className="hidden sm:flex items-center gap-1.5 rounded-full bg-green-500/10 border border-green-500/20 px-2.5 py-1">
          <Wifi className="h-3 w-3 text-green-500" />
          <span className="text-[10px] font-medium text-green-500">Connected</span>
        </div>
        <div className="flex sm:hidden items-center">
          <Activity className="h-3.5 w-3.5 text-green-500" />
        </div>
        {pathname === "/chat" && onNewChat && (
          <Button
            variant="outline"
            size="sm"
            onClick={onNewChat}
            className="h-8 gap-1.5 text-xs rounded-lg border-white/10"
          >
            <Plus className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">New Chat</span>
          </Button>
        )}
      </div>
    </header>
  );
}
