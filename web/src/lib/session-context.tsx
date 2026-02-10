"use client";

import { createContext, useContext, useState, useCallback, useMemo } from "react";

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

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(
    null,
  );
  const [selectedSessionName, setSelectedSessionName] = useState<string | null>(null);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isProcessing, setProcessing] = useState(false);

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
