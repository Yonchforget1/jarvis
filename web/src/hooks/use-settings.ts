"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";

interface SettingsData {
  backend: string;
  model: string;
  has_api_key: boolean;
  max_tokens: number;
  disabled_tools: string[];
}

interface ModelOption {
  id: string;
  name: string;
  description: string;
}

interface BackendOption {
  id: string;
  name: string;
  key_env: string;
}

interface ModelsData {
  backends: BackendOption[];
  models: Record<string, ModelOption[]>;
}

export function useSettings() {
  const [settings, setSettings] = useState<SettingsData | null>(null);
  const [modelsData, setModelsData] = useState<ModelsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSettings = useCallback(async () => {
    try {
      setLoading(true);
      const [settingsRes, modelsRes] = await Promise.all([
        api.get<SettingsData>("/api/settings"),
        api.get<ModelsData>("/api/settings/models"),
      ]);
      setSettings(settingsRes);
      setModelsData(modelsRes);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load settings");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSettings();
  }, [fetchSettings]);

  const updateSettings = useCallback(
    async (update: Partial<{
      backend: string;
      model: string;
      api_key: string;
      max_tokens: number;
      disabled_tools: string[];
    }>) => {
      setSaving(true);
      setError(null);
      try {
        const res = await api.put<SettingsData>("/api/settings", update);
        setSettings(res);
        return res;
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Failed to save settings";
        setError(msg);
        throw err;
      } finally {
        setSaving(false);
      }
    },
    [],
  );

  return { settings, modelsData, loading, saving, error, updateSettings, refetch: fetchSettings };
}
