"use client";

import { usePathname } from "next/navigation";
import { useTheme } from "next-themes";
import { Menu, Plus, Wifi, WifiOff, Loader2, Sun, Moon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useConnection } from "@/hooks/use-connection";

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
  const { status, latency } = useConnection();
  const { theme, setTheme } = useTheme();

  return (
    <header className="flex h-14 items-center justify-between border-b border-border/50 bg-background/80 backdrop-blur-xl px-4">
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
        {/* Connection status */}
        {status === "connected" ? (
          <div className="hidden sm:flex items-center gap-1.5 rounded-full bg-green-500/10 border border-green-500/20 px-2.5 py-1 transition-all">
            <Wifi className="h-3 w-3 text-green-500" />
            <span className="text-[10px] font-medium text-green-500">
              Connected{latency !== null && ` (${latency}ms)`}
            </span>
          </div>
        ) : status === "disconnected" ? (
          <div className="hidden sm:flex items-center gap-1.5 rounded-full bg-red-500/10 border border-red-500/20 px-2.5 py-1 animate-pulse">
            <WifiOff className="h-3 w-3 text-red-400" />
            <span className="text-[10px] font-medium text-red-400">Disconnected</span>
          </div>
        ) : (
          <div className="hidden sm:flex items-center gap-1.5 rounded-full bg-yellow-500/10 border border-yellow-500/20 px-2.5 py-1">
            <Loader2 className="h-3 w-3 text-yellow-500 animate-spin" />
            <span className="text-[10px] font-medium text-yellow-500">Connecting</span>
          </div>
        )}

        {/* Mobile connection dot */}
        <div className="flex sm:hidden items-center">
          <div
            className={`h-2 w-2 rounded-full ${
              status === "connected"
                ? "bg-green-500"
                : status === "disconnected"
                ? "bg-red-500 animate-pulse"
                : "bg-yellow-500 animate-pulse"
            }`}
          />
        </div>

        {/* Theme toggle */}
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          className="h-8 w-8 text-muted-foreground hover:text-foreground"
        >
          <Sun className="h-4 w-4 rotate-0 scale-100 transition-transform dark:-rotate-90 dark:scale-0" />
          <Moon className="absolute h-4 w-4 rotate-90 scale-0 transition-transform dark:rotate-0 dark:scale-100" />
          <span className="sr-only">Toggle theme</span>
        </Button>

        {pathname === "/chat" && onNewChat && (
          <Button
            variant="outline"
            size="sm"
            onClick={onNewChat}
            className="h-8 gap-1.5 text-xs rounded-lg border-border/50"
          >
            <Plus className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">New Chat</span>
          </Button>
        )}
      </div>
    </header>
  );
}
