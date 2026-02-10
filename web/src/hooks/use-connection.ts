"use client";

import { useState, useEffect, useCallback, useRef } from "react";

type ConnectionStatus = "connected" | "disconnected" | "checking";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const POLL_INTERVAL = 30000; // 30 seconds
const RETRY_INTERVAL = 5000; // 5 seconds when disconnected

export function useConnection() {
  const [status, setStatus] = useState<ConnectionStatus>("checking");
  const [latency, setLatency] = useState<number | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

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

    const startPolling = () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
      intervalRef.current = setInterval(checkConnection, POLL_INTERVAL);
    };

    startPolling();

    // Poll faster when disconnected
    const statusCheck = setInterval(() => {
      if (status === "disconnected") {
        checkConnection();
      }
    }, RETRY_INTERVAL);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
      clearInterval(statusCheck);
    };
  }, [checkConnection, status]);

  return { status, latency, retry: checkConnection };
}
