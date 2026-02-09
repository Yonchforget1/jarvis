"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import type { ToolInfo } from "@/lib/types";

interface ToolsResponse {
  tools: ToolInfo[];
  count: number;
}

export function useTools() {
  const [tools, setTools] = useState<ToolInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchTools = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.get<ToolsResponse>("/api/tools");
      setTools(res.tools);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load tools");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTools();
  }, [fetchTools]);

  return { tools, loading, error, refetch: fetchTools };
}
