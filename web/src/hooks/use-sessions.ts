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
  const [archivedSessions, setArchivedSessions] = useState<SessionEntry[]>([]);
  const [showArchived, setShowArchived] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sessionNames, setSessionNames] = useState<Record<string, string>>({});
  const [pinnedIds, setPinnedIds] = useState<Set<string>>(new Set());
  const renameTimersRef = useRef<Record<string, ReturnType<typeof setTimeout>>>({});

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

  // Listen for auto-title updates from chat stream
  useEffect(() => {
    const handler = (e: Event) => {
      const { sessionId, autoTitle } = (e as CustomEvent<{ sessionId: string; autoTitle: string }>).detail;
      if (!sessionId || !autoTitle) return;
      setSessions((prev) =>
        prev.map((s) =>
          s.session_id === sessionId ? { ...s, auto_title: autoTitle } : s,
        ),
      );
    };
    window.addEventListener("session-title-updated", handler);
    return () => window.removeEventListener("session-title-updated", handler);
  }, []);

  const fetchSessions = useCallback(async () => {
    try {
      const data = await api.get<{ sessions: SessionEntry[]; total: number }>("/api/conversation/sessions?limit=200&archived=false");
      // Handle both paginated response and legacy array format
      const list = Array.isArray(data) ? data : (data?.sessions || []);
      setSessions(list);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load sessions");
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchArchivedSessions = useCallback(async () => {
    try {
      const data = await api.get<{ sessions: SessionEntry[]; total: number }>("/api/conversation/sessions?limit=200&archived=true");
      const list = Array.isArray(data) ? data : (data?.sessions || []);
      setArchivedSessions(list);
    } catch {
      setArchivedSessions([]);
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

    // Update local name when session is renamed from chat header
    const handleSessionRenamed = (e: Event) => {
      const { sessionId, name } = (e as CustomEvent<{ sessionId: string; name: string }>).detail;
      if (sessionId && name) {
        setSessionNames((prev) => {
          const next = { ...prev, [sessionId]: name };
          saveSessionNames(next);
          return next;
        });
      }
    };

    // Sync immediately when window regains focus (e.g. user switches from another app)
    const handleFocus = () => fetchSessions();

    document.addEventListener("visibilitychange", handleVisibility);
    window.addEventListener("session-created", handleSessionCreated);
    window.addEventListener("session-renamed", handleSessionRenamed);
    window.addEventListener("focus", handleFocus);

    return () => {
      clearInterval(interval);
      document.removeEventListener("visibilitychange", handleVisibility);
      window.removeEventListener("session-created", handleSessionCreated);
      window.removeEventListener("session-renamed", handleSessionRenamed);
      window.removeEventListener("focus", handleFocus);
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
        await api.delete(`/api/conversation/sessions/${sessionId}`);
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
      // Capture previous name for rollback
      let previousName: string | undefined;
      // Optimistic local update
      setSessionNames((prev) => {
        previousName = prev[sessionId];
        const next = { ...prev };
        if (trimmed) {
          next[sessionId] = trimmed;
        } else {
          delete next[sessionId];
        }
        saveSessionNames(next);
        return next;
      });
      // Clear previous debounce timer for this session
      if (renameTimersRef.current[sessionId]) {
        clearTimeout(renameTimersRef.current[sessionId]);
      }
      // Debounce server sync (500ms)
      renameTimersRef.current[sessionId] = setTimeout(() => {
        api.patch(`/api/conversation/sessions/${sessionId}`, { name: trimmed }).catch(() => {
          // Rollback to previous name on error
          setSessionNames((prev) => {
            const next = { ...prev };
            if (previousName) {
              next[sessionId] = previousName;
            } else {
              delete next[sessionId];
            }
            saveSessionNames(next);
            return next;
          });
          _onDeleteError?.("Failed to save session name. Please try again.");
        });
        delete renameTimersRef.current[sessionId];
      }, 500);
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
        // Move from active to archived list
        setSessions((prev) => {
          const session = prev.find((s) => s.session_id === sessionId);
          if (session) setArchivedSessions((ar) => [session, ...ar]);
          return prev.filter((s) => s.session_id !== sessionId);
        });
      } catch {
        _onDeleteError?.("Failed to archive session.");
      }
    },
    [],
  );

  const unarchiveSession = useCallback(
    async (sessionId: string) => {
      try {
        await api.patch(`/api/conversation/sessions/${sessionId}/archive`, {});
        // Move from archived to active list
        setArchivedSessions((prev) => {
          const session = prev.find((s) => s.session_id === sessionId);
          if (session) setSessions((active) => [session, ...active]);
          return prev.filter((s) => s.session_id !== sessionId);
        });
      } catch {
        _onDeleteError?.("Failed to unarchive session.");
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

  return { sessions: sessionsWithNames, archivedSessions, showArchived, setShowArchived, loading, error, fetchSessions, fetchArchivedSessions, deleteSession, renameSession, togglePin, archiveSession, unarchiveSession };
}
