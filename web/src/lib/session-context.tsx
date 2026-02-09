"use client";

import { createContext, useContext, useState, useCallback } from "react";

interface SessionContextType {
  selectedSessionId: string | null;
  selectSession: (id: string) => void;
  clearSelection: () => void;
}

const SessionContext = createContext<SessionContextType>({
  selectedSessionId: null,
  selectSession: () => {},
  clearSelection: () => {},
});

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(
    null,
  );

  const selectSession = useCallback((id: string) => {
    setSelectedSessionId(id || null);
  }, []);

  const clearSelection = useCallback(() => {
    setSelectedSessionId(null);
  }, []);

  return (
    <SessionContext.Provider
      value={{ selectedSessionId, selectSession, clearSelection }}
    >
      {children}
    </SessionContext.Provider>
  );
}

export function useSessionContext() {
  return useContext(SessionContext);
}
