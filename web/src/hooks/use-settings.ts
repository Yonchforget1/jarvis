"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";

const SETTINGS_CACHE_KEY = "jarvis-settings-cache";
const MODELS_CACHE_KEY = "jarvis-models-cache";
const CACHE_TTL_MS = 10 * 60 * 1000; // 10 minutes

function getCached<T>(key: string): T | null {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    const { data, ts } = JSON.parse(raw);
    if (Date.now() - ts > CACHE_TTL_MS) {
      localStorage.removeItem(key);
      return null;
    }
    return data as T;
  } catch {
    return null;
  }
}

function setCache(key: string, data: unknown) {
  try {
    localStorage.setItem(key, JSON.stringify({ data, ts: Date.now() }));
  } catch {}
}

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
      // Show cached data immediately while fetching fresh
      const cachedSettings = getCached<SettingsData>(SETTINGS_CACHE_KEY);
      const cachedModels = getCached<ModelsData>(MODELS_CACHE_KEY);
      if (cachedSettings && cachedModels) {
        setSettings(cachedSettings);
        setModelsData(cachedModels);
        setLoading(false);
      } else {
        setLoading(true);
      }

      const [settingsRes, modelsRes] = await Promise.all([
        api.get<SettingsData>("/api/settings"),
        api.get<ModelsData>("/api/settings/models"),
      ]);
      setSettings(settingsRes);
      setModelsData(modelsRes);
      setCache(SETTINGS_CACHE_KEY, settingsRes);
      setCache(MODELS_CACHE_KEY, modelsRes);
      setError(null);
    } catch (err) {
      // If we have cached data, don't show error
      if (!settings) {
        setError(err instanceof Error ? err.message : "Failed to load settings");
      }
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
        setCache(SETTINGS_CACHE_KEY, res);
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
