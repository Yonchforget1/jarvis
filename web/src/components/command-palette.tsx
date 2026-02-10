"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  Search,
  MessageSquare,
  LayoutDashboard,
  Wrench,
  Brain,
  Settings,
  Plus,
  Moon,
  Sun,
  LogOut,
  Maximize,
  Keyboard,
  Download,
  Monitor,
} from "lucide-react";
import { useTheme } from "next-themes";
import { useAuth } from "@/lib/auth";
import { useSessionContext } from "@/lib/session-context";
import { useSessions } from "@/hooks/use-sessions";
import { FocusTrap } from "@/components/ui/focus-trap";

interface CommandItem {
  id: string;
  label: string;
  description?: string;
  icon: typeof Search;
  action: () => void;
  category: string;
}

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const router = useRouter();
  const { theme, setTheme } = useTheme();
  const { logout } = useAuth();
  const { selectSession } = useSessionContext();
  const { sessions } = useSessions();

  const close = useCallback(() => {
    setOpen(false);
    setQuery("");
    setSelectedIndex(0);
  }, []);

  const commands: CommandItem[] = [
    {
      id: "new-chat",
      label: "New Chat",
      description: "Start a new conversation",
      icon: Plus,
      action: () => { selectSession(""); router.push("/chat"); close(); },
      category: "Actions",
    },
    {
      id: "nav-chat",
      label: "Chat",
      description: "Go to chat page",
      icon: MessageSquare,
      action: () => { router.push("/chat"); close(); },
      category: "Navigation",
    },
    {
      id: "nav-dashboard",
      label: "Dashboard",
      description: "View system overview",
      icon: LayoutDashboard,
      action: () => { router.push("/dashboard"); close(); },
      category: "Navigation",
    },
    {
      id: "nav-tools",
      label: "Tools",
      description: "Browse available tools",
      icon: Wrench,
      action: () => { router.push("/tools"); close(); },
      category: "Navigation",
    },
    {
      id: "nav-learnings",
      label: "Learnings",
      description: "View agent learnings",
      icon: Brain,
      action: () => { router.push("/learnings"); close(); },
      category: "Navigation",
    },
    {
      id: "nav-settings",
      label: "Settings",
      description: "Configure Jarvis",
      icon: Settings,
      action: () => { router.push("/settings"); close(); },
      category: "Navigation",
    },
    {
      id: "toggle-theme",
      label: theme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode",
      description: "Toggle appearance",
      icon: theme === "dark" ? Sun : Moon,
      action: () => { setTheme(theme === "dark" ? "light" : "dark"); close(); },
      category: "Actions",
    },
    {
      id: "focus-mode",
      label: "Toggle Focus Mode",
      description: "Hide sidebar and nav for distraction-free chat",
      icon: Maximize,
      action: () => {
        document.dispatchEvent(new KeyboardEvent("keydown", { key: "F", ctrlKey: true, shiftKey: true }));
        close();
      },
      category: "Actions",
    },
    {
      id: "shortcuts",
      label: "Keyboard Shortcuts",
      description: "View all keyboard shortcuts",
      icon: Keyboard,
      action: () => {
        document.dispatchEvent(new KeyboardEvent("keydown", { key: "?", ctrlKey: true }));
        close();
      },
      category: "Actions",
    },
    {
      id: "system-theme",
      label: "Use System Theme",
      description: "Match your OS appearance",
      icon: Monitor,
      action: () => { setTheme("system"); close(); },
      category: "Actions",
    },
    {
      id: "logout",
      label: "Log Out",
      description: "Sign out of Jarvis",
      icon: LogOut,
      action: () => { logout(); close(); },
      category: "Actions",
    },
  ];

  // Add recent sessions as switchable commands (only when searching)
  const sessionCommands: CommandItem[] = query
    ? sessions.slice(0, 8).map((s) => ({
        id: `session-${s.session_id}`,
        label: s.customName || s.autoTitle || s.preview || "New conversation",
        description: `${s.message_count} messages`,
        icon: MessageSquare,
        action: () => { selectSession(s.session_id, s.customName || s.autoTitle || s.preview); router.push("/chat"); close(); },
        category: "Sessions",
      }))
    : [];

  const allCommands = [...commands, ...sessionCommands];

  const filtered = query
    ? allCommands.filter(
        (cmd) =>
          cmd.label.toLowerCase().includes(query.toLowerCase()) ||
          cmd.description?.toLowerCase().includes(query.toLowerCase())
      )
    : commands; // Don't show sessions when there's no query

  // Group by category
  const categories = [...new Set(filtered.map((c) => c.category))];

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        setOpen((prev) => !prev);
        return;
      }
      if (e.key === "Escape" && open) {
        close();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, close]);

  // Focus input when opened
  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  // Navigate list with arrow keys
  const handleInputKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((i) => Math.min(i + 1, filtered.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (filtered[selectedIndex]) {
        filtered[selectedIndex].action();
      }
    }
  };

  // Scroll selected item into view
  useEffect(() => {
    if (listRef.current) {
      const selected = listRef.current.querySelector("[data-selected=true]");
      selected?.scrollIntoView({ block: "nearest" });
    }
  }, [selectedIndex]);

  if (!open) return null;

  let flatIndex = 0;

  return (
    <div className="fixed inset-0 z-[100]">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm animate-fade-in-up"
        onClick={close}
        style={{ animationDuration: "0.15s" }}
      />

      {/* Dialog */}
      <FocusTrap>
      <div className="relative flex justify-center pt-[20vh]">
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Command palette"
          className="w-full max-w-lg mx-4 rounded-2xl border border-border/50 bg-background shadow-2xl overflow-hidden animate-scale-in"
          style={{ animationDuration: "0.15s" }}
        >
          {/* Search input */}
          <div className="flex items-center gap-3 border-b border-border/50 px-4">
            <Search className="h-4 w-4 text-muted-foreground shrink-0" />
            <input
              ref={inputRef}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleInputKeyDown}
              placeholder="Type a command or search..."
              aria-label="Command search"
              className="flex-1 bg-transparent py-4 text-sm outline-none placeholder:text-muted-foreground/50"
            />
            <kbd className="hidden sm:inline-flex rounded bg-muted px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground">
              Esc
            </kbd>
          </div>

          {/* Results */}
          <div ref={listRef} className="max-h-72 overflow-y-auto p-2">
            {filtered.length === 0 ? (
              <div className="py-8 text-center text-sm text-muted-foreground">
                No results found
              </div>
            ) : (
              categories.map((category) => {
                const items = filtered.filter((c) => c.category === category);
                return (
                  <div key={category}>
                    <p className="px-3 pt-2 pb-1 text-[10px] font-medium uppercase tracking-wider text-muted-foreground/50">
                      {category}
                    </p>
                    {items.map((cmd) => {
                      const thisIndex = flatIndex++;
                      const isSelected = thisIndex === selectedIndex;
                      return (
                        <button
                          key={cmd.id}
                          data-selected={isSelected}
                          onClick={cmd.action}
                          onMouseEnter={() => setSelectedIndex(thisIndex)}
                          className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left transition-colors ${
                            isSelected
                              ? "bg-primary/10 text-foreground"
                              : "text-muted-foreground hover:bg-muted/50"
                          }`}
                        >
                          <cmd.icon className={`h-4 w-4 shrink-0 ${isSelected ? "text-primary" : ""}`} />
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium">{cmd.label}</p>
                            {cmd.description && (
                              <p className="text-xs text-muted-foreground/60 truncate">
                                {cmd.description}
                              </p>
                            )}
                          </div>
                        </button>
                      );
                    })}
                  </div>
                );
              })
            )}
          </div>

          {/* Footer */}
          <div className="flex items-center gap-4 border-t border-border/50 px-4 py-2.5">
            <div className="flex items-center gap-1 text-[10px] text-muted-foreground/40">
              <kbd className="rounded bg-muted px-1 py-0.5 font-mono text-[9px]">&uarr;&darr;</kbd>
              navigate
            </div>
            <div className="flex items-center gap-1 text-[10px] text-muted-foreground/40">
              <kbd className="rounded bg-muted px-1 py-0.5 font-mono text-[9px]">&crarr;</kbd>
              select
            </div>
            <div className="flex items-center gap-1 text-[10px] text-muted-foreground/40">
              <kbd className="rounded bg-muted px-1 py-0.5 font-mono text-[9px]">Esc</kbd>
              close
            </div>
          </div>
        </div>
      </div>
      </FocusTrap>
    </div>
  );
}
