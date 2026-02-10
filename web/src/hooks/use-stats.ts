"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import type { SystemStats } from "@/lib/types";

export function useStats(pollInterval: number = 15000) {
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [refetching, setRefetching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchStats = useCallback(async () => {
    try {
      const data = await api.get<SystemStats>("/api/stats");
      setStats(data);
      setError(null);
      setLastUpdated(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch stats");
    } finally {
      setLoading(false);
      setRefetching(false);
    }
  }, []);

  const refetch = useCallback(() => {
    setRefetching(true);
    return fetchStats();
  }, [fetchStats]);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, pollInterval);
    return () => clearInterval(interval);
  }, [fetchStats, pollInterval]);

  return { stats, loading, refetching, error, refetch, lastUpdated };
}
