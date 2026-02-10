"use client";

import { useState, useEffect, useCallback, useRef } from "react";

type ConnectionStatus = "connected" | "degraded" | "disconnected" | "checking";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const POLL_INTERVAL = 30000; // 30 seconds
const INITIAL_RETRY_INTERVAL = 5000; // 5 seconds on first disconnect
const MAX_RETRY_INTERVAL = 60000; // Cap at 60 seconds

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
  const slowStreakRef = useRef(0);
  const failCountRef = useRef(0);

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
        failCountRef.current = 0;
        if (wasDisconnected) {
          window.dispatchEvent(new CustomEvent("jarvis-reconnected"));
        }
      } else {
        failCountRef.current++;
        setStatus("disconnected");
        setLatency(null);
        slowStreakRef.current = 0;
      }
    } catch {
      failCountRef.current++;
      setStatus("disconnected");
      setLatency(null);
      slowStreakRef.current = 0;
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;

    // Use setTimeout chain instead of setInterval to prevent overlap
    const scheduleNext = () => {
      if (cancelled || document.hidden) return;
      let baseInterval: number;
      if (statusRef.current === "disconnected") {
        baseInterval = Math.min(
          INITIAL_RETRY_INTERVAL * Math.pow(2, Math.max(0, failCountRef.current - 1)),
          MAX_RETRY_INTERVAL,
        );
      } else {
        baseInterval = POLL_INTERVAL;
      }
      timer = setTimeout(() => {
        if (cancelled) return;
        checkConnection().then(scheduleNext);
      }, jitter(baseInterval));
    };

    checkConnection().then(scheduleNext);

    // Pause polling when tab is hidden, resume when visible
    const handleVisibility = () => {
      if (document.hidden) {
        if (timer) { clearTimeout(timer); timer = null; }
      } else {
        checkConnection().then(scheduleNext);
      }
    };

    // Detect browser online/offline for instant feedback
    const handleOnline = () => {
      checkConnection().then(scheduleNext);
    };
    const handleOffline = () => {
      setStatus("disconnected");
      setLatency(null);
    };

    document.addEventListener("visibilitychange", handleVisibility);
    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
      document.removeEventListener("visibilitychange", handleVisibility);
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, [checkConnection]);

  return { status, latency, retry: checkConnection };
}
