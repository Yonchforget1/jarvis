"use client";

import { createContext, useContext, useState, useCallback, useMemo, useEffect } from "react";

interface SessionContextType {
  selectedSessionId: string | null;
  selectedSessionName: string | null;
  selectSession: (id: string, name?: string) => void;
  clearSelection: () => void;
  setSessionName: (name: string) => void;
  unreadCount: number;
  incrementUnread: () => void;
  clearUnread: () => void;
  isProcessing: boolean;
  setProcessing: (v: boolean) => void;
}

const SessionContext = createContext<SessionContextType>({
  selectedSessionId: null,
  selectedSessionName: null,
  selectSession: () => {},
  clearSelection: () => {},
  setSessionName: () => {},
  unreadCount: 0,
  incrementUnread: () => {},
  clearUnread: () => {},
  isProcessing: false,
  setProcessing: () => {},
});

const SESSION_STORAGE_KEY = "jarvis-active-session";

function getPersistedSession(): { id: string; name: string | null } | null {
  try {
    const raw = localStorage.getItem(SESSION_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed.id === "string") return parsed;
  } catch { /* ignore */ }
  return null;
}

function persistSession(id: string | null, name: string | null) {
  try {
    if (id) {
      localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify({ id, name }));
    } else {
      localStorage.removeItem(SESSION_STORAGE_KEY);
    }
  } catch { /* ignore */ }
}

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(
    null,
  );
  const [selectedSessionName, setSelectedSessionName] = useState<string | null>(null);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isProcessing, setProcessing] = useState(false);

  // Restore session from localStorage on mount
  useEffect(() => {
    const saved = getPersistedSession();
    if (saved && !selectedSessionId) {
      setSelectedSessionId(saved.id);
      setSelectedSessionName(saved.name);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const selectSession = useCallback((id: string, name?: string) => {
    const sid = id || null;
    const sname = name || null;
    setSelectedSessionId(sid);
    setSelectedSessionName(sname);
    persistSession(sid, sname);
  }, []);

  const clearSelection = useCallback(() => {
    setSelectedSessionId(null);
    setSelectedSessionName(null);
    persistSession(null, null);
  }, []);

  const setSessionName = useCallback((name: string) => {
    setSelectedSessionName(name);
  }, []);

  const incrementUnread = useCallback(() => {
    setUnreadCount((prev) => prev + 1);
  }, []);

  const clearUnread = useCallback(() => {
    setUnreadCount(0);
  }, []);

  const value = useMemo(() => ({
    selectedSessionId, selectedSessionName, selectSession, clearSelection, setSessionName, unreadCount, incrementUnread, clearUnread, isProcessing, setProcessing,
  }), [selectedSessionId, selectedSessionName, selectSession, clearSelection, setSessionName, unreadCount, incrementUnread, clearUnread, isProcessing, setProcessing]);

  return (
    <SessionContext.Provider value={value}>
      {children}
    </SessionContext.Provider>
  );
}

export function useSessionContext() {
  return useContext(SessionContext);
}
