"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import type { ToolInfo } from "@/lib/types";

interface ToolsResponse {
  tools: ToolInfo[];
  count: number;
}

const CACHE_KEY = "jarvis_tools_cache";
const CACHE_TTL_MS = 30 * 60 * 1000; // 30 minutes

function getCachedTools(): ToolInfo[] | null {
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (parsed && Array.isArray(parsed.tools) && typeof parsed.ts === "number") {
      if (Date.now() - parsed.ts < CACHE_TTL_MS) return parsed.tools;
    }
    localStorage.removeItem(CACHE_KEY);
  } catch { /* ignore */ }
  return null;
}

function setCachedTools(tools: ToolInfo[]) {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify({ tools, ts: Date.now() }));
  } catch { /* ignore */ }
}

export function useTools() {
  const [tools, setTools] = useState<ToolInfo[]>(() => getCachedTools() || []);
  const [loading, setLoading] = useState(() => getCachedTools() === null);
  const [error, setError] = useState<string | null>(null);

  const fetchTools = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.get<ToolsResponse>("/api/tools");
      setTools(res.tools);
      setCachedTools(res.tools);
      setError(null);
    } catch (err) {
      // If we have cached data, don't show error
      const cached = getCachedTools();
      if (cached) {
        setTools(cached);
        setError(null);
      } else {
        setError(err instanceof Error ? err.message : "Failed to load tools");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // If we loaded from cache, still fetch fresh data in background
    const cached = getCachedTools();
    if (cached) {
      setTools(cached);
      setLoading(false);
      // Background refresh
      api.get<ToolsResponse>("/api/tools")
        .then((res) => {
          setTools(res.tools);
          setCachedTools(res.tools);
        })
        .catch(() => {});
    } else {
      fetchTools();
    }
  }, [fetchTools]);

  return { tools, loading, error, refetch: fetchTools };
}
