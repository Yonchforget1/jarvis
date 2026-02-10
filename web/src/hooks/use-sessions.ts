"use client";

import { useState, useCallback, useEffect } from "react";
import { api } from "@/lib/api";

interface SessionEntry {
  session_id: string;
  created_at: string;
  last_active: string;
  message_count: number;
  preview: string;
}

// Generate a short title from a message preview
function generateTitle(preview: string): string {
  if (!preview) return "New conversation";
  // Truncate to first sentence or ~40 chars
  const clean = preview.replace(/\s+/g, " ").trim();
  const sentence = clean.match(/^[^.!?\n]+[.!?]?/)?.[0] || clean;
  if (sentence.length <= 40) return sentence;
  return sentence.slice(0, 37).trimEnd() + "...";
}

// Client-side session names stored in localStorage
function getSessionNames(): Record<string, string> {
  try {
    const stored = localStorage.getItem("jarvis-session-names");
    return stored ? JSON.parse(stored) : {};
  } catch {
    return {};
  }
}

function saveSessionNames(names: Record<string, string>) {
  localStorage.setItem("jarvis-session-names", JSON.stringify(names));
}

function getPinnedSessions(): Set<string> {
  try {
    const stored = localStorage.getItem("jarvis-pinned-sessions");
    return stored ? new Set(JSON.parse(stored)) : new Set();
  } catch {
    return new Set();
  }
}

function savePinnedSessions(pinned: Set<string>) {
  localStorage.setItem("jarvis-pinned-sessions", JSON.stringify([...pinned]));
}

export function useSessions() {
  const [sessions, setSessions] = useState<SessionEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sessionNames, setSessionNames] = useState<Record<string, string>>({});
  const [pinnedIds, setPinnedIds] = useState<Set<string>>(new Set());

  // Load custom names and pinned from localStorage
  useEffect(() => {
    setSessionNames(getSessionNames());
    setPinnedIds(getPinnedSessions());
  }, []);

  // Listen for session-deleted events from chat (e.g., 404 on load)
  useEffect(() => {
    const handler = (e: Event) => {
      const { sessionId } = (e as CustomEvent<{ sessionId: string }>).detail;
      setSessions((prev) => prev.filter((s) => s.session_id !== sessionId));
    };
    window.addEventListener("session-deleted", handler);
    return () => window.removeEventListener("session-deleted", handler);
  }, []);

  const fetchSessions = useCallback(async () => {
    try {
      const data = await api.get<SessionEntry[]>("/api/sessions");
      setSessions(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load sessions");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  const deleteSession = useCallback(
    async (sessionId: string) => {
      // Optimistic: remove from UI immediately
      const previousSessions = sessions;
      setSessions((prev) => prev.filter((s) => s.session_id !== sessionId));
      setSessionNames((prev) => {
        const next = { ...prev };
        delete next[sessionId];
        saveSessionNames(next);
        return next;
      });
      try {
        await api.delete(`/api/sessions/${sessionId}`);
      } catch {
        // Rollback on error
        setSessions(previousSessions);
      }
    },
    [sessions],
  );

  const renameSession = useCallback(
    (sessionId: string, name: string) => {
      const trimmed = name.trim().slice(0, 100);
      setSessionNames((prev) => {
        const next = { ...prev };
        if (trimmed) {
          next[sessionId] = trimmed;
        } else {
          delete next[sessionId];
        }
        saveSessionNames(next);
        return next;
      });
    },
    [],
  );

  const togglePin = useCallback(
    (sessionId: string) => {
      setPinnedIds((prev) => {
        const next = new Set(prev);
        if (next.has(sessionId)) {
          next.delete(sessionId);
        } else {
          next.add(sessionId);
        }
        savePinnedSessions(next);
        return next;
      });
    },
    [],
  );

  // Merge custom names into sessions, auto-generate titles from preview
  const sessionsWithNames = sessions
    .map((s) => ({
      ...s,
      customName: sessionNames[s.session_id] || undefined,
      autoTitle: generateTitle(s.preview),
      pinned: pinnedIds.has(s.session_id),
    }))
    .sort((a, b) => {
      // Pinned sessions first, then by last_active
      if (a.pinned && !b.pinned) return -1;
      if (!a.pinned && b.pinned) return 1;
      return new Date(b.last_active).getTime() - new Date(a.last_active).getTime();
    });

  return { sessions: sessionsWithNames, loading, error, fetchSessions, deleteSession, renameSession, togglePin };
}
