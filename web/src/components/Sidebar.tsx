"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

interface Session {
  session_id: string;
  title: string;
  message_count: number;
  last_active: string;
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
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<
    { session_id: string; title: string; matches: { role: string; content: string }[] }[]
  >([]);
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    loadSessions();
  }, [refreshTrigger]);

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

  if (collapsed) {
    return (
      <div className="w-12 bg-zinc-900 border-r border-zinc-800 flex flex-col items-center py-3 gap-3">
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
    );
  }

  return (
    <div className="w-64 bg-zinc-900 border-r border-zinc-800 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-3 border-b border-zinc-800">
        <button
          onClick={onNewChat}
          className="flex-1 text-left text-sm text-zinc-300 hover:text-white px-2 py-1.5 rounded hover:bg-zinc-800 transition-colors"
        >
          + New Chat
        </button>
        <button
          onClick={() => setCollapsed(true)}
          className="text-zinc-500 hover:text-zinc-300 px-1"
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
                onSelectSession(r.session_id);
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
            onClick={() => onSelectSession(s.session_id)}
            className={`group flex items-center gap-2 px-3 py-2 mx-1 rounded cursor-pointer text-sm transition-colors ${
              s.session_id === currentSessionId
                ? "bg-zinc-800 text-white"
                : "text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200"
            }`}
          >
            <span className="flex-1 truncate">{s.title}</span>
            <button
              onClick={(e) => handleDelete(e, s.session_id)}
              className="opacity-0 group-hover:opacity-100 text-zinc-600 hover:text-red-400 text-xs transition-opacity"
              title="Delete"
            >
              x
            </button>
          </div>
        ))}
      </div>

      {/* Footer */}
      <div className="border-t border-zinc-800 px-3 py-2 space-y-1">
        <div className="text-xs text-zinc-600 mb-1">{api.getUsername()}</div>
        <div className="flex gap-3">
          <button
            onClick={() => router.push("/settings")}
            className="text-xs text-zinc-500 hover:text-blue-400 transition-colors"
          >
            Settings
          </button>
          <button
            onClick={() => router.push("/keys")}
            className="text-xs text-zinc-500 hover:text-yellow-400 transition-colors"
          >
            API Keys
          </button>
          <button
            onClick={() => router.push("/usage")}
            className="text-xs text-zinc-500 hover:text-green-400 transition-colors"
          >
            Usage
          </button>
          <button
            onClick={() => router.push("/schedules")}
            className="text-xs text-zinc-500 hover:text-cyan-400 transition-colors"
          >
            Schedules
          </button>
          <button
            onClick={() => router.push("/admin")}
            className="text-xs text-zinc-500 hover:text-purple-400 transition-colors"
          >
            Admin
          </button>
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
}
