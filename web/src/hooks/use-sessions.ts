"use client";

import { useState, useCallback, useEffect, useMemo, useRef } from "react";
import { api } from "@/lib/api";

interface SessionEntry {
  session_id: string;
  created_at: string;
  last_active: string;
  message_count: number;
  preview: string;
  custom_name?: string | null;
  auto_title?: string | null;
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

type ErrorCallback = (message: string) => void;

let _onDeleteError: ErrorCallback | null = null;

/** Register a callback for delete errors (call from component with toast access). */
export function onSessionDeleteError(cb: ErrorCallback) {
  _onDeleteError = cb;
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
      const data = await api.get<{ sessions: SessionEntry[]; total: number }>("/api/sessions?limit=200");
      // Handle both paginated response and legacy array format
      const list = Array.isArray(data) ? data : data.sessions;
      setSessions(list);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load sessions");
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial fetch + visibility-aware polling every 30s
  useEffect(() => {
    fetchSessions();
    let interval = setInterval(fetchSessions, 30000);

    const handleVisibility = () => {
      if (document.hidden) {
        clearInterval(interval);
      } else {
        fetchSessions();
        interval = setInterval(fetchSessions, 30000);
      }
    };

    // Refresh when a new session is created in chat
    const handleSessionCreated = () => fetchSessions();

    document.addEventListener("visibilitychange", handleVisibility);
    window.addEventListener("session-created", handleSessionCreated);

    return () => {
      clearInterval(interval);
      document.removeEventListener("visibilitychange", handleVisibility);
      window.removeEventListener("session-created", handleSessionCreated);
    };
  }, [fetchSessions]);

  const deleteSession = useCallback(
    async (sessionId: string) => {
      // Capture current state for rollback via functional update
      let previousSessions: SessionEntry[] = [];
      setSessions((prev) => {
        previousSessions = prev;
        return prev.filter((s) => s.session_id !== sessionId);
      });
      setSessionNames((prev) => {
        const next = { ...prev };
        delete next[sessionId];
        saveSessionNames(next);
        return next;
      });
      setPinnedIds((prev) => {
        if (!prev.has(sessionId)) return prev;
        const next = new Set(prev);
        next.delete(sessionId);
        savePinnedSessions(next);
        return next;
      });
      try {
        await api.delete(`/api/sessions/${sessionId}`);
      } catch {
        // Rollback on error
        setSessions(previousSessions);
        _onDeleteError?.("Failed to delete conversation. Please try again.");
      }
    },
    [],
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
      // Sync to server (fire-and-forget)
      api.patch(`/api/sessions/${sessionId}`, { name: trimmed }).catch(() => {});
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

  const archiveSession = useCallback(
    async (sessionId: string) => {
      try {
        await api.patch(`/api/conversation/sessions/${sessionId}/archive`, {});
        // Remove from visible list (archived sessions are hidden by default)
        setSessions((prev) => prev.filter((s) => s.session_id !== sessionId));
      } catch {
        _onDeleteError?.("Failed to archive session.");
      }
    },
    [],
  );

  // Clean up stale session names/pins that reference deleted sessions
  useEffect(() => {
    if (sessions.length === 0 || loading) return;
    const ids = new Set(sessions.map((s) => s.session_id));
    // Clean names
    const names = getSessionNames();
    let namesDirty = false;
    for (const key of Object.keys(names)) {
      if (!ids.has(key)) { delete names[key]; namesDirty = true; }
    }
    if (namesDirty) {
      saveSessionNames(names);
      setSessionNames(names);
    }
    // Clean pins
    let pinsDirty = false;
    const pins = getPinnedSessions();
    for (const id of pins) {
      if (!ids.has(id)) { pins.delete(id); pinsDirty = true; }
    }
    if (pinsDirty) {
      savePinnedSessions(pins);
      setPinnedIds(pins);
    }
  }, [sessions, loading]);

  // Merge custom names into sessions, auto-generate titles from preview
  const sessionsWithNames = useMemo(() =>
    sessions
      .map((s) => ({
        ...s,
        customName: sessionNames[s.session_id] || s.custom_name || undefined,
        autoTitle: s.auto_title || generateTitle(s.preview),
        pinned: pinnedIds.has(s.session_id),
      }))
      .sort((a, b) => {
        // Pinned sessions first, then by last_active
        if (a.pinned && !b.pinned) return -1;
        if (!a.pinned && b.pinned) return 1;
        return new Date(b.last_active).getTime() - new Date(a.last_active).getTime();
      }),
    [sessions, sessionNames, pinnedIds],
  );

  return { sessions: sessionsWithNames, loading, error, fetchSessions, deleteSession, renameSession, togglePin, archiveSession };
}
