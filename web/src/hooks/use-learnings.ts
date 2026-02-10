"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { api } from "@/lib/api";
import type { LearningEntry } from "@/lib/types";

interface LearningsResponse {
  learnings: LearningEntry[];
  count: number;
  total: number;
  page: number;
  page_size: number;
}

interface UseLearningsOptions {
  search?: string;
  sort?: "newest" | "oldest" | "category";
  category?: string;
  page?: number;
  pageSize?: number;
}

export function useLearnings(options: UseLearningsOptions = {}) {
  const { search, sort = "newest", category, page = 1, pageSize = 200 } = options;
  const [learnings, setLearnings] = useState<LearningEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Debounce search to avoid excessive API calls
  const [debouncedSearch, setDebouncedSearch] = useState(search);
  const searchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    searchTimerRef.current = setTimeout(() => setDebouncedSearch(search), 300);
    return () => { if (searchTimerRef.current) clearTimeout(searchTimerRef.current); };
  }, [search]);

  const fetchLearnings = useCallback(async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (debouncedSearch) params.set("search", debouncedSearch);
      if (sort) params.set("sort", sort);
      if (category) params.set("category", category);
      params.set("page", String(page));
      params.set("page_size", String(pageSize));
      const qs = params.toString();
      const res = await api.get<LearningsResponse>(`/api/learnings${qs ? `?${qs}` : ""}`);
      setLearnings(res.learnings);
      setTotal(res.total);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load learnings");
    } finally {
      setLoading(false);
    }
  }, [debouncedSearch, sort, category, page, pageSize]);

  useEffect(() => {
    fetchLearnings();
  }, [fetchLearnings]);

  return { learnings, total, loading, error, refetch: fetchLearnings };
}
