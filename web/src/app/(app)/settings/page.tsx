"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import {
  Cpu,
  Key,
  Lock,
  Wrench,
  Save,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Eye,
  EyeOff,
  Sparkles,
  Sliders,
  Download,
  Upload,
  Trash2,
  AlertTriangle,
  Sun,
  Moon,
  Monitor,
  RotateCcw,
  Plus,
  Copy,
  X,
  Bell,
  BellOff,
} from "lucide-react";
import { useTheme } from "next-themes";
import { useSettings } from "@/hooks/use-settings";
import { useLearnings } from "@/hooks/use-learnings";
import { useToast } from "@/components/ui/toast";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { ErrorState } from "@/components/ui/error-state";
import { api } from "@/lib/api";

export default function SettingsPage() {
  const { settings, modelsData, loading, saving, error: settingsError, updateSettings, refetch } = useSettings();
  const { learnings } = useLearnings();
  const toast = useToast();
  const { theme, setTheme } = useTheme();

  const [backend, setBackend] = useState("");
  const [model, setModel] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [maxTokens, setMaxTokens] = useState(4096);
  const [showApiKey, setShowApiKey] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});
  const [clearingAllSessions, setClearingAllSessions] = useState(false);
  const [confirmClear, setConfirmClear] = useState(false);
  const confirmTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Password change
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [changingPassword, setChangingPassword] = useState(false);
  const [showOldPassword, setShowOldPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);

  const handleChangePassword = async () => {
    if (changingPassword) return;
    if (newPassword.length < 8) {
      toast.error("Too short", "New password must be at least 8 characters.");
      return;
    }
    if (newPassword !== confirmPassword) {
      toast.error("Mismatch", "New passwords do not match.");
      return;
    }
    setChangingPassword(true);
    try {
      await api.post("/api/auth/change-password", { old_password: oldPassword, new_password: newPassword });
      toast.success("Password changed", "Your password has been updated.");
      setOldPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err) {
      toast.error("Failed", err instanceof Error ? err.message : "Could not change password.");
    } finally {
      setChangingPassword(false);
    }
  };

  // Notification preferences
  const [notificationsEnabled, setNotificationsEnabled] = useState(() => {
    if (typeof window === "undefined") return true;
    try {
      const saved = localStorage.getItem("jarvis_notifications");
      if (saved) return JSON.parse(saved).enabled !== false;
    } catch { /* ignore */ }
    return true;
  });
  const [notificationSound, setNotificationSound] = useState(() => {
    if (typeof window === "undefined") return false;
    try {
      const saved = localStorage.getItem("jarvis_notifications");
      if (saved) return JSON.parse(saved).sound === true;
    } catch { /* ignore */ }
    return false;
  });

  const handleToggleNotifications = (enabled: boolean) => {
    setNotificationsEnabled(enabled);
    try {
      const current = JSON.parse(localStorage.getItem("jarvis_notifications") || "{}");
      localStorage.setItem("jarvis_notifications", JSON.stringify({ ...current, enabled }));
    } catch { /* ignore */ }
    if (enabled && typeof Notification !== "undefined" && Notification.permission === "default") {
      Notification.requestPermission();
    }
  };

  const handleToggleSound = (sound: boolean) => {
    setNotificationSound(sound);
    try {
      const current = JSON.parse(localStorage.getItem("jarvis_notifications") || "{}");
      localStorage.setItem("jarvis_notifications", JSON.stringify({ ...current, sound }));
    } catch { /* ignore */ }
  };

  // Tool groups (fetched dynamically)
  const [toolGroups, setToolGroups] = useState<{ name: string; count: number; color: string }[]>([]);

  // API Key management
  const [apiKeys, setApiKeys] = useState<{ id: string; label: string; prefix: string; created_at: string; last_used: string | null }[]>([]);
  const [apiKeysLoading, setApiKeysLoading] = useState(false);
  const [newKeyLabel, setNewKeyLabel] = useState("");
  const [newKeyValue, setNewKeyValue] = useState<string | null>(null);
  const [creatingKey, setCreatingKey] = useState(false);

  const fetchApiKeys = useCallback(async () => {
    setApiKeysLoading(true);
    try {
      const res = await api.get<{ api_keys: typeof apiKeys }>("/api/auth/api-keys");
      setApiKeys(res.api_keys);
    } catch {
      // Non-critical, silently fail
    } finally {
      setApiKeysLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchApiKeys();
  }, [fetchApiKeys]);

  // Fetch tool groups dynamically
  const CATEGORY_COLORS: Record<string, string> = {
    filesystem: "text-blue-400", execution: "text-green-400", web: "text-orange-400",
    gamedev: "text-purple-400", memory: "text-yellow-400", computer: "text-cyan-400",
    browser: "text-pink-400", other: "text-muted-foreground",
  };
  useEffect(() => {
    api.get<{ tools: { category: string }[] }>("/api/tools")
      .then((res) => {
        const counts: Record<string, number> = {};
        for (const t of res.tools) {
          const cat = t.category || "other";
          counts[cat] = (counts[cat] || 0) + 1;
        }
        setToolGroups(
          Object.entries(counts)
            .sort(([a], [b]) => a.localeCompare(b))
            .map(([name, count]) => ({
              name: name.charAt(0).toUpperCase() + name.slice(1),
              count,
              color: CATEGORY_COLORS[name] || "text-muted-foreground",
            }))
        );
      })
      .catch(() => {});
  }, []);

  const handleCreateApiKey = async () => {
    if (creatingKey) return;
    setCreatingKey(true);
    try {
      const res = await api.post<{ api_key: { id: string; key: string; label: string; prefix: string } }>("/api/auth/api-keys", { label: newKeyLabel || "default" });
      setNewKeyValue(res.api_key.key);
      setNewKeyLabel("");
      fetchApiKeys();
    } catch {
      toast.error("Failed", "Could not create API key.");
    } finally {
      setCreatingKey(false);
    }
  };

  const handleRevokeApiKey = async (keyId: string) => {
    try {
      await api.delete(`/api/auth/api-keys/${keyId}`);
      setApiKeys((prev) => prev.filter((k) => k.id !== keyId));
      toast.success("Revoked", "API key has been revoked.");
    } catch {
      toast.error("Failed", "Could not revoke API key.");
    }
  };

  const handleCopyKey = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success("Copied", "API key copied to clipboard.");
  };

  // Initialize form from settings
  useEffect(() => {
    if (settings) {
      setBackend(settings.backend);
      setModel(settings.model);
      setMaxTokens(settings.max_tokens);
    }
  }, [settings]);

  // Track changes
  useEffect(() => {
    if (!settings) return;
    const changed =
      backend !== settings.backend ||
      model !== settings.model ||
      maxTokens !== settings.max_tokens ||
      apiKey.length > 0;
    setHasChanges(changed);
  }, [backend, model, maxTokens, apiKey, settings]);

  // Warn before leaving with unsaved changes
  useEffect(() => {
    if (!hasChanges) return;
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      e.preventDefault();
    };
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [hasChanges]);

  const handleBackendChange = (newBackend: string) => {
    setBackend(newBackend);
    const models = modelsData?.models[newBackend];
    if (models && models.length > 0) {
      setModel(models[0].id);
    }
  };

  // Cleanup confirmClear timer on unmount
  useEffect(() => {
    return () => {
      if (confirmTimerRef.current) clearTimeout(confirmTimerRef.current);
    };
  }, []);

  const validateForm = useCallback((): boolean => {
    const errors: Record<string, string> = {};
    if (maxTokens < 256 || maxTokens > 32768) {
      errors.maxTokens = "Must be between 256 and 32,768";
    }
    if (apiKey && apiKey.length > 0 && apiKey.length < 10) {
      errors.apiKey = "API key appears too short";
    }
    if (!backend) {
      errors.backend = "Please select a backend";
    }
    if (!model) {
      errors.model = "Please select a model";
    }
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  }, [maxTokens, apiKey, backend, model]);

  const handleSave = async () => {
    if (saving) return;
    if (!validateForm()) {
      toast.error("Validation failed", "Please fix the highlighted errors.");
      return;
    }
    try {
      const update: Partial<{
        backend: string;
        model: string;
        api_key: string;
        max_tokens: number;
      }> = {};
      if (backend !== settings?.backend) update.backend = backend;
      if (model !== settings?.model) update.model = model;
      if (maxTokens !== settings?.max_tokens) update.max_tokens = maxTokens;
      if (apiKey) update.api_key = apiKey;

      await updateSettings(update);
      setApiKey("");
      setHasChanges(false);
      setFormErrors({});
      toast.success("Settings saved", "Your preferences have been updated.");
    } catch {
      toast.error("Failed to save", "Please check your settings and try again.");
    }
  };

  const importFileRef = useRef<HTMLInputElement>(null);

  const handleImportSettings = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = async (event) => {
      try {
        const data = JSON.parse(event.target?.result as string);
        if (data.backend) setBackend(data.backend);
        if (data.model) setModel(data.model);
        if (data.max_tokens && typeof data.max_tokens === "number") {
          setMaxTokens(Math.max(256, Math.min(32768, data.max_tokens)));
        }
        if (data.theme) {
          setTheme(data.theme);
        }
        setHasChanges(true);
        toast.success("Settings imported", "Review the values below and click Save to apply.");
      } catch {
        toast.error("Import failed", "The file does not contain valid settings JSON.");
      }
    };
    reader.readAsText(file);
    // Reset input so the same file can be re-imported
    e.target.value = "";
  };

  const handleResetOnboarding = () => {
    localStorage.removeItem("jarvis-onboarding-seen");
    toast.success("Onboarding reset", "The welcome tour will show on your next page load.");
  };

  const handleExportSettings = () => {
    const data = JSON.stringify(
      {
        exported_at: new Date().toISOString(),
        backend,
        model,
        max_tokens: maxTokens,
        theme,
      },
      null,
      2,
    );
    const blob = new Blob([data], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `jarvis-settings-${new Date().toISOString().split("T")[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast.success("Settings exported", "Your configuration has been downloaded.");
  };

  const handleExportLearnings = () => {
    const data = JSON.stringify(learnings, null, 2);
    const blob = new Blob([data], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `jarvis-learnings-${new Date().toISOString().split("T")[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast.success("Export complete", `${learnings.length} learnings exported.`);
  };

  const handleClearAllSessions = async () => {
    if (!confirmClear) {
      setConfirmClear(true);
      if (confirmTimerRef.current) clearTimeout(confirmTimerRef.current);
      confirmTimerRef.current = setTimeout(() => setConfirmClear(false), 5000);
      return;
    }
    setClearingAllSessions(true);
    try {
      const res = await api.get<{ sessions: { session_id: string }[] }>("/api/conversation/sessions");
      const ids = res.sessions.map((s) => s.session_id);
      if (ids.length === 0) {
        toast.info("No sessions", "There are no sessions to delete.");
        setConfirmClear(false);
        return;
      }
      const result = await api.post<{ deleted_count: number }>("/api/conversation/sessions/bulk-delete", { session_ids: ids });
      setConfirmClear(false);
      toast.success("Sessions cleared", `${result.deleted_count} sessions deleted.`);
    } catch {
      toast.error("Failed", "Could not clear all sessions.");
    } finally {
      setClearingAllSessions(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="flex items-center gap-3 animate-fade-in-up">
          <Loader2 className="h-5 w-5 animate-spin text-primary" />
          <span className="text-sm text-muted-foreground">Loading settings...</span>
        </div>
      </div>
    );
  }

  if (settingsError && !settings) {
    return (
      <div className="h-full overflow-y-auto p-4 sm:p-6">
        <div className="mx-auto max-w-2xl">
          <ErrorState message={settingsError} onRetry={refetch} />
        </div>
      </div>
    );
  }

  const currentModels = modelsData?.models[backend] || [];

  const themeOptions = [
    { id: "light", label: "Light", icon: Sun },
    { id: "dark", label: "Dark", icon: Moon },
    { id: "system", label: "System", icon: Monitor },
  ];

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-2xl space-y-6 p-4 sm:p-6 pb-20 animate-fade-in-up">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Configure your AI backend, model, appearance, and data.
          </p>
        </div>

        {/* Theme */}
        <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Sun className="h-4 w-4 text-primary" />
              Appearance
            </CardTitle>
            <CardDescription>Choose how Jarvis looks</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-3">
              {themeOptions.map((opt) => (
                <button
                  key={opt.id}
                  onClick={() => setTheme(opt.id)}
                  className={`relative flex flex-col items-center gap-2 rounded-xl border p-4 transition-all duration-200 ${
                    theme === opt.id
                      ? "border-primary/50 bg-primary/5 shadow-sm shadow-primary/10"
                      : "border-border/50 bg-muted/30 hover:border-border hover:bg-muted/50"
                  }`}
                >
                  {theme === opt.id && (
                    <CheckCircle2 className="absolute top-2 right-2 h-4 w-4 text-primary" />
                  )}
                  <opt.icon className={`h-5 w-5 ${theme === opt.id ? "text-primary" : "text-muted-foreground"}`} />
                  <span className={`text-sm font-medium ${theme === opt.id ? "text-primary" : ""}`}>
                    {opt.label}
                  </span>
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Notifications */}
        <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Bell className="h-4 w-4 text-primary" />
              Notifications
            </CardTitle>
            <CardDescription>Control how Jarvis notifies you about new responses</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <button
              onClick={() => handleToggleNotifications(!notificationsEnabled)}
              className={`flex w-full items-center justify-between rounded-xl border p-3 transition-all duration-200 ${
                notificationsEnabled
                  ? "border-primary/50 bg-primary/5"
                  : "border-border/50 bg-muted/30 hover:border-border"
              }`}
            >
              <div className="flex items-center gap-3">
                {notificationsEnabled ? (
                  <Bell className="h-4 w-4 text-primary" />
                ) : (
                  <BellOff className="h-4 w-4 text-muted-foreground" />
                )}
                <div className="text-left">
                  <p className={`text-sm font-medium ${notificationsEnabled ? "text-primary" : ""}`}>
                    Desktop Notifications
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {notificationsEnabled ? "You'll be notified when Jarvis responds in a background tab" : "Notifications are disabled"}
                  </p>
                </div>
              </div>
              <div className={`relative h-6 w-11 rounded-full transition-colors ${notificationsEnabled ? "bg-primary" : "bg-muted"}`}>
                <div className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow-sm transition-transform ${notificationsEnabled ? "translate-x-5" : "translate-x-0.5"}`} />
              </div>
            </button>
            <button
              onClick={() => handleToggleSound(!notificationSound)}
              disabled={!notificationsEnabled}
              className={`flex w-full items-center justify-between rounded-xl border p-3 transition-all duration-200 ${
                !notificationsEnabled ? "opacity-50 cursor-not-allowed" : ""
              } ${
                notificationSound
                  ? "border-primary/50 bg-primary/5"
                  : "border-border/50 bg-muted/30 hover:border-border"
              }`}
            >
              <div className="text-left">
                <p className={`text-sm font-medium ${notificationSound ? "text-primary" : ""}`}>
                  Notification Sound
                </p>
                <p className="text-xs text-muted-foreground">Play a sound when a response arrives</p>
              </div>
              <div className={`relative h-6 w-11 rounded-full transition-colors ${notificationSound && notificationsEnabled ? "bg-primary" : "bg-muted"}`}>
                <div className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow-sm transition-transform ${notificationSound && notificationsEnabled ? "translate-x-5" : "translate-x-0.5"}`} />
              </div>
            </button>
            {typeof Notification !== "undefined" && Notification.permission === "denied" && notificationsEnabled && (
              <p className="text-[10px] text-yellow-400 flex items-center gap-1 animate-fade-in">
                <AlertCircle className="h-3 w-3" />
                Browser notifications are blocked. Please allow them in your browser settings.
              </p>
            )}
          </CardContent>
        </Card>

        {/* AI Backend */}
        <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Cpu className="h-4 w-4 text-primary" />
              AI Backend
            </CardTitle>
            <CardDescription>Choose which AI provider powers Jarvis</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {modelsData?.backends.map((b) => (
                <button
                  key={b.id}
                  onClick={() => handleBackendChange(b.id)}
                  className={`relative flex flex-col items-center gap-2 rounded-xl border p-4 transition-all duration-200 ${
                    backend === b.id
                      ? "border-primary/50 bg-primary/5 shadow-sm shadow-primary/10"
                      : "border-border/50 bg-muted/30 hover:border-border hover:bg-muted/50"
                  }`}
                >
                  {backend === b.id && (
                    <CheckCircle2 className="absolute top-2 right-2 h-4 w-4 text-primary" />
                  )}
                  <Sparkles className={`h-5 w-5 ${backend === b.id ? "text-primary" : "text-muted-foreground"}`} />
                  <span className={`text-sm font-medium ${backend === b.id ? "text-primary" : ""}`}>
                    {b.name}
                  </span>
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Model Selection */}
        <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Sliders className="h-4 w-4 text-primary" />
              Model
            </CardTitle>
            <CardDescription>Select the AI model for this backend</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              {currentModels.map((m) => (
                <button
                  key={m.id}
                  onClick={() => setModel(m.id)}
                  className={`flex w-full items-center justify-between rounded-xl border p-3 transition-all duration-200 ${
                    model === m.id
                      ? "border-primary/50 bg-primary/5"
                      : "border-border/50 bg-muted/30 hover:border-border"
                  }`}
                >
                  <div className="text-left">
                    <p className={`text-sm font-medium ${model === m.id ? "text-primary" : ""}`}>
                      {m.name}
                    </p>
                    <p className="text-xs text-muted-foreground">{m.description}</p>
                  </div>
                  {model === m.id && (
                    <CheckCircle2 className="h-4 w-4 text-primary shrink-0" />
                  )}
                </button>
              ))}
            </div>

            <Separator className="bg-border/50" />

            {/* Max tokens */}
            <div className="space-y-2">
              <Label htmlFor="max_tokens">Max Tokens</Label>
              <div className="flex items-center gap-3">
                <Input
                  id="max_tokens"
                  type="number"
                  min={256}
                  max={32768}
                  value={maxTokens}
                  onChange={(e) => setMaxTokens(Number(e.target.value))}
                  onBlur={() => setMaxTokens(Math.max(256, Math.min(32768, maxTokens || 4096)))}
                  aria-invalid={maxTokens < 256 || maxTokens > 32768}
                  className={`w-32 bg-secondary/50 ${
                    maxTokens < 256 || maxTokens > 32768
                      ? "border-red-500/50 focus:border-red-500/50"
                      : "border-border/50"
                  }`}
                />
                <span className="text-xs text-muted-foreground">
                  (256 - 32,768)
                </span>
              </div>
              {(maxTokens < 256 || maxTokens > 32768) && (
                <p className="text-[10px] text-red-400 flex items-center gap-1 animate-fade-in">
                  <AlertCircle className="h-3 w-3" />
                  Value will be clamped to valid range on blur
                </p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* API Key */}
        <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Key className="h-4 w-4 text-primary" />
              API Key
            </CardTitle>
            <CardDescription>
              {settings?.has_api_key ? (
                <span className="flex items-center gap-1.5">
                  <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />
                  API key is configured
                </span>
              ) : (
                <span className="flex items-center gap-1.5">
                  <AlertCircle className="h-3.5 w-3.5 text-yellow-500" />
                  No API key set. Using server default.
                </span>
              )}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <Label htmlFor="api_key">
                {modelsData?.backends.find((b) => b.id === backend)?.key_env || "API Key"}
              </Label>
              <div className="relative">
                <Input
                  id="api_key"
                  type={showApiKey ? "text" : "password"}
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="Enter your API key to override server default"
                  maxLength={256}
                  autoComplete="off"
                  aria-invalid={!!formErrors.apiKey}
                  className={`pr-10 bg-secondary/50 ${formErrors.apiKey ? "border-red-500/50" : "border-border/50"}`}
                />
                <button
                  type="button"
                  onClick={() => setShowApiKey(!showApiKey)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                >
                  {showApiKey ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
              {formErrors.apiKey ? (
                <p className="text-[10px] text-red-400 flex items-center gap-1 animate-fade-in">
                  <AlertCircle className="h-3 w-3" />
                  {formErrors.apiKey}
                </p>
              ) : (
                <p className="text-[10px] text-muted-foreground/60">
                  Your key is stored securely and used only for your sessions.
                </p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* API Keys Management */}
        <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Key className="h-4 w-4 text-primary" />
              API Keys
            </CardTitle>
            <CardDescription>Create and manage API keys for programmatic access</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Create new key */}
            <div className="flex items-center gap-2">
              <Input
                value={newKeyLabel}
                onChange={(e) => setNewKeyLabel(e.target.value)}
                placeholder="Key label (e.g. 'CI/CD', 'Mobile app')"
                maxLength={64}
                className="bg-secondary/50 border-border/50 text-sm"
              />
              <Button
                variant="outline"
                size="sm"
                onClick={handleCreateApiKey}
                disabled={creatingKey}
                className="shrink-0 gap-1.5"
              >
                {creatingKey ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Plus className="h-3.5 w-3.5" />}
                Create
              </Button>
            </div>

            {/* Newly created key (shown once) */}
            {newKeyValue && (
              <div className="rounded-xl border border-green-500/30 bg-green-500/5 p-3 animate-scale-in">
                <p className="text-xs text-green-400 font-medium mb-1.5">New API key created - copy it now, it won&apos;t be shown again</p>
                <div className="flex items-center gap-2">
                  <code className="flex-1 rounded-lg bg-black/20 px-3 py-1.5 text-xs font-mono text-green-300 truncate">
                    {newKeyValue}
                  </code>
                  <button
                    onClick={() => handleCopyKey(newKeyValue)}
                    className="shrink-0 rounded-lg p-1.5 text-green-400 hover:bg-green-500/10 transition-colors"
                    aria-label="Copy API key"
                  >
                    <Copy className="h-3.5 w-3.5" />
                  </button>
                  <button
                    onClick={() => setNewKeyValue(null)}
                    className="shrink-0 rounded-lg p-1.5 text-muted-foreground hover:bg-muted transition-colors"
                    aria-label="Dismiss"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            )}

            {/* Existing keys list */}
            {apiKeysLoading ? (
              <div className="space-y-2">
                {[1, 2].map((i) => (
                  <div key={i} className="h-12 rounded-xl bg-muted/30 animate-pulse" />
                ))}
              </div>
            ) : apiKeys.length === 0 ? (
              <div className="rounded-xl border border-dashed border-border/50 bg-muted/20 p-6 text-center">
                <p className="text-xs text-muted-foreground/60">No API keys created yet</p>
                <p className="text-[10px] text-muted-foreground/40 mt-1">Create one above to use the API programmatically</p>
              </div>
            ) : (
              <div className="space-y-2">
                {apiKeys.map((k) => (
                  <div key={k.id} className="flex items-center gap-3 rounded-xl border border-border/50 bg-muted/20 px-3 py-2.5">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium truncate">{k.label}</span>
                        <code className="text-[10px] font-mono text-muted-foreground/50">{k.prefix}...</code>
                      </div>
                      <p className="text-[10px] text-muted-foreground/40">
                        Created {new Date(k.created_at).toLocaleDateString()}
                        {k.last_used && ` · Last used ${new Date(k.last_used).toLocaleDateString()}`}
                      </p>
                    </div>
                    <button
                      onClick={() => handleRevokeApiKey(k.id)}
                      className="shrink-0 rounded-lg p-1.5 text-muted-foreground/50 hover:text-red-400 hover:bg-red-400/10 transition-colors"
                      aria-label={`Revoke key ${k.label}`}
                      title="Revoke"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Change Password */}
        <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Lock className="h-4 w-4 text-primary" />
              Change Password
            </CardTitle>
            <CardDescription>Update your account password</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-1.5">
              <Label htmlFor="old_password">Current Password</Label>
              <div className="relative">
                <Input
                  id="old_password"
                  type={showOldPassword ? "text" : "password"}
                  value={oldPassword}
                  onChange={(e) => setOldPassword(e.target.value)}
                  placeholder="Enter current password"
                  autoComplete="current-password"
                  className="pr-10 bg-secondary/50 border-border/50"
                />
                <button
                  type="button"
                  onClick={() => setShowOldPassword(!showOldPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                >
                  {showOldPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="new_password">New Password</Label>
              <div className="relative">
                <Input
                  id="new_password"
                  type={showNewPassword ? "text" : "password"}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="At least 8 characters"
                  autoComplete="new-password"
                  className="pr-10 bg-secondary/50 border-border/50"
                />
                <button
                  type="button"
                  onClick={() => setShowNewPassword(!showNewPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                >
                  {showNewPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="confirm_password">Confirm New Password</Label>
              <Input
                id="confirm_password"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Re-enter new password"
                autoComplete="new-password"
                className={`bg-secondary/50 ${confirmPassword && confirmPassword !== newPassword ? "border-red-500/50" : "border-border/50"}`}
              />
              {confirmPassword && confirmPassword !== newPassword && (
                <p className="text-[10px] text-red-400 flex items-center gap-1 animate-fade-in">
                  <AlertCircle className="h-3 w-3" />
                  Passwords do not match
                </p>
              )}
            </div>
            <Button
              onClick={handleChangePassword}
              disabled={changingPassword || !oldPassword || !newPassword || newPassword !== confirmPassword}
              variant="outline"
              className="w-full h-10 rounded-xl gap-2 mt-1"
            >
              {changingPassword ? <Loader2 className="h-4 w-4 animate-spin" /> : <Lock className="h-4 w-4" />}
              {changingPassword ? "Changing..." : "Change Password"}
            </Button>
          </CardContent>
        </Card>

        {/* Tools Configuration */}
        <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Wrench className="h-4 w-4 text-primary" />
              Tools
            </CardTitle>
            <CardDescription>
              All tools are enabled by default. Installed tool groups:
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {toolGroups.length > 0 ? toolGroups.map((group) => (
                <div
                  key={group.name}
                  className="flex items-center gap-2 rounded-xl border border-border/50 bg-muted/30 p-2.5"
                >
                  <div className={`text-xs font-medium ${group.color}`}>
                    {group.name}
                  </div>
                  <span className="ml-auto rounded-full bg-muted px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground">
                    {group.count}
                  </span>
                </div>
              )) : (
                <div className="col-span-full text-xs text-muted-foreground/50">Loading tools...</div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Data & Export */}
        <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Download className="h-4 w-4 text-primary" />
              Data Management
            </CardTitle>
            <CardDescription>Import, export, and manage your data</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Button
              variant="outline"
              className="w-full justify-start gap-2 h-11 rounded-xl border-border/50"
              onClick={handleExportLearnings}
              aria-label="Export all learnings as JSON file"
            >
              <Download className="h-4 w-4 text-primary" />
              Export Learnings ({learnings.length} entries)
            </Button>
            <Button
              variant="outline"
              className="w-full justify-start gap-2 h-11 rounded-xl border-border/50"
              onClick={handleExportSettings}
              aria-label="Export current settings as JSON file"
            >
              <Download className="h-4 w-4 text-primary" />
              Export Current Settings
            </Button>
            <Button
              variant="outline"
              className="w-full justify-start gap-2 h-11 rounded-xl border-border/50"
              onClick={() => importFileRef.current?.click()}
              aria-label="Import settings from JSON file"
            >
              <Upload className="h-4 w-4 text-primary" />
              Import Settings from File
            </Button>
            <input
              ref={importFileRef}
              type="file"
              accept=".json"
              onChange={handleImportSettings}
              className="hidden"
            />
            <Separator className="bg-border/30" />
            <Button
              variant="outline"
              className="w-full justify-start gap-2 h-11 rounded-xl border-border/50"
              onClick={handleResetOnboarding}
            >
              <RotateCcw className="h-4 w-4 text-primary" />
              Replay Welcome Tour
            </Button>
          </CardContent>
        </Card>

        {/* Danger Zone */}
        <Card className="border-red-500/20 bg-red-500/[0.02] backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base text-red-400">
              <AlertTriangle className="h-4 w-4" />
              Danger Zone
            </CardTitle>
            <CardDescription>Irreversible actions. Be careful.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Button
              variant="outline"
              className={`w-full justify-start gap-2 h-11 rounded-xl transition-all duration-200 ${
                confirmClear
                  ? "border-red-500/50 bg-red-500/10 text-red-400 hover:bg-red-500/20 animate-pulse"
                  : "border-red-500/20 text-muted-foreground hover:text-red-400 hover:border-red-500/30"
              }`}
              onClick={handleClearAllSessions}
              disabled={clearingAllSessions}
            >
              {clearingAllSessions ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Trash2 className="h-4 w-4" />
              )}
              {confirmClear
                ? "Click again to confirm - this cannot be undone"
                : "Delete All Chat Sessions"}
            </Button>
          </CardContent>
        </Card>

        {/* Save Button */}
        <div className={`sticky bottom-0 backdrop-blur-xl py-4 -mx-4 sm:-mx-6 px-4 sm:px-6 border-t transition-colors duration-200 ${
          hasChanges
            ? "bg-primary/5 border-primary/20"
            : "bg-background/80 border-border/50"
        }`}>
          {hasChanges && (
            <p className="text-[10px] text-primary/70 text-center mb-2 animate-fade-in">
              You have unsaved changes
            </p>
          )}
          <Button
            onClick={handleSave}
            disabled={!hasChanges || saving || maxTokens < 256 || maxTokens > 32768}
            className="w-full h-11 rounded-xl gap-2"
          >
            {saving ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="h-4 w-4" />
                Save Settings
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
