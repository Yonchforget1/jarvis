"use client";

import { useEffect, useState } from "react";
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
  const [sessions, setSessions] = useState<Session[]>([]);
  const [collapsed, setCollapsed] = useState(false);

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
      <div className="border-t border-zinc-800 px-3 py-2">
        <div className="text-xs text-zinc-600 mb-1">{api.getUsername()}</div>
        <button
          onClick={onLogout}
          className="text-xs text-zinc-500 hover:text-red-400 transition-colors"
        >
          Logout
        </button>
      </div>
    </div>
  );
}
