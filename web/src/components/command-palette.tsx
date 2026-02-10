"use client";

import { useState, useEffect, useRef, useCallback, useMemo } from "react";
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
  Monitor,
  Trash2,
  FileText,
  AlertTriangle,
  BarChart3,
  Shield,
} from "lucide-react";
import { useTheme } from "next-themes";
import { useAuth } from "@/lib/auth";
import { useSessionContext } from "@/lib/session-context";
import { useSessions } from "@/hooks/use-sessions";
import { FocusTrap } from "@/components/ui/focus-trap";
import { api } from "@/lib/api";

interface CommandItem {
  id: string;
  label: string;
  description?: string;
  icon: typeof Search;
  action: () => void;
  category: string;
  destructive?: boolean;
}

// Recent actions tracking (frecency)
function getRecentActions(): Record<string, { count: number; lastUsed: number }> {
  try {
    return JSON.parse(localStorage.getItem("jarvis-cmd-recents") || "{}");
  } catch { return {}; }
}

function recordAction(id: string) {
  const recents = getRecentActions();
  recents[id] = { count: (recents[id]?.count || 0) + 1, lastUsed: Date.now() };
  // Keep only top 20
  const entries = Object.entries(recents).sort(([,a], [,b]) => b.lastUsed - a.lastUsed).slice(0, 20);
  localStorage.setItem("jarvis-cmd-recents", JSON.stringify(Object.fromEntries(entries)));
}

interface SearchResult {
  session_id: string;
  preview: string;
  match_count: number;
  matches: { snippet: string; role: string }[];
}

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const searchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const router = useRouter();
  const { theme, setTheme } = useTheme();
  const { logout } = useAuth();
  const { selectSession } = useSessionContext();
  const { sessions } = useSessions();

  // Global cross-session search (debounced)
  useEffect(() => {
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    if (!query || query.length < 3) {
      setSearchResults([]);
      return;
    }
    searchTimerRef.current = setTimeout(() => {
      api.get<{ sessions: SearchResult[] }>(`/api/conversation/search?q=${encodeURIComponent(query)}`)
        .then((res) => setSearchResults(res.sessions?.slice(0, 5) || []))
        .catch(() => setSearchResults([]));
    }, 400);
    return () => { if (searchTimerRef.current) clearTimeout(searchTimerRef.current); };
  }, [query]);

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
      id: "nav-analytics",
      label: "Analytics",
      description: "Usage patterns and cost analysis",
      icon: BarChart3,
      action: () => { router.push("/analytics"); close(); },
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
      id: "nav-admin",
      label: "Admin Dashboard",
      description: "System management (admin only)",
      icon: Shield,
      action: () => { router.push("/admin"); close(); },
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
      id: "search-messages",
      label: "Search Messages",
      description: "Find text in current conversation",
      icon: Search,
      action: () => {
        document.dispatchEvent(new KeyboardEvent("keydown", { key: "f", ctrlKey: true }));
        close();
      },
      category: "Actions",
    },
    {
      id: "export-md",
      label: "Export as Markdown",
      description: "Download conversation as .md file",
      icon: FileText,
      action: () => {
        document.dispatchEvent(new KeyboardEvent("keydown", { key: "E", ctrlKey: true, shiftKey: true }));
        close();
      },
      category: "Actions",
    },
    {
      id: "clear-chat",
      label: "Clear Chat",
      description: "Remove all messages from current conversation",
      icon: Trash2,
      destructive: true,
      action: () => {
        document.dispatchEvent(new KeyboardEvent("keydown", { key: "l", ctrlKey: true }));
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
      destructive: true,
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

  // Wrap actions to track usage
  const wrappedCommands = commands.map((cmd) => ({
    ...cmd,
    action: () => { recordAction(cmd.id); cmd.action(); },
  }));

  // Cross-session search results
  const globalSearchCommands: CommandItem[] = searchResults.map((r) => ({
    id: `search-${r.session_id}`,
    label: r.matches[0]?.snippet?.slice(0, 60) || r.preview || "Match",
    description: `${r.match_count} match${r.match_count > 1 ? "es" : ""} in conversation`,
    icon: Search,
    action: () => { selectSession(r.session_id); router.push("/chat"); close(); },
    category: "Search Results",
  }));

  const allCommands = [...wrappedCommands, ...sessionCommands, ...globalSearchCommands];

  const filtered = useMemo(() => {
    if (query) {
      const q = query.toLowerCase();
      return allCommands.filter(
        (cmd) =>
          cmd.label.toLowerCase().includes(q) ||
          cmd.description?.toLowerCase().includes(q)
      );
    }
    // No query: show recent actions first, then all commands
    const recents = getRecentActions();
    const recentIds = Object.entries(recents)
      .sort(([,a], [,b]) => b.lastUsed - a.lastUsed)
      .slice(0, 5)
      .map(([id]) => id);
    const recentItems = recentIds
      .map((id) => wrappedCommands.find((c) => c.id === id))
      .filter(Boolean)
      .map((cmd) => ({ ...cmd!, category: "Recent" }));
    // Remaining commands without duplicating recents
    const recentIdSet = new Set(recentIds);
    const rest = wrappedCommands.filter((c) => !recentIdSet.has(c.id));
    return [...recentItems, ...rest];
  }, [query, allCommands, wrappedCommands]);

  // Pre-compute flat indexed items grouped by category (StrictMode-safe)
  const categories = [...new Set(filtered.map((c) => c.category))];
  const indexedGroups = useMemo(() => {
    let idx = 0;
    return categories.map((category) => ({
      category,
      items: filtered
        .filter((c) => c.category === category)
        .map((cmd) => ({ cmd, flatIndex: idx++ })),
    }));
  }, [filtered, categories]);

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
  const focusTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    if (open) {
      focusTimerRef.current = setTimeout(() => inputRef.current?.focus(), 50);
    }
    return () => {
      if (focusTimerRef.current) clearTimeout(focusTimerRef.current);
    };
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
          <div ref={listRef} role="listbox" aria-label="Command results" className="max-h-72 overflow-y-auto p-2">
            {filtered.length === 0 ? (
              <div className="py-8 text-center text-sm text-muted-foreground">
                No results found
              </div>
            ) : (
              indexedGroups.map(({ category, items }) => (
                  <div key={category}>
                    <p className="px-3 pt-2 pb-1 text-[10px] font-medium uppercase tracking-wider text-muted-foreground/50">
                      {category}
                    </p>
                    {items.map(({ cmd, flatIndex: fi }) => {
                      const isSelected = fi === selectedIndex;
                      return (
                        <button
                          key={cmd.id}
                          role="option"
                          aria-selected={isSelected}
                          aria-label={`${cmd.label}${cmd.description ? `: ${cmd.description}` : ""}`}
                          data-selected={isSelected}
                          onClick={cmd.action}
                          onMouseEnter={() => setSelectedIndex(fi)}
                          className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left transition-colors ${
                            isSelected
                              ? cmd.destructive ? "bg-red-500/10 text-red-400" : "bg-primary/10 text-foreground"
                              : cmd.destructive ? "text-red-400/70 hover:bg-red-500/5" : "text-muted-foreground hover:bg-muted/50"
                          }`}
                        >
                          <cmd.icon className={`h-4 w-4 shrink-0 ${isSelected ? (cmd.destructive ? "text-red-400" : "text-primary") : ""}`} />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-1.5">
                              <p className="text-sm font-medium">{cmd.label}</p>
                              {cmd.destructive && <AlertTriangle className="h-3 w-3 text-red-400/60 shrink-0" />}
                            </div>
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
                ))
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
