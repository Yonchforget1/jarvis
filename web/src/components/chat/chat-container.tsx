"use client";

import { useEffect, useRef, useState, useCallback, useMemo } from "react";
import {
  MessageSquare,
  Zap,
  Code,
  Globe,
  Gamepad2,
  Sparkles,
  Keyboard,
  Search,
  X,
  ChevronUp,
  ChevronDown,
  ArrowDown,
  Square,
  FileJson,
  FileText,
  Trash2,
} from "lucide-react";
import type { ChatMessage } from "@/lib/types";
import { MessageBubble } from "./message-bubble";
import { TypingIndicator } from "./typing-indicator";
import { ChatInput } from "./chat-input";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { ShortcutsDialog } from "@/components/ui/shortcuts-dialog";
import { useConnection } from "@/hooks/use-connection";
import { useToast } from "@/components/ui/toast";

function getDateLabel(dateStr: string): string {
  const date = new Date(dateStr);
  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);

  if (date.toDateString() === today.toDateString()) return "Today";
  if (date.toDateString() === yesterday.toDateString()) return "Yesterday";
  return date.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" });
}

interface ChatContainerProps {
  messages: ChatMessage[];
  isLoading: boolean;
  onSend: (message: string) => void;
  onEditMessage?: (messageId: string, newContent: string) => void;
  onRetry?: () => void;
  onStop?: () => void;
  onClear?: () => void;
}

const SUGGESTIONS = [
  {
    icon: Code,
    text: "Write a Python script that generates a fractal image",
    color: "text-green-400",
    bg: "bg-green-400/10 border-green-400/20 hover:bg-green-400/15",
  },
  {
    icon: Globe,
    text: "Search the web for the latest AI news",
    color: "text-orange-400",
    bg: "bg-orange-400/10 border-orange-400/20 hover:bg-orange-400/15",
  },
  {
    icon: Gamepad2,
    text: "Create a platformer game called SpaceRunner",
    color: "text-purple-400",
    bg: "bg-purple-400/10 border-purple-400/20 hover:bg-purple-400/15",
  },
  {
    icon: Zap,
    text: "List all files in the current directory",
    color: "text-blue-400",
    bg: "bg-blue-400/10 border-blue-400/20 hover:bg-blue-400/15",
  },
];

export function ChatContainer({
  messages,
  isLoading,
  onSend,
  onEditMessage,
  onRetry,
  onStop,
  onClear,
}: ChatContainerProps) {
  const { status: connectionStatus, retry: retryConnection } = useConnection();
  const toast = useToast();
  const scrollRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [activeMatchIndex, setActiveMatchIndex] = useState(0);
  const [showScrollButton, setShowScrollButton] = useState(false);
  const [newMessageCount, setNewMessageCount] = useState(0);
  const [clearConfirmOpen, setClearConfirmOpen] = useState(false);
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  const prevMessageCountRef = useRef(messages.length);

  const hasStreaming = useMemo(() => messages.some((m) => m.isStreaming), [messages]);

  // Debounce search query to avoid recomputing matches on every keystroke
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const searchDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current);
    searchDebounceRef.current = setTimeout(() => setDebouncedSearch(searchQuery), 200);
    return () => { if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current); };
  }, [searchQuery]);

  // Find matching message indices (uses debounced query)
  const matchingIndices = useMemo(() => {
    if (!debouncedSearch.trim()) return [];
    const q = debouncedSearch.toLowerCase();
    return messages
      .map((msg, i) => (msg.content.toLowerCase().includes(q) ? i : -1))
      .filter((i) => i !== -1);
  }, [messages, debouncedSearch]);

  // Scroll to active match
  useEffect(() => {
    if (matchingIndices.length === 0 || !scrollRef.current) return;
    const msgId = messages[matchingIndices[activeMatchIndex]]?.id;
    if (!msgId) return;
    const el = scrollRef.current.querySelector(`[data-message-id="${msgId}"]`);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [activeMatchIndex, matchingIndices, messages]);

  const navigateMatch = useCallback(
    (direction: "next" | "prev") => {
      if (matchingIndices.length === 0) return;
      setActiveMatchIndex((prev) => {
        if (direction === "next") return (prev + 1) % matchingIndices.length;
        return (prev - 1 + matchingIndices.length) % matchingIndices.length;
      });
    },
    [matchingIndices.length]
  );

  const closeSearch = useCallback(() => {
    setSearchOpen(false);
    setSearchQuery("");
    setActiveMatchIndex(0);
  }, []);

  const exportChat = useCallback(() => {
    if (messages.length === 0) return;
    try {
      const lines: string[] = [
        "# JARVIS Chat Export",
        `> Exported on ${new Date().toLocaleString()}`,
        `> ${messages.length} messages`,
        "",
      ];
      for (const msg of messages) {
        const time = new Date(msg.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
        if (msg.role === "user") {
          lines.push(`## User (${time})`, "", msg.content, "");
        } else {
          lines.push(`## JARVIS (${time})`, "");
          if (msg.tool_calls?.length) {
            for (const tc of msg.tool_calls) {
              lines.push(
                `<details><summary>Tool: ${tc.name}</summary>`,
                "",
                "```json",
                JSON.stringify(tc.args, null, 2),
                "```",
                "",
                "Result:",
                "```",
                tc.result.slice(0, 500),
                "```",
                "</details>",
                ""
              );
            }
          }
          lines.push(msg.content, "");
        }
        lines.push("---", "");
      }
      const blob = new Blob([lines.join("\n")], { type: "text/markdown" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `jarvis-chat-${new Date().toISOString().split("T")[0]}.md`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success("Exported", "Chat saved as Markdown");
    } catch {
      toast.error("Export failed", "Could not generate Markdown export");
    }
  }, [messages, toast]);

  const exportChatJSON = useCallback(() => {
    if (messages.length === 0) return;
    try {
      const data = {
        exported_at: new Date().toISOString(),
        message_count: messages.length,
        messages: messages.map((msg) => ({
          id: msg.id,
          role: msg.role,
          content: msg.content,
          timestamp: msg.timestamp,
          ...(msg.tool_calls?.length ? { tool_calls: msg.tool_calls } : {}),
          ...(msg.isError ? { is_error: true } : {}),
        })),
      };
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `jarvis-chat-${new Date().toISOString().split("T")[0]}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success("Exported", "Chat saved as JSON");
    } catch {
      toast.error("Export failed", "Could not generate JSON export");
    }
  }, [messages, toast]);

  // Track messages length + last error in refs so keyboard handler stays stable
  const messagesLenRef = useRef(messages.length);
  const lastMsgErrorRef = useRef(false);
  useEffect(() => {
    messagesLenRef.current = messages.length;
    lastMsgErrorRef.current = messages.length > 0 && !!messages[messages.length - 1].isError;
  }, [messages]);

  const searchFocusRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => () => {
    if (searchFocusRef.current) clearTimeout(searchFocusRef.current);
  }, []);

  // Ctrl+F to open search, Ctrl+Shift+E to export, Escape to close
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "f" && messagesLenRef.current > 0) {
        e.preventDefault();
        setSearchOpen(true);
        if (searchFocusRef.current) clearTimeout(searchFocusRef.current);
        searchFocusRef.current = setTimeout(() => searchInputRef.current?.focus(), 50);
      }
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === "E" && messagesLenRef.current > 0) {
        e.preventDefault();
        exportChat();
      }
      if (e.key === "Escape" && searchOpen) {
        closeSearch();
      }
      if ((e.ctrlKey || e.metaKey) && e.key === "?") {
        e.preventDefault();
        setShortcutsOpen(true);
      }
      if ((e.ctrlKey || e.metaKey) && e.key === "l" && messagesLenRef.current > 0 && onClear) {
        e.preventDefault();
        setClearConfirmOpen(true);
      }
      // Ctrl+Shift+R to retry last failed message
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === "R" && lastMsgErrorRef.current && onRetry) {
        e.preventDefault();
        onRetry();
      }
      // Ctrl+Home to scroll to top
      if ((e.ctrlKey || e.metaKey) && e.key === "Home" && scrollRef.current) {
        e.preventDefault();
        scrollRef.current.scrollTo({ top: 0, behavior: "smooth" });
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [searchOpen, closeSearch, exportChat, onClear, onRetry]);

  // Track scroll position to show/hide scroll-to-bottom button (throttled via rAF)
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    let rafId: number | null = null;
    const handleScroll = () => {
      if (rafId !== null) return;
      rafId = requestAnimationFrame(() => {
        rafId = null;
        const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
        setShowScrollButton(distanceFromBottom > 200);
        if (distanceFromBottom < 100) {
          setNewMessageCount(0);
        }
      });
    };
    el.addEventListener("scroll", handleScroll, { passive: true });
    return () => {
      el.removeEventListener("scroll", handleScroll);
      if (rafId !== null) cancelAnimationFrame(rafId);
    };
  }, []);

  // Auto-scroll to bottom on new messages (only if already near bottom)
  useEffect(() => {
    if (!scrollRef.current || searchOpen) return;
    const el = scrollRef.current;
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    const isNearBottom = distanceFromBottom < 200;

    if (isNearBottom) {
      el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
      setNewMessageCount(0);
    } else if (messages.length > prevMessageCountRef.current) {
      // User is scrolled up and new messages arrived
      setNewMessageCount((prev) => prev + (messages.length - prevMessageCountRef.current));
    }
    prevMessageCountRef.current = messages.length;
  }, [messages, isLoading, searchOpen]);

  const scrollToBottom = useCallback(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
      setNewMessageCount(0);
    }
  }, []);

  // Determine which message is the active match
  const handleSlashCommand = useCallback((action: "clear" | "export" | "new" | "help") => {
    if (action === "clear") setClearConfirmOpen(true);
    else if (action === "export") exportChat();
    else if (action === "new") onSend("/new");
    else if (action === "help") setShortcutsOpen(true);
  }, [exportChat, onSend]);

  const activeMatchMsgId =
    matchingIndices.length > 0
      ? messages[matchingIndices[activeMatchIndex]]?.id
      : null;

  return (
    <div className="flex h-full flex-col">
      {/* Search bar */}
      <div
        className={`overflow-hidden transition-all duration-200 ease-in-out ${
          searchOpen ? "max-h-14" : "max-h-0"
        }`}
      >
        <div className="flex items-center gap-2 border-b border-border/50 bg-card/80 backdrop-blur-sm px-4 py-2">
          <Search className="h-4 w-4 text-muted-foreground shrink-0" />
          <input
            ref={searchInputRef}
            type="text"
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setActiveMatchIndex(0);
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                navigateMatch(e.shiftKey ? "prev" : "next");
              }
              if (e.key === "Escape") {
                closeSearch();
              }
            }}
            placeholder="Search messages..."
            aria-label="Search messages"
            className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground/50"
          />
          {searchQuery && (
            <span className="text-xs text-muted-foreground/60 shrink-0">
              {matchingIndices.length === 0
                ? "No matches"
                : `${activeMatchIndex + 1} of ${matchingIndices.length}`}
            </span>
          )}
          <div className="flex items-center gap-0.5">
            <button
              onClick={() => navigateMatch("prev")}
              disabled={matchingIndices.length === 0}
              aria-label="Previous match"
              className="rounded-md p-1 text-muted-foreground hover:bg-muted hover:text-foreground disabled:opacity-30 transition-colors"
            >
              <ChevronUp className="h-4 w-4" />
            </button>
            <button
              onClick={() => navigateMatch("next")}
              disabled={matchingIndices.length === 0}
              aria-label="Next match"
              className="rounded-md p-1 text-muted-foreground hover:bg-muted hover:text-foreground disabled:opacity-30 transition-colors"
            >
              <ChevronDown className="h-4 w-4" />
            </button>
          </div>
          <button
            onClick={closeSearch}
            aria-label="Close search"
            className="rounded-md p-1 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Offline banner */}
      {connectionStatus === "disconnected" && (
        <div className="flex items-center justify-center gap-2 bg-red-500/10 border-b border-red-500/20 px-4 py-2 animate-fade-in">
          <div className="h-2 w-2 rounded-full bg-red-500 animate-pulse" />
          <span className="text-xs text-red-400">Unable to reach the server</span>
          <button
            onClick={retryConnection}
            className="text-xs text-red-400 underline underline-offset-2 hover:text-red-300 transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {/* Chat actions bar */}
      {messages.length > 0 && !searchOpen && (
        <div className="flex items-center justify-end gap-1 px-4 py-1.5 border-b border-border/30">
          <button
            onClick={exportChat}
            aria-label="Export as Markdown"
            className="flex items-center gap-1.5 rounded-lg px-2 py-1 text-[10px] text-muted-foreground/50 hover:text-foreground hover:bg-muted transition-colors"
            title="Export as Markdown"
          >
            <FileText className="h-3 w-3" />
            <span className="hidden sm:inline">.md</span>
          </button>
          <button
            onClick={exportChatJSON}
            aria-label="Export as JSON"
            className="flex items-center gap-1.5 rounded-lg px-2 py-1 text-[10px] text-muted-foreground/50 hover:text-foreground hover:bg-muted transition-colors"
            title="Export as JSON"
          >
            <FileJson className="h-3 w-3" />
            <span className="hidden sm:inline">.json</span>
          </button>
          {onClear && (
            <button
              onClick={() => setClearConfirmOpen(true)}
              className="flex items-center gap-1.5 rounded-lg px-2 py-1 text-[10px] text-muted-foreground/50 hover:text-red-400 hover:bg-red-400/10 transition-colors"
              title="Clear chat"
            >
              <Trash2 className="h-3 w-3" />
              <span className="hidden sm:inline">Clear</span>
            </button>
          )}
        </div>
      )}

      {/* Message area */}
      <div ref={scrollRef} role="log" aria-label="Chat messages" aria-live="polite" className="flex-1 overflow-y-auto scroll-smooth">
        {messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center px-4 animate-fade-in-up">
            {/* Logo with animated gradient ring */}
            <div className="relative mb-8">
              <div className="absolute -inset-1 rounded-3xl bg-gradient-to-r from-primary/20 via-purple-500/20 to-cyan-500/20 blur-lg animate-glow-pulse" />
              <div className="relative flex h-20 w-20 items-center justify-center rounded-3xl bg-card border border-border/50">
                <MessageSquare className="h-10 w-10 text-primary" />
              </div>
              <div className="absolute -bottom-1 -right-1 flex h-7 w-7 items-center justify-center rounded-full bg-green-500/20 border border-green-500/30">
                <Sparkles className="h-3.5 w-3.5 text-green-400" />
              </div>
            </div>

            {/* Welcome text */}
            <h2 className="mb-2 text-2xl sm:text-3xl font-bold tracking-tight text-center">
              What can I help you build?
            </h2>
            <p className="mb-10 text-sm text-muted-foreground/70 max-w-md text-center leading-relaxed">
              I&apos;m JARVIS, your AI agent with 16+ professional tools. I can
              write code, search the web, manage files, and build games.
            </p>

            {/* Suggestion cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-lg w-full px-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s.text}
                  onClick={() => onSend(s.text)}
                  className={`flex items-start gap-3 rounded-2xl border p-4 text-left text-sm transition-all duration-200 hover:scale-[1.02] hover:shadow-lg active:scale-[0.98] ${s.bg}`}
                >
                  <s.icon className={`h-4 w-4 mt-0.5 shrink-0 ${s.color}`} />
                  <span className="text-muted-foreground leading-relaxed">
                    {s.text}
                  </span>
                </button>
              ))}
            </div>

            {/* Keyboard shortcut hint */}
            <div className="mt-8 flex items-center gap-3 text-[10px] text-muted-foreground/40">
              <Keyboard className="h-3 w-3" />
              <span>
                <kbd className="rounded bg-muted px-1 py-0.5 font-mono text-[9px]">Ctrl+K</kbd>{" "}
                commands
              </span>
              <span className="text-muted-foreground/20">|</span>
              <span>
                <kbd className="rounded bg-muted px-1 py-0.5 font-mono text-[9px]">Ctrl+N</kbd>{" "}
                new chat
              </span>
              <span className="text-muted-foreground/20">|</span>
              <span>
                <kbd className="rounded bg-muted px-1 py-0.5 font-mono text-[9px]">/</kbd>{" "}
                slash commands
              </span>
            </div>
          </div>
        ) : (
          <div className="mx-auto max-w-3xl py-4">
            {messages.map((msg, idx) => {
              const prevMsg = idx > 0 ? messages[idx - 1] : null;
              const currentDate = getDateLabel(msg.timestamp);
              const prevDate = prevMsg ? getDateLabel(prevMsg.timestamp) : null;
              const showDateSeparator = currentDate !== prevDate;
              const isGrouped = !showDateSeparator && prevMsg?.role === msg.role;

              return (
                <div key={msg.id}>
                  {showDateSeparator && (
                    <div className="flex items-center gap-3 px-4 py-3">
                      <div className="flex-1 h-px bg-border/50" />
                      <span className="text-[10px] font-medium text-muted-foreground/50 uppercase tracking-wider shrink-0">
                        {currentDate}
                      </span>
                      <div className="flex-1 h-px bg-border/50" />
                    </div>
                  )}
                  <MessageBubble
                    message={msg}
                    onRetry={msg.isError ? onRetry : undefined}
                    onStop={msg.isStreaming ? onStop : undefined}
                    onEdit={msg.role === "user" && !isLoading ? (newContent) => {
                      if (onEditMessage) {
                        onEditMessage(msg.id, newContent);
                      } else {
                        onSend(newContent);
                      }
                    } : undefined}
                    searchQuery={searchOpen ? searchQuery : ""}
                    isActiveMatch={msg.id === activeMatchMsgId}
                    isGrouped={isGrouped}
                  />
                </div>
              );
            })}
            {isLoading && !hasStreaming && (
              <TypingIndicator />
            )}
          </div>
        )}
      </div>

      {/* Scroll to bottom button */}
      {showScrollButton && messages.length > 0 && (
        <div className="relative">
          <div className="absolute bottom-2 left-1/2 -translate-x-1/2 z-10 animate-fade-in-up">
            <button
              onClick={scrollToBottom}
              aria-label={newMessageCount > 0 ? `${newMessageCount} new messages, scroll to latest` : "Scroll to latest message"}
              className="flex items-center gap-1.5 rounded-full bg-card/90 backdrop-blur-sm border border-border/50 shadow-lg px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground hover:bg-card transition-all duration-200 hover:shadow-xl"
            >
              <ArrowDown className="h-3.5 w-3.5" />
              {newMessageCount > 0 ? (
                <span className="flex items-center gap-1">
                  <span className="flex h-4 min-w-4 items-center justify-center rounded-full bg-primary px-1 text-[10px] font-medium text-primary-foreground">
                    {newMessageCount}
                  </span>
                  <span>new</span>
                </span>
              ) : (
                <span>Latest</span>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Floating stop button during streaming */}
      {isLoading && onStop && hasStreaming && (
        <div className="flex justify-center py-2 animate-fade-in">
          <button
            onClick={onStop}
            aria-label="Stop generating response"
            className="flex items-center gap-2 rounded-full bg-card border border-border/50 shadow-lg px-4 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-muted transition-all duration-200 hover:shadow-xl active:scale-95"
          >
            <Square className="h-3.5 w-3.5 fill-current" />
            Stop generating
          </button>
        </div>
      )}

      {/* Input */}
      <ChatInput
        onSend={onSend}
        disabled={isLoading}
        onSlashCommand={handleSlashCommand}
      />

      {/* Keyboard shortcuts dialog */}
      <ShortcutsDialog open={shortcutsOpen} onClose={() => setShortcutsOpen(false)} />

      {/* Clear confirmation */}
      <ConfirmDialog
        open={clearConfirmOpen}
        onClose={() => setClearConfirmOpen(false)}
        onConfirm={() => onClear?.()}
        title="Clear conversation?"
        description="This will remove all messages from this chat. This action cannot be undone."
        confirmLabel="Clear Chat"
        variant="danger"
      />
    </div>
  );
}
