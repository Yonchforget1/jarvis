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

export function useSessions() {
  const [sessions, setSessions] = useState<SessionEntry[]>([]);
  const [loading, setLoading] = useState(true);

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
      } catch {
        // Silently fail
      }
    },
    [],
  );

  return { sessions, loading, fetchSessions, deleteSession };
}
