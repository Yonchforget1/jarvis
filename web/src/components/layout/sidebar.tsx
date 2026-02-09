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
} from "lucide-react";
import { useState, useRef, useEffect } from "react";
import { useAuth } from "@/lib/auth";
import { useSessions } from "@/hooks/use-sessions";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";

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
  onSessionSelect?: (sessionId: string) => void;
  activeSessionId?: string | null;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export function Sidebar({ onClose, onSessionSelect, activeSessionId, collapsed, onToggleCollapse }: SidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();
  const { sessions, deleteSession, renameSession } = useSessions();
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");
  const editInputRef = useRef<HTMLInputElement>(null);

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

  const handleSessionClick = (sessionId: string) => {
    if (onSessionSelect) {
      onSessionSelect(sessionId);
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
          <Button variant="ghost" size="icon" onClick={onClose} className="h-8 w-8 lg:hidden">
            <X className="h-4 w-4" />
          </Button>
        )}
      </div>

      <Separator className="bg-muted" />

      {/* New Chat Button */}
      <div className={`${collapsed ? "px-2" : "px-3"} pt-3 pb-1`}>
        <button
          onClick={handleNewChat}
          className={`flex items-center rounded-xl border border-dashed border-border/50 text-sm text-muted-foreground transition-all duration-200 hover:border-primary/30 hover:bg-primary/5 hover:text-foreground ${
            collapsed
              ? "w-full justify-center p-2.5"
              : "w-full gap-2.5 px-3 py-2.5"
          }`}
          title={collapsed ? "New Chat" : undefined}
        >
          <Plus className="h-4 w-4 shrink-0" />
          {!collapsed && "New Chat"}
        </button>
      </div>

      {/* Navigation */}
      <div role="list" aria-label="Page navigation" className={`space-y-0.5 ${collapsed ? "px-2" : "px-3"} pt-2`}>
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onClose}
              title={collapsed ? item.label : undefined}
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
              <item.icon className="h-4 w-4 shrink-0" />
              {!collapsed && (
                <>
                  {item.label}
                  {item.label === "Chat" && (
                    <Sparkles className="ml-auto h-3 w-3 text-primary/50" />
                  )}
                </>
              )}
            </Link>
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
              <button
                key={session.session_id}
                onClick={() => handleSessionClick(session.session_id)}
                title={session.customName || session.autoTitle || session.preview || "New conversation"}
                className={`flex w-full items-center justify-center rounded-xl p-2.5 cursor-pointer transition-all duration-200 ${
                  activeSessionId === session.session_id
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground/70 hover:bg-muted hover:text-foreground"
                }`}
              >
                <MessageCircle className="h-3.5 w-3.5" />
              </button>
            ))}
          </div>
        ) : (
          <>
            <p className="px-3 py-1.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground/50">
              Recent Chats
            </p>
            {sessions.length === 0 ? (
              <p className="px-3 py-2 text-xs text-muted-foreground/40">
                No conversations yet
              </p>
            ) : (
              sessions.slice(0, 10).map((session) => (
                <div
                  key={session.session_id}
                  className={`group flex items-center gap-2 rounded-xl px-3 py-2 cursor-pointer transition-all duration-200 ${
                    activeSessionId === session.session_id
                      ? "bg-primary/10 text-primary"
                      : "text-muted-foreground/70 hover:bg-muted hover:text-foreground"
                  }`}
                  onClick={() => handleSessionClick(session.session_id)}
                >
                  <MessageCircle className="h-3.5 w-3.5 shrink-0" />
                  <div className="flex-1 min-w-0">
                    {editingSessionId === session.session_id ? (
                      <input
                        ref={editInputRef}
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") finishRename();
                          if (e.key === "Escape") setEditingSessionId(null);
                        }}
                        onBlur={finishRename}
                        onClick={(e) => e.stopPropagation()}
                        className="w-full text-xs bg-transparent outline-none border-b border-primary/40 pb-0.5"
                      />
                    ) : (
                      <p className="text-xs truncate">
                        {session.customName || session.autoTitle || session.preview || "New conversation"}
                      </p>
                    )}
                    <p className="text-[10px] text-muted-foreground/40">
                      {timeAgo(session.last_active)} &middot; {session.message_count} msgs
                    </p>
                  </div>
                  <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-all">
                    {editingSessionId === session.session_id ? (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          finishRename();
                        }}
                        className="p-1 rounded-md hover:bg-green-400/10 hover:text-green-400"
                      >
                        <Check className="h-3 w-3" />
                      </button>
                    ) : (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          startRename(session.session_id, session.customName || session.preview || "");
                        }}
                        className="p-1 rounded-md hover:bg-primary/10 hover:text-primary"
                      >
                        <Pencil className="h-3 w-3" />
                      </button>
                    )}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteSession(session.session_id);
                      }}
                      className="p-1 rounded-md hover:bg-red-400/10 hover:text-red-400"
                    >
                      <Trash2 className="h-3 w-3" />
                    </button>
                  </div>
                </div>
              ))
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
          <button
            onClick={onToggleCollapse}
            className={`flex items-center rounded-xl text-xs text-muted-foreground/50 transition-all duration-200 hover:bg-muted hover:text-foreground ${
              collapsed
                ? "w-full justify-center p-2.5"
                : "w-full gap-2.5 px-3 py-2"
            }`}
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? (
              <ChevronsRight className="h-4 w-4 shrink-0" />
            ) : (
              <>
                <ChevronsLeft className="h-4 w-4 shrink-0" />
                <span>Collapse</span>
              </>
            )}
          </button>
        </div>
      )}

      {/* User */}
      <div className="border-t border-border/50 p-3">
        <div className={`flex items-center ${collapsed ? "justify-center" : "justify-between"} rounded-xl px-2 py-1.5`}>
          <div className={`flex items-center ${collapsed ? "" : "gap-2.5"}`}>
            <div
              className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-primary/30 to-primary/10 text-xs font-semibold text-primary border border-primary/20 shrink-0"
              title={collapsed ? (user?.username || "User") : undefined}
            >
              {user?.username?.[0]?.toUpperCase() || "U"}
            </div>
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
              onClick={logout}
              className="h-8 w-8 text-muted-foreground/50 hover:text-red-400 hover:bg-red-400/10 transition-all"
            >
              <LogOut className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>
    </nav>
  );
}
