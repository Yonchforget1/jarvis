"use client";

import { useState, useEffect, useCallback, useRef } from "react";

type ConnectionStatus = "connected" | "disconnected" | "checking";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const POLL_INTERVAL = 30000; // 30 seconds
const RETRY_INTERVAL = 5000; // 5 seconds when disconnected

export function useConnection() {
  const [status, setStatus] = useState<ConnectionStatus>("checking");
  const [latency, setLatency] = useState<number | null>(null);
  const statusRef = useRef<ConnectionStatus>("checking");
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Keep statusRef in sync without causing re-renders in the effect
  statusRef.current = status;

  const checkConnection = useCallback(async () => {
    const start = Date.now();
    try {
      const res = await fetch(`${API_URL}/api/health`, {
        method: "GET",
        signal: AbortSignal.timeout(5000),
      });
      if (res.ok) {
        setStatus("connected");
        setLatency(Date.now() - start);
      } else {
        setStatus("disconnected");
        setLatency(null);
      }
    } catch {
      setStatus("disconnected");
      setLatency(null);
    }
  }, []);

  useEffect(() => {
    checkConnection();

    // Adaptive polling: faster when disconnected
    const poll = () => {
      const interval = statusRef.current === "disconnected" ? RETRY_INTERVAL : POLL_INTERVAL;
      if (intervalRef.current) clearInterval(intervalRef.current);
      intervalRef.current = setInterval(() => {
        checkConnection().then(() => {
          // Re-adjust interval if status changed
          const newInterval = statusRef.current === "disconnected" ? RETRY_INTERVAL : POLL_INTERVAL;
          if (newInterval !== interval) poll();
        });
      }, interval);
    };
    poll();

    // Pause polling when tab is hidden
    const handleVisibility = () => {
      if (document.hidden) {
        if (intervalRef.current) clearInterval(intervalRef.current);
      } else {
        checkConnection();
        poll();
      }
    };

    // Detect browser online/offline for instant feedback
    const handleOnline = () => checkConnection();
    const handleOffline = () => {
      setStatus("disconnected");
      setLatency(null);
    };

    document.addEventListener("visibilitychange", handleVisibility);
    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
      document.removeEventListener("visibilitychange", handleVisibility);
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, [checkConnection]);

  return { status, latency, retry: checkConnection };
}
