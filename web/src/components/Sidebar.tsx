"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

interface Session {
  session_id: string;
  title: string;
  message_count: number;
  last_active: string;
  pinned?: boolean;
}

interface SidebarProps {
  currentSessionId: string | null;
  onSelectSession: (sessionId: string) => void;
  onNewChat: () => void;
  onLogout: () => void;
  refreshTrigger: number;
}

export function Sidebar({
  currentSessionId,
  onSelectSession,
  onNewChat,
  onLogout,
  refreshTrigger,
}: SidebarProps) {
  const router = useRouter();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<
    { session_id: string; title: string; matches: { role: string; content: string }[] }[]
  >([]);
  const [searching, setSearching] = useState(false);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameText, setRenameText] = useState("");
  const renameRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadSessions();
  }, [refreshTrigger]);

  // Close mobile sidebar on session select
  function selectSession(sid: string) {
    onSelectSession(sid);
    setMobileOpen(false);
  }

  async function loadSessions() {
    try {
      const data = await api.getSessions();
      setSessions(data);
    } catch {
      // ignore - might not be logged in yet
    }
  }

  async function handleSearch(query: string) {
    setSearchQuery(query);
    if (!query.trim()) {
      setSearchResults([]);
      return;
    }
    setSearching(true);
    try {
      const data = await api.searchSessions(query);
      setSearchResults(data.results);
    } catch {
      setSearchResults([]);
    } finally {
      setSearching(false);
    }
  }

  async function handleDelete(e: React.MouseEvent, sessionId: string) {
    e.stopPropagation();
    try {
      await api.deleteSession(sessionId);
      setSessions((prev) => prev.filter((s) => s.session_id !== sessionId));
    } catch {
      // ignore
    }
  }

  function startRename(e: React.MouseEvent, session: Session) {
    e.preventDefault();
    e.stopPropagation();
    setRenamingId(session.session_id);
    setRenameText(session.title);
    setTimeout(() => renameRef.current?.focus(), 50);
  }

  async function submitRename(sessionId: string) {
    if (renameText.trim() && renameText !== sessions.find(s => s.session_id === sessionId)?.title) {
      try {
        await api.renameSession(sessionId, renameText.trim());
        setSessions((prev) =>
          prev.map((s) =>
            s.session_id === sessionId ? { ...s, title: renameText.trim() } : s
          )
        );
      } catch { /* ignore */ }
    }
    setRenamingId(null);
  }

  async function handlePin(e: React.MouseEvent, sessionId: string, currentlyPinned: boolean) {
    e.stopPropagation();
    try {
      await api.pinSession(sessionId, !currentlyPinned);
      setSessions((prev) =>
        prev.map((s) =>
          s.session_id === sessionId ? { ...s, pinned: !currentlyPinned } : s
        )
      );
    } catch {
      // ignore
    }
  }

  // Mobile toggle button (always visible on small screens)
  const mobileToggle = (
    <button
      onClick={() => setMobileOpen(!mobileOpen)}
      className="md:hidden fixed top-3 left-3 z-50 w-10 h-10 flex items-center justify-center bg-zinc-800 border border-zinc-700 rounded-lg text-zinc-300 hover:text-white hover:bg-zinc-700 transition-colors"
      aria-label="Toggle sidebar"
    >
      {mobileOpen ? "\u2715" : "\u2630"}
    </button>
  );

  // Desktop collapsed state
  if (collapsed) {
    return (
      <>
        {mobileToggle}
        <div className="hidden md:flex w-12 bg-zinc-900 border-r border-zinc-800 flex-col items-center py-3 gap-3">
          <button
            onClick={() => setCollapsed(false)}
            className="w-8 h-8 flex items-center justify-center text-zinc-500 hover:text-zinc-300 text-lg"
            title="Expand sidebar"
          >
            &raquo;
          </button>
          <button
            onClick={onNewChat}
            className="w-8 h-8 flex items-center justify-center text-zinc-500 hover:text-zinc-300 text-lg"
            title="New chat"
          >
            +
          </button>
        </div>
      </>
    );
  }

  const sidebarContent = (
    <div className="w-64 bg-zinc-900 border-r border-zinc-800 flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-3 border-b border-zinc-800">
        <button
          onClick={() => { onNewChat(); setMobileOpen(false); }}
          className="flex-1 text-left text-sm text-zinc-300 hover:text-white px-2 py-1.5 rounded hover:bg-zinc-800 transition-colors"
        >
          + New Chat
        </button>
        <button
          onClick={() => setCollapsed(true)}
          className="hidden md:block text-zinc-500 hover:text-zinc-300 px-1"
          title="Collapse"
        >
          &laquo;
        </button>
      </div>

      {/* Search */}
      <div className="px-3 py-2 border-b border-zinc-800">
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => handleSearch(e.target.value)}
          placeholder="Search conversations..."
          className="w-full bg-zinc-800 text-zinc-300 text-xs px-2.5 py-1.5 rounded border border-zinc-700 focus:border-blue-500 focus:outline-none placeholder-zinc-600"
        />
      </div>

      {/* Search Results */}
      {searchQuery && (
        <div className="overflow-y-auto py-1 border-b border-zinc-800 max-h-48">
          {searching && (
            <p className="text-xs text-zinc-500 px-4 py-2 animate-pulse">Searching...</p>
          )}
          {!searching && searchResults.length === 0 && (
            <p className="text-xs text-zinc-600 px-4 py-2">No results</p>
          )}
          {searchResults.map((r) => (
            <div
              key={r.session_id}
              onClick={() => {
                selectSession(r.session_id);
                setSearchQuery("");
                setSearchResults([]);
              }}
              className="px-3 py-2 mx-1 rounded cursor-pointer hover:bg-zinc-800/50 transition-colors"
            >
              <p className="text-xs font-medium text-zinc-300 truncate">{r.title}</p>
              {r.matches[0] && (
                <p className="text-xs text-zinc-500 truncate mt-0.5">
                  {r.matches[0].content}
                </p>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Session list */}
      <div className="flex-1 overflow-y-auto py-2">
        {sessions.length === 0 && (
          <p className="text-xs text-zinc-600 px-4 py-2">No conversations yet</p>
        )}
        {sessions.map((s) => (
          <div
            key={s.session_id}
            onClick={() => renamingId !== s.session_id && selectSession(s.session_id)}
            onDoubleClick={(e) => startRename(e, s)}
            className={`group flex items-center gap-1.5 px-3 py-2 mx-1 rounded cursor-pointer text-sm transition-colors ${
              s.session_id === currentSessionId
                ? "bg-zinc-800 text-white"
                : "text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200"
            }`}
          >
            {s.pinned && <span className="text-xs text-yellow-500 shrink-0" title="Pinned">{"\u{1F4CC}"}</span>}
            {renamingId === s.session_id ? (
              <input
                ref={renameRef}
                value={renameText}
                onChange={(e) => setRenameText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") submitRename(s.session_id);
                  if (e.key === "Escape") setRenamingId(null);
                }}
                onBlur={() => submitRename(s.session_id)}
                className="flex-1 bg-zinc-700 text-zinc-100 text-sm px-1 py-0.5 rounded border border-zinc-600 focus:border-blue-500 focus:outline-none"
                onClick={(e) => e.stopPropagation()}
              />
            ) : (
              <span className="flex-1 truncate">{s.title}</span>
            )}
            <button
              onClick={(e) => handlePin(e, s.session_id, !!s.pinned)}
              className="opacity-0 group-hover:opacity-100 text-zinc-600 hover:text-yellow-400 text-xs transition-opacity shrink-0"
              title={s.pinned ? "Unpin" : "Pin"}
            >
              {"\u{1F4CC}"}
            </button>
            <button
              onClick={(e) => handleDelete(e, s.session_id)}
              className="opacity-0 group-hover:opacity-100 text-zinc-600 hover:text-red-400 text-xs transition-opacity shrink-0"
              title="Delete"
            >
              x
            </button>
          </div>
        ))}
      </div>

      {/* Footer */}
      <div className="border-t border-zinc-800 px-3 py-2 space-y-1.5">
        <div className="text-xs text-zinc-600">{api.getUsername()}</div>
        <div className="flex flex-wrap gap-x-3 gap-y-1">
          {[
            { path: "/tools", label: "Tools", color: "hover:text-orange-400" },
            { path: "/schedules", label: "Schedules", color: "hover:text-cyan-400" },
            { path: "/usage", label: "Usage", color: "hover:text-green-400" },
            { path: "/keys", label: "Keys", color: "hover:text-yellow-400" },
            { path: "/settings", label: "Settings", color: "hover:text-blue-400" },
            { path: "/status", label: "Status", color: "hover:text-emerald-400" },
            { path: "/admin", label: "Admin", color: "hover:text-purple-400" },
          ].map((link) => (
            <button
              key={link.path}
              onClick={() => { router.push(link.path); setMobileOpen(false); }}
              className={`text-xs text-zinc-500 ${link.color} transition-colors`}
            >
              {link.label}
            </button>
          ))}
          <button
            onClick={onLogout}
            className="text-xs text-zinc-500 hover:text-red-400 transition-colors"
          >
            Logout
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <>
      {mobileToggle}

      {/* Desktop sidebar */}
      <div className="hidden md:block">
        {sidebarContent}
      </div>

      {/* Mobile overlay sidebar */}
      {mobileOpen && (
        <>
          <div
            className="md:hidden fixed inset-0 bg-black/60 z-40"
            onClick={() => setMobileOpen(false)}
          />
          <div className="md:hidden fixed inset-y-0 left-0 z-40">
            {sidebarContent}
          </div>
        </>
      )}
    </>
  );
}
