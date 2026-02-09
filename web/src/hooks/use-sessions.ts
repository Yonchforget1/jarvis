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

export function useSessions() {
  const [sessions, setSessions] = useState<SessionEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [sessionNames, setSessionNames] = useState<Record<string, string>>({});

  // Load custom names from localStorage
  useEffect(() => {
    setSessionNames(getSessionNames());
  }, []);

  const fetchSessions = useCallback(async () => {
    try {
      const data = await api.get<SessionEntry[]>("/api/sessions");
      setSessions(data);
    } catch {
      // Silently fail - sessions are not critical
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  const deleteSession = useCallback(
    async (sessionId: string) => {
      try {
        await api.delete(`/api/sessions/${sessionId}`);
        setSessions((prev) => prev.filter((s) => s.session_id !== sessionId));
        // Clean up custom name
        setSessionNames((prev) => {
          const next = { ...prev };
          delete next[sessionId];
          saveSessionNames(next);
          return next;
        });
      } catch {
        // Silently fail
      }
    },
    [],
  );

  const renameSession = useCallback(
    (sessionId: string, name: string) => {
      setSessionNames((prev) => {
        const next = { ...prev };
        if (name.trim()) {
          next[sessionId] = name.trim();
        } else {
          delete next[sessionId];
        }
        saveSessionNames(next);
        return next;
      });
    },
    [],
  );

  // Merge custom names into sessions
  const sessionsWithNames = sessions.map((s) => ({
    ...s,
    customName: sessionNames[s.session_id] || undefined,
  }));

  return { sessions: sessionsWithNames, loading, fetchSessions, deleteSession, renameSession };
}
