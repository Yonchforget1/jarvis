"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import type { SystemStats } from "@/lib/types";

export function useStats() {
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get<SystemStats>("/api/stats")
      .then(setStats)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return { stats, loading };
}
