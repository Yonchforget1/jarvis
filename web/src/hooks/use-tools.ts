"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import type { ToolInfo } from "@/lib/types";

interface ToolsResponse {
  tools: ToolInfo[];
  count: number;
}

export function useTools() {
  const [tools, setTools] = useState<ToolInfo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get<ToolsResponse>("/api/tools")
      .then((res) => setTools(res.tools))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return { tools, loading };
}
