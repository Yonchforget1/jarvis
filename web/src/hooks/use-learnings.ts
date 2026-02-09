"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import type { LearningEntry } from "@/lib/types";

interface LearningsResponse {
  learnings: LearningEntry[];
  count: number;
}

export function useLearnings() {
  const [learnings, setLearnings] = useState<LearningEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get<LearningsResponse>("/api/learnings")
      .then((res) => setLearnings(res.learnings))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return { learnings, loading };
}
