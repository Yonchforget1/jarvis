"use client";

import { createContext, useContext, useState, useCallback } from "react";

interface SessionContextType {
  selectedSessionId: string | null;
  selectedSessionName: string | null;
  selectSession: (id: string, name?: string) => void;
  clearSelection: () => void;
  setSessionName: (name: string) => void;
  unreadCount: number;
  incrementUnread: () => void;
  clearUnread: () => void;
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
});

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(
    null,
  );
  const [selectedSessionName, setSelectedSessionName] = useState<string | null>(null);
  const [unreadCount, setUnreadCount] = useState(0);

  const selectSession = useCallback((id: string, name?: string) => {
    setSelectedSessionId(id || null);
    setSelectedSessionName(name || null);
  }, []);

  const clearSelection = useCallback(() => {
    setSelectedSessionId(null);
    setSelectedSessionName(null);
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

  return (
    <SessionContext.Provider
      value={{ selectedSessionId, selectedSessionName, selectSession, clearSelection, setSessionName, unreadCount, incrementUnread, clearUnread }}
    >
      {children}
    </SessionContext.Provider>
  );
}

export function useSessionContext() {
  return useContext(SessionContext);
}
