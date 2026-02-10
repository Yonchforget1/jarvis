"use client";

import { useState, useEffect, useCallback, useRef } from "react";

type ConnectionStatus = "connected" | "degraded" | "disconnected" | "checking";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const POLL_INTERVAL = 30000; // 30 seconds
const RETRY_INTERVAL = 5000; // 5 seconds when disconnected

// Add ±10% jitter to prevent thundering herd across multiple tabs
function jitter(interval: number): number {
  const variance = interval * 0.1;
  return interval + (Math.random() * 2 - 1) * variance;
}
const DEGRADED_LATENCY_MS = 500; // Consider degraded above this
const DEGRADED_STREAK_THRESHOLD = 3; // Consecutive slow checks to trigger degraded

export function useConnection() {
  const [status, setStatus] = useState<ConnectionStatus>("checking");
  const [latency, setLatency] = useState<number | null>(null);
  const statusRef = useRef<ConnectionStatus>("checking");
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const slowStreakRef = useRef(0);

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
        const ms = Date.now() - start;
        const wasDisconnected = statusRef.current === "disconnected";
        setLatency(ms);
        if (ms > DEGRADED_LATENCY_MS) {
          slowStreakRef.current++;
        } else {
          slowStreakRef.current = 0;
        }
        if (slowStreakRef.current >= DEGRADED_STREAK_THRESHOLD) {
          setStatus("degraded");
        } else {
          setStatus("connected");
        }
        if (wasDisconnected) {
          window.dispatchEvent(new CustomEvent("jarvis-reconnected"));
        }
      } else {
        setStatus("disconnected");
        setLatency(null);
        slowStreakRef.current = 0;
      }
    } catch {
      setStatus("disconnected");
      setLatency(null);
      slowStreakRef.current = 0;
    }
  }, []);

  useEffect(() => {
    checkConnection();

    // Adaptive polling with jitter: faster when disconnected
    const poll = () => {
      const baseInterval = statusRef.current === "disconnected" ? RETRY_INTERVAL : POLL_INTERVAL;
      const interval = jitter(baseInterval);
      if (intervalRef.current) clearInterval(intervalRef.current);
      intervalRef.current = setInterval(() => {
        checkConnection().then(() => {
          // Re-adjust interval if status changed
          const newBase = statusRef.current === "disconnected" ? RETRY_INTERVAL : POLL_INTERVAL;
          if (newBase !== baseInterval) poll();
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
