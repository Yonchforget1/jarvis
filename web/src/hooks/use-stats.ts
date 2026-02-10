"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { api } from "@/lib/api";
import type { SystemStats } from "@/lib/types";

export function useStats(pollInterval: number = 15000) {
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [refetching, setRefetching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const consecutiveFailures = useRef(0);
  const consecutiveSuccesses = useRef(0);

  const fetchStats = useCallback(async () => {
    try {
      const data = await api.get<SystemStats>("/api/stats");
      setStats(data);
      setError(null);
      setLastUpdated(new Date());
      consecutiveSuccesses.current++;
      // Reset backoff after 3 consecutive successes (trending healthy)
      if (consecutiveSuccesses.current >= 3) {
        consecutiveFailures.current = 0;
      }
    } catch (err) {
      consecutiveFailures.current++;
      consecutiveSuccesses.current = 0;
      setError(err instanceof Error ? err.message : "Failed to fetch stats");
    } finally {
      setLoading(false);
      setRefetching(false);
    }
  }, []);

  const refetch = useCallback(() => {
    consecutiveFailures.current = 0;
    setRefetching(true);
    return fetchStats();
  }, [fetchStats]);

  // Visibility-aware polling with exponential backoff on errors
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    let cancelled = false;

    const scheduleNext = () => {
      if (cancelled) return;
      // Exponential backoff: double interval per failure, cap at 2 minutes
      const backoff = consecutiveFailures.current > 0
        ? Math.min(pollInterval * Math.pow(2, consecutiveFailures.current), 120000)
        : pollInterval;
      timer = setTimeout(() => {
        if (!cancelled) fetchStats().then(scheduleNext);
      }, backoff);
    };

    fetchStats().then(scheduleNext);

    const handleVisibility = () => {
      if (document.hidden) {
        clearTimeout(timer);
      } else if (!cancelled) {
        fetchStats().then(scheduleNext);
      }
    };

    document.addEventListener("visibilitychange", handleVisibility);
    return () => {
      cancelled = true;
      clearTimeout(timer);
      document.removeEventListener("visibilitychange", handleVisibility);
    };
  }, [fetchStats, pollInterval]);

  return { stats, loading, refetching, error, refetch, lastUpdated };
}
