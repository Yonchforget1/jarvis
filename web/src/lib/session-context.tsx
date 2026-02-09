"use client";

import { createContext, useContext, useState, useCallback } from "react";

interface SessionContextType {
  selectedSessionId: string | null;
  selectSession: (id: string) => void;
  clearSelection: () => void;
  unreadCount: number;
  incrementUnread: () => void;
  clearUnread: () => void;
}

const SessionContext = createContext<SessionContextType>({
  selectedSessionId: null,
  selectSession: () => {},
  clearSelection: () => {},
  unreadCount: 0,
  incrementUnread: () => {},
  clearUnread: () => {},
});

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(
    null,
  );
  const [unreadCount, setUnreadCount] = useState(0);

  const selectSession = useCallback((id: string) => {
    setSelectedSessionId(id || null);
  }, []);

  const clearSelection = useCallback(() => {
    setSelectedSessionId(null);
  }, []);

  const incrementUnread = useCallback(() => {
    setUnreadCount((prev) => prev + 1);
  }, []);

  const clearUnread = useCallback(() => {
    setUnreadCount(0);
  }, []);

  return (
    <SessionContext.Provider
      value={{ selectedSessionId, selectSession, clearSelection, unreadCount, incrementUnread, clearUnread }}
    >
      {children}
    </SessionContext.Provider>
  );
}

export function useSessionContext() {
  return useContext(SessionContext);
}
