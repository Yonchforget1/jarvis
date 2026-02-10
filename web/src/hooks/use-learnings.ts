"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import type { LearningEntry } from "@/lib/types";

interface LearningsResponse {
  learnings: LearningEntry[];
  count: number;
}

export function useLearnings() {
  const [learnings, setLearnings] = useState<LearningEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchLearnings = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.get<LearningsResponse>("/api/learnings");
      setLearnings(res.learnings);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load learnings");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchLearnings();
  }, [fetchLearnings]);

  return { learnings, loading, error, refetch: fetchLearnings };
}
