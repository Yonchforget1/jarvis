"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  MessageSquare,
  LayoutDashboard,
  Wrench,
  Brain,
  LogOut,
  X,
  Folder,
  Terminal,
  Globe,
  Gamepad2,
  Lightbulb,
  Settings,
  Sparkles,
  Plus,
  Trash2,
  MessageCircle,
  ChevronsLeft,
  ChevronsRight,
  Pencil,
  Check,
  Clock,
  Pin,
  PinOff,
  Search,
  ArrowUpDown,
} from "lucide-react";
import { useState, useRef, useEffect, useMemo, useCallback } from "react";
import { useAuth } from "@/lib/auth";
import { useSessionContext } from "@/lib/session-context";
import { useSessions, onSessionDeleteError } from "@/hooks/use-sessions";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { Tooltip } from "@/components/ui/tooltip";
import { useToast } from "@/components/ui/toast";

const NAV_ITEMS = [
  { href: "/chat", label: "Chat", icon: MessageSquare },
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/tools", label: "Tools", icon: Wrench },
  { href: "/learnings", label: "Learnings", icon: Brain },
  { href: "/settings", label: "Settings", icon: Settings },
];

const TOOL_GROUPS = [
  { label: "Filesystem", icon: Folder, count: 7, color: "text-blue-400" },
  { label: "Execution", icon: Terminal, count: 2, color: "text-green-400" },
  { label: "Web", icon: Globe, count: 2, color: "text-orange-400" },
  { label: "Game Dev", icon: Gamepad2, count: 2, color: "text-purple-400" },
  { label: "Memory", icon: Lightbulb, count: 3, color: "text-yellow-400" },
];

interface SidebarProps {
  onClose?: () => void;
  onSessionSelect?: (sessionId: string, name?: string) => void;
  activeSessionId?: string | null;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const secs = Math.floor(diff / 1000);
  if (secs < 10) return "just now";
  if (secs < 60) return `${secs}s ago`;
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function sessionDuration(createdAt: string, lastActive: string): string {
  const diff = new Date(lastActive).getTime() - new Date(createdAt).getTime();
  if (diff < 0) return "";
  const secs = Math.floor(diff / 1000);
  if (secs < 60) return `${secs}s`;
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins}m`;
  const hours = Math.floor(mins / 60);
  const remMins = mins % 60;
  if (hours < 24) return remMins > 0 ? `${hours}h ${remMins}m` : `${hours}h`;
  const days = Math.floor(hours / 24);
  return `${days}d`;
}

function sessionDateGroup(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  const weekAgo = new Date(today);
  weekAgo.setDate(weekAgo.getDate() - 7);

  if (date >= today) return "Today";
  if (date >= yesterday) return "Yesterday";
  if (date >= weekAgo) return "This Week";
  return "Older";
}

function usernameHue(name: string): number {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return Math.abs(hash) % 360;
}

export function Sidebar({ onClose, onSessionSelect, activeSessionId, collapsed, onToggleCollapse }: SidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();
  const { unreadCount, isProcessing } = useSessionContext();
  const { sessions, loading: sessionsLoading, error: sessionsError, fetchSessions, deleteSession, renameSession, togglePin } = useSessions();
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");
  const avatarHue = usernameHue(user?.username || "User");
  const [deletingSessionId, setDeletingSessionId] = useState<string | null>(null);
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);
  const [sessionSearch, setSessionSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const searchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [sessionLimit, setSessionLimit] = useState(15);
  const [sortMode, setSortMode] = useState<"recent" | "name" | "messages">("recent");
  const toast = useToast();
  const editInputRef = useRef<HTMLInputElement>(null);

  // Register delete error callback once
  useEffect(() => {
    onSessionDeleteError((msg) => toast.error("Delete failed", msg));
  }, [toast]);

  // Debounce session search
  useEffect(() => {
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    searchTimerRef.current = setTimeout(() => setDebouncedSearch(sessionSearch), 200);
    return () => { if (searchTimerRef.current) clearTimeout(searchTimerRef.current); };
  }, [sessionSearch]);

  const filteredSessions = useMemo(() => {
    let result = sessions;
    if (debouncedSearch.trim()) {
      const q = debouncedSearch.toLowerCase();
      result = result.filter((s) =>
        s.customName?.toLowerCase().includes(q) ||
        s.autoTitle?.toLowerCase().includes(q) ||
        s.preview?.toLowerCase().includes(q)
      );
    }
    if (sortMode === "name") {
      result = [...result].sort((a, b) => {
        const aName = (a.customName || a.autoTitle || a.preview || "").toLowerCase();
        const bName = (b.customName || b.autoTitle || b.preview || "").toLowerCase();
        return aName.localeCompare(bName);
      });
    } else if (sortMode === "messages") {
      result = [...result].sort((a, b) => b.message_count - a.message_count);
    }
    // "recent" uses default order from API (most recent first)
    return result;
  }, [sessions, debouncedSearch, sortMode]);

  useEffect(() => {
    if (editingSessionId && editInputRef.current) {
      editInputRef.current.focus();
      editInputRef.current.select();
    }
  }, [editingSessionId]);

  const startRename = (sessionId: string, currentName: string) => {
    setEditingSessionId(sessionId);
    setEditValue(currentName);
  };

  const finishRename = () => {
    if (editingSessionId) {
      renameSession(editingSessionId, editValue);
      setEditingSessionId(null);
      setEditValue("");
    }
  };

  const handleNewChat = () => {
    if (onSessionSelect) {
      onSessionSelect("");
    }
    router.push("/chat");
    onClose?.();
  };

  const handleSessionClick = (sessionId: string, name?: string) => {
    if (onSessionSelect) {
      onSessionSelect(sessionId, name);
    }
    router.push("/chat");
    onClose?.();
  };

  return (
    <nav
      aria-label="Main navigation"
      role="navigation"
      className={`flex h-full flex-col border-r border-border/50 bg-sidebar transition-all duration-300 ease-in-out ${
        collapsed ? "w-[68px]" : "w-[280px]"
      }`}
    >
      {/* Header */}
      <div className={`flex items-center ${collapsed ? "justify-center" : "justify-between"} p-4`}>
        <div className={`flex items-center ${collapsed ? "" : "gap-2.5"}`}>
          <div className="relative shrink-0">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/20 border border-primary/10">
              <span className="text-sm font-bold text-primary">J</span>
            </div>
            <div className="absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full bg-green-500 border-2 border-sidebar" />
          </div>
          {!collapsed && (
            <div className="overflow-hidden">
              <h1 className="text-sm font-semibold tracking-wide">JARVIS</h1>
              <p className="text-[10px] text-muted-foreground/60">AI Agent Platform</p>
            </div>
          )}
        </div>
        {onClose && !collapsed && (
          <Button variant="ghost" size="icon" onClick={onClose} aria-label="Close sidebar" className="h-8 w-8 lg:hidden">
            <X className="h-4 w-4" />
          </Button>
        )}
      </div>

      <Separator className="bg-muted" />

      {/* New Chat Button */}
      <div className={`${collapsed ? "px-2" : "px-3"} pt-3 pb-1`}>
        {collapsed ? (
          <Tooltip content="New Chat" side="right">
            <button
              onClick={handleNewChat}
              className="flex w-full items-center justify-center rounded-xl border border-dashed border-border/50 text-sm text-muted-foreground transition-all duration-200 hover:border-primary/30 hover:bg-primary/5 hover:text-foreground p-2.5"
            >
              <Plus className="h-4 w-4 shrink-0" />
            </button>
          </Tooltip>
        ) : (
          <button
            onClick={handleNewChat}
            className="flex w-full items-center gap-2.5 rounded-xl border border-dashed border-border/50 text-sm text-muted-foreground transition-all duration-200 hover:border-primary/30 hover:bg-primary/5 hover:text-foreground px-3 py-2.5"
          >
            <Plus className="h-4 w-4 shrink-0" />
            New Chat
          </button>
        )}
      </div>

      {/* Navigation */}
      <div role="list" aria-label="Page navigation" className={`space-y-0.5 ${collapsed ? "px-2" : "px-3"} pt-2`}>
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href;
          const linkEl = (
            <Link
              key={item.href}
              href={item.href}
              onClick={onClose}
              aria-label={item.label}
              aria-current={isActive ? "page" : undefined}
              className={`flex items-center rounded-xl text-sm transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:ring-offset-1 ${
                collapsed
                  ? "justify-center p-2.5"
                  : "gap-3 px-3 py-2.5"
              } ${
                isActive
                  ? "bg-primary/10 text-primary shadow-sm shadow-primary/5"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              }`}
            >
              <div className="relative shrink-0">
                <item.icon className="h-4 w-4" />
                {item.label === "Chat" && unreadCount > 0 && collapsed && (
                  <span className="absolute -top-1.5 -right-1.5 flex h-3.5 min-w-3.5 items-center justify-center rounded-full bg-primary px-0.5 text-[8px] font-bold text-primary-foreground">
                    {unreadCount > 9 ? "9+" : unreadCount}
                  </span>
                )}
              </div>
              {!collapsed && (
                <>
                  {item.label}
                  {item.label === "Chat" && unreadCount > 0 ? (
                    <span className="ml-auto flex h-5 min-w-5 items-center justify-center rounded-full bg-primary px-1 text-[10px] font-bold text-primary-foreground">
                      {unreadCount > 99 ? "99+" : unreadCount}
                    </span>
                  ) : item.label === "Chat" ? (
                    <Sparkles className="ml-auto h-3 w-3 text-primary/50" />
                  ) : null}
                </>
              )}
            </Link>
          );
          return collapsed ? (
            <Tooltip key={item.href} content={item.label} side="right">
              {linkEl}
            </Tooltip>
          ) : (
            <div key={item.href}>{linkEl}</div>
          );
        })}
      </div>

      <Separator className={`${collapsed ? "mx-2" : "mx-3"} !my-3 bg-muted`} />

      {/* Chat History - hidden when collapsed */}
      <div className={`flex-1 overflow-y-auto ${collapsed ? "px-2" : "px-3"} space-y-1`}>
        {collapsed ? (
          /* Collapsed: show recent chat dots */
          <div className="space-y-1">
            {sessions.slice(0, 5).map((session) => (
              <Tooltip
                key={session.session_id}
                content={session.customName || session.autoTitle || session.preview || "New conversation"}
                side="right"
              >
                <button
                  onClick={() => handleSessionClick(session.session_id, session.customName || session.autoTitle || session.preview || "New conversation")}
                  className={`flex w-full items-center justify-center rounded-xl p-2.5 cursor-pointer transition-all duration-200 ${
                    activeSessionId === session.session_id
                      ? "bg-primary/10 text-primary"
                      : "text-muted-foreground/70 hover:bg-muted hover:text-foreground"
                  }`}
                >
                  <MessageCircle className="h-3.5 w-3.5" />
                </button>
              </Tooltip>
            ))}
          </div>
        ) : (
          <>
            {/* Session search + sort */}
            {sessions.length > 3 && (
              <div className="flex items-center gap-1 px-1 mb-1">
                <div role="search" className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3 w-3 text-muted-foreground/40" />
                  <input
                    value={sessionSearch}
                    onChange={(e) => { setSessionSearch(e.target.value); setSessionLimit(15); }}
                    placeholder="Search chats..."
                    aria-label="Search conversations"
                    className="w-full rounded-lg bg-muted/50 border border-border/30 pl-7 pr-2 py-1.5 text-[11px] placeholder:text-muted-foreground/30 outline-none focus:border-primary/30 transition-colors"
                  />
                </div>
                <Tooltip content={`Sort: ${sortMode === "recent" ? "Recent" : sortMode === "name" ? "Name" : "Messages"}`} side="bottom">
                  <button
                    onClick={() => setSortMode((prev) => prev === "recent" ? "name" : prev === "name" ? "messages" : "recent")}
                    aria-label={`Sort by ${sortMode}`}
                    className="shrink-0 rounded-lg p-1.5 text-muted-foreground/40 hover:text-foreground hover:bg-muted/50 transition-colors"
                  >
                    <ArrowUpDown className="h-3 w-3" />
                  </button>
                </Tooltip>
              </div>
            )}
            {sessionsLoading ? (
              <div className="space-y-1.5 px-1">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="flex items-center gap-2 rounded-xl px-2 py-2">
                    <Skeleton className="h-3.5 w-3.5 rounded shrink-0" />
                    <div className="flex-1 space-y-1">
                      <Skeleton className="h-3 w-3/4 rounded" />
                      <Skeleton className="h-2 w-1/2 rounded" />
                    </div>
                  </div>
                ))}
              </div>
            ) : sessionsError ? (
              <div className="px-3 py-3 text-center">
                <p className="text-xs text-red-400/70 mb-1.5">Failed to load sessions</p>
                <button
                  onClick={fetchSessions}
                  className="text-[10px] text-primary/60 hover:text-primary transition-colors"
                >
                  Try again
                </button>
              </div>
            ) : sessions.length === 0 ? (
              <div className="px-3 py-4 text-center">
                <MessageCircle className="h-8 w-8 text-muted-foreground/20 mx-auto mb-2" />
                <p className="text-xs text-muted-foreground/50 font-medium">No conversations yet</p>
                <p className="text-[10px] text-muted-foreground/30 mt-0.5">Start chatting to see your history here</p>
              </div>
            ) : (
              filteredSessions
                .slice(0, sessionLimit).map((session, idx, arr) => {
                const group = sessionDateGroup(session.last_active);
                const prevGroup = idx > 0 ? sessionDateGroup(arr[idx - 1].last_active) : null;
                const showGroupHeader = group !== prevGroup;
                return (
                <div key={session.session_id}>
                  {showGroupHeader && (
                    <p className="px-3 py-1.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground/50">
                      {group}
                    </p>
                  )}
                <div
                  role="button"
                  tabIndex={0}
                  aria-label={`Open conversation: ${session.customName || session.autoTitle || session.preview || "New conversation"}`}
                  className={`group flex items-center gap-2 rounded-xl px-3 py-2 cursor-pointer transition-all duration-200 ${
                    activeSessionId === session.session_id
                      ? "bg-primary/10 text-primary"
                      : "text-muted-foreground/70 hover:bg-muted hover:text-foreground"
                  }`}
                  onClick={() => handleSessionClick(session.session_id, session.customName || session.autoTitle || session.preview || "New conversation")}
                  onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); handleSessionClick(session.session_id, session.customName || session.autoTitle || session.preview || "New conversation"); } }}
                >
                  <MessageCircle className="h-3.5 w-3.5 shrink-0" />
                  <div className="flex-1 min-w-0">
                    {editingSessionId === session.session_id ? (
                      <input
                        ref={editInputRef}
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value.slice(0, 100))}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") finishRename();
                          if (e.key === "Escape") setEditingSessionId(null);
                        }}
                        onBlur={finishRename}
                        onClick={(e) => e.stopPropagation()}
                        maxLength={100}
                        className="w-full text-xs bg-transparent outline-none border-b border-primary/40 pb-0.5"
                      />
                    ) : (
                      <p
                        className="text-xs truncate flex items-center gap-1"
                        onDoubleClick={(e) => {
                          e.stopPropagation();
                          startRename(session.session_id, session.customName || session.autoTitle || session.preview || "New conversation");
                        }}
                      >
                        <span className="truncate">{session.customName || session.autoTitle || session.preview || "New conversation"}</span>
                        {activeSessionId === session.session_id && isProcessing && (
                          <span className="shrink-0 flex gap-0.5">
                            {[0, 1, 2].map((i) => (
                              <span
                                key={i}
                                className="h-1 w-1 rounded-full bg-primary animate-typing-wave"
                                style={{ animationDelay: `${i * 0.15}s` }}
                              />
                            ))}
                          </span>
                        )}
                      </p>
                    )}
                    <p className="text-[10px] text-muted-foreground/40 flex items-center gap-1">
                      <span>{timeAgo(session.last_active)}</span>
                      <span>&middot;</span>
                      <span>{session.message_count} msgs</span>
                      {sessionDuration(session.created_at, session.last_active) && (
                        <>
                          <span>&middot;</span>
                          <Clock className="h-2 w-2 inline" />
                          <span>{sessionDuration(session.created_at, session.last_active)}</span>
                        </>
                      )}
                    </p>
                  </div>
                  <div className={`flex items-center gap-0.5 transition-all ${session.pinned ? "opacity-60 group-hover:opacity-100" : "opacity-0 group-hover:opacity-100"}`}>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        togglePin(session.session_id);
                      }}
                      className={`p-1 rounded-md transition-colors ${
                        session.pinned
                          ? "text-primary/70 hover:bg-primary/10 hover:text-primary"
                          : "hover:bg-primary/10 hover:text-primary"
                      }`}
                      aria-label={session.pinned ? "Unpin conversation" : "Pin conversation"}
                      title={session.pinned ? "Unpin" : "Pin"}
                    >
                      {session.pinned ? <PinOff className="h-3 w-3" /> : <Pin className="h-3 w-3" />}
                    </button>
                    {editingSessionId === session.session_id ? (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          finishRename();
                        }}
                        aria-label="Confirm rename"
                        className="p-1 rounded-md hover:bg-green-400/10 hover:text-green-400"
                      >
                        <Check className="h-3 w-3" />
                      </button>
                    ) : (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          startRename(session.session_id, session.customName || session.autoTitle || session.preview || "New conversation");
                        }}
                        aria-label="Rename conversation"
                        className="p-1 rounded-md hover:bg-primary/10 hover:text-primary"
                      >
                        <Pencil className="h-3 w-3" />
                      </button>
                    )}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setDeletingSessionId(session.session_id);
                      }}
                      aria-label="Delete conversation"
                      className="p-1 rounded-md hover:bg-red-400/10 hover:text-red-400"
                    >
                      <Trash2 className="h-3 w-3" />
                    </button>
                  </div>
                </div>
                </div>
                );
              })
            )}
            {/* Load more sessions button */}
            {filteredSessions.length > sessionLimit && (
              <button
                onClick={() => setSessionLimit((prev) => prev + 15)}
                className="w-full py-2 text-[10px] text-primary/60 hover:text-primary transition-colors"
              >
                Show more ({filteredSessions.length - sessionLimit} remaining)
              </button>
            )}

            <Separator className="!my-3 bg-muted" />

            {/* Tool groups */}
            <p className="px-3 py-1.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground/50">
              Tool Groups
            </p>
            {TOOL_GROUPS.map((group) => (
              <div
                key={group.label}
                className="flex items-center justify-between rounded-xl px-3 py-2 text-xs text-muted-foreground/70"
              >
                <div className="flex items-center gap-2.5">
                  <group.icon className={`h-3.5 w-3.5 ${group.color}`} />
                  <span>{group.label}</span>
                </div>
                <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-mono">
                  {group.count}
                </span>
              </div>
            ))}
          </>
        )}
      </div>

      {/* Collapse toggle (desktop only) */}
      {onToggleCollapse && (
        <div className={`${collapsed ? "px-2" : "px-3"} pb-1`}>
          {collapsed ? (
            <Tooltip content="Expand sidebar" side="right">
              <button
                onClick={onToggleCollapse}
                className="flex w-full items-center justify-center rounded-xl text-xs text-muted-foreground/50 transition-all duration-200 hover:bg-muted hover:text-foreground p-2.5"
              >
                <ChevronsRight className="h-4 w-4 shrink-0" />
              </button>
            </Tooltip>
          ) : (
            <button
              onClick={onToggleCollapse}
              className="flex w-full items-center gap-2.5 rounded-xl text-xs text-muted-foreground/50 transition-all duration-200 hover:bg-muted hover:text-foreground px-3 py-2"
            >
              <ChevronsLeft className="h-4 w-4 shrink-0" />
              <span>Collapse</span>
            </button>
          )}
        </div>
      )}

      {/* User */}
      <div className="border-t border-border/50 p-3">
        <div className={`flex items-center ${collapsed ? "justify-center" : "justify-between"} rounded-xl px-2 py-1.5`}>
          <div className={`flex items-center ${collapsed ? "" : "gap-2.5"}`}>
            {collapsed ? (
              <Tooltip content={user?.username || "User"} side="right">
                <div className="flex h-8 w-8 items-center justify-center rounded-full text-xs font-semibold border shrink-0"
                style={{ background: `linear-gradient(135deg, hsl(${avatarHue}, 60%, 35%) 0%, hsl(${avatarHue}, 50%, 20%) 100%)`, borderColor: `hsl(${avatarHue}, 50%, 40%)`, color: `hsl(${avatarHue}, 80%, 80%)` }}>
                  {user?.username?.[0]?.toUpperCase() || "U"}
                </div>
              </Tooltip>
            ) : (
              <div className="flex h-8 w-8 items-center justify-center rounded-full text-xs font-semibold border shrink-0"
                style={{ background: `linear-gradient(135deg, hsl(${avatarHue}, 60%, 35%) 0%, hsl(${avatarHue}, 50%, 20%) 100%)`, borderColor: `hsl(${avatarHue}, 50%, 40%)`, color: `hsl(${avatarHue}, 80%, 80%)` }}>
                {user?.username?.[0]?.toUpperCase() || "U"}
              </div>
            )}
            {!collapsed && (
              <div className="overflow-hidden">
                <span className="text-sm font-medium">{user?.username || "User"}</span>
                <p className="text-[10px] text-muted-foreground/50">Free Plan</p>
              </div>
            )}
          </div>
          {!collapsed && (
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setShowLogoutConfirm(true)}
              aria-label="Log out"
              className="h-8 w-8 text-muted-foreground/50 hover:text-red-400 hover:bg-red-400/10 transition-all"
            >
              <LogOut className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>

      {/* Delete session confirmation */}
      <ConfirmDialog
        open={!!deletingSessionId}
        onClose={() => setDeletingSessionId(null)}
        onConfirm={() => {
          if (deletingSessionId) {
            deleteSession(deletingSessionId);
            toast.success("Deleted", "Conversation removed.");
          }
        }}
        title="Delete conversation?"
        description="This will permanently delete this chat session and all its messages."
        confirmLabel="Delete"
        variant="danger"
      />

      {/* Logout confirmation */}
      <ConfirmDialog
        open={showLogoutConfirm}
        onClose={() => setShowLogoutConfirm(false)}
        onConfirm={logout}
        title="Log out?"
        description="You will need to sign in again to access your conversations."
        confirmLabel="Log out"
        variant="danger"
      />
    </nav>
  );
}
