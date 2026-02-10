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
  ChevronDown,
  ChevronUp,
  ToggleLeft,
  ToggleRight,
  FileArchive,
  Webhook,
  Zap,
  Keyboard,
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
  const { theme, setTheme, systemTheme } = useTheme();

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
  const [confirmDeleteAccount, setConfirmDeleteAccount] = useState(false);
  const [deletingAccount, setDeletingAccount] = useState(false);
  const confirmDeleteAccountTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Password change
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [changingPassword, setChangingPassword] = useState(false);
  const [showOldPassword, setShowOldPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);

  const handleChangePassword = async () => {
    if (changingPassword) return;
    if (!oldPassword.trim()) {
      toast.error("Required", "Please enter your current password.");
      return;
    }
    if (newPassword.length < 8) {
      toast.error("Too short", "New password must be at least 8 characters.");
      return;
    }
    if (/^\d+$/.test(newPassword) || /^[a-zA-Z]+$/.test(newPassword)) {
      toast.error("Too simple", "Password must contain both letters and numbers.");
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

  // Ctrl+Enter to send preference
  const [ctrlEnterSend, setCtrlEnterSend] = useState(() => {
    if (typeof window === "undefined") return false;
    try { return localStorage.getItem("jarvis_ctrl_enter_send") === "true"; } catch { return false; }
  });

  const handleToggleCtrlEnter = (enabled: boolean) => {
    setCtrlEnterSend(enabled);
    try {
      localStorage.setItem("jarvis_ctrl_enter_send", enabled ? "true" : "false");
    } catch { /* ignore */ }
    // Notify chat-input in the same tab (storage event only fires cross-tab)
    window.dispatchEvent(new Event("ctrl-enter-pref-changed"));
  };

  // Tool groups and individual tools (fetched dynamically)
  const [toolGroups, setToolGroups] = useState<{ name: string; count: number; color: string }[]>([]);
  const [allTools, setAllTools] = useState<{ name: string; description: string; category: string }[]>([]);
  const [disabledTools, setDisabledTools] = useState<Set<string>>(new Set());
  const [savingTools, setSavingTools] = useState(false);
  const [toolsExpanded, setToolsExpanded] = useState(false);

  // API Key management
  const [apiKeys, setApiKeys] = useState<{ id: string; label: string; prefix: string; created_at: string; last_used: string | null }[]>([]);
  const [apiKeysLoading, setApiKeysLoading] = useState(false);
  const [newKeyLabel, setNewKeyLabel] = useState("");
  const [newKeyValue, setNewKeyValue] = useState<string | null>(null);
  const [creatingKey, setCreatingKey] = useState(false);
  const [confirmRevokeKeyId, setConfirmRevokeKeyId] = useState<string | null>(null);
  const confirmRevokeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

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
    api.get<{ tools: { name: string; description: string; category: string }[] }>("/api/tools")
      .then((res) => {
        setAllTools(res.tools || []);
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

  // Sync disabled_tools from settings
  useEffect(() => {
    if (settings?.disabled_tools) {
      setDisabledTools(new Set(settings.disabled_tools));
    }
  }, [settings?.disabled_tools]);

  const handleToggleTool = async (toolName: string) => {
    const next = new Set(disabledTools);
    if (next.has(toolName)) {
      next.delete(toolName);
    } else {
      next.add(toolName);
    }
    setDisabledTools(next);
    setSavingTools(true);
    try {
      await updateSettings({ disabled_tools: [...next] });
    } catch {
      // Revert on error
      setDisabledTools(disabledTools);
      toast.error("Failed", "Could not update tool configuration.");
    } finally {
      setSavingTools(false);
    }
  };

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

  const handleRevokeApiKey = (keyId: string) => {
    if (confirmRevokeKeyId === keyId) {
      // Second click - actually revoke
      if (confirmRevokeTimerRef.current) clearTimeout(confirmRevokeTimerRef.current);
      setConfirmRevokeKeyId(null);
      api.delete(`/api/auth/api-keys/${keyId}`)
        .then(() => {
          setApiKeys((prev) => prev.filter((k) => k.id !== keyId));
          toast.success("Revoked", "API key has been revoked.");
        })
        .catch(() => {
          toast.error("Failed", "Could not revoke API key.");
        });
    } else {
      // First click - enter confirm state
      setConfirmRevokeKeyId(keyId);
      if (confirmRevokeTimerRef.current) clearTimeout(confirmRevokeTimerRef.current);
      confirmRevokeTimerRef.current = setTimeout(() => setConfirmRevokeKeyId(null), 5000);
    }
  };

  const handleCopyKey = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success("Copied", "API key copied to clipboard.");
  };

  // Webhook management
  interface WebhookEntry { id: string; url: string; events: string[]; has_secret: boolean; created_at: string }
  const [webhooks, setWebhooks] = useState<WebhookEntry[]>([]);
  const [webhooksLoading, setWebhooksLoading] = useState(false);
  const [newWebhookUrl, setNewWebhookUrl] = useState("");
  const [newWebhookEvents, setNewWebhookEvents] = useState<Set<string>>(new Set(["*"]));
  const [newWebhookSecret, setNewWebhookSecret] = useState("");
  const [creatingWebhook, setCreatingWebhook] = useState(false);
  const [confirmDeleteWebhookId, setConfirmDeleteWebhookId] = useState<string | null>(null);
  const confirmDeleteWebhookTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [testingWebhookId, setTestingWebhookId] = useState<string | null>(null);

  const WEBHOOK_EVENTS = [
    { value: "*", label: "All Events" },
    { value: "chat.complete", label: "Chat Complete" },
    { value: "tool.complete", label: "Tool Complete" },
    { value: "tool.error", label: "Tool Error" },
    { value: "session.created", label: "Session Created" },
  ];

  const fetchWebhooks = useCallback(async () => {
    setWebhooksLoading(true);
    try {
      const res = await api.get<{ webhooks: WebhookEntry[] }>("/api/webhooks");
      setWebhooks(res.webhooks || []);
    } catch { /* ignore */ }
    finally { setWebhooksLoading(false); }
  }, []);

  useEffect(() => { fetchWebhooks(); }, [fetchWebhooks]);

  const handleCreateWebhook = async () => {
    if (creatingWebhook || !newWebhookUrl.trim()) return;
    setCreatingWebhook(true);
    try {
      await api.post("/api/webhooks", { url: newWebhookUrl, events: [...newWebhookEvents], secret: newWebhookSecret });
      setNewWebhookUrl("");
      setNewWebhookSecret("");
      setNewWebhookEvents(new Set(["*"]));
      fetchWebhooks();
      toast.success("Webhook created", "Webhook registered successfully.");
    } catch (err) {
      toast.error("Failed", err instanceof Error ? err.message : "Could not create webhook.");
    } finally { setCreatingWebhook(false); }
  };

  const handleDeleteWebhook = (id: string) => {
    if (confirmDeleteWebhookId === id) {
      // Second click - actually delete
      if (confirmDeleteWebhookTimerRef.current) clearTimeout(confirmDeleteWebhookTimerRef.current);
      setConfirmDeleteWebhookId(null);
      api.delete(`/api/webhooks/${id}`)
        .then(() => {
          setWebhooks((prev) => prev.filter((w) => w.id !== id));
          toast.success("Deleted", "Webhook removed.");
        })
        .catch(() => {
          toast.error("Failed", "Could not delete webhook.");
        });
    } else {
      // First click - enter confirm state
      setConfirmDeleteWebhookId(id);
      if (confirmDeleteWebhookTimerRef.current) clearTimeout(confirmDeleteWebhookTimerRef.current);
      confirmDeleteWebhookTimerRef.current = setTimeout(() => setConfirmDeleteWebhookId(null), 5000);
    }
  };

  const handleTestWebhook = async (id: string) => {
    setTestingWebhookId(id);
    try {
      const res = await api.post<{ status: string; http_status?: number; error?: string }>(`/api/webhooks/${id}/test`, {});
      if (res.status === "delivered") {
        toast.success("Test sent", `Webhook responded with HTTP ${res.http_status}.`);
      } else {
        toast.error("Test failed", res.error || "Could not reach webhook.");
      }
    } catch {
      toast.error("Test failed", "Could not send test event.");
    } finally {
      setTestingWebhookId(null);
    }
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

  // Cleanup confirm timers on unmount
  useEffect(() => {
    return () => {
      if (confirmTimerRef.current) clearTimeout(confirmTimerRef.current);
      if (confirmRevokeTimerRef.current) clearTimeout(confirmRevokeTimerRef.current);
      if (confirmDeleteWebhookTimerRef.current) clearTimeout(confirmDeleteWebhookTimerRef.current);
      if (confirmDeleteAccountTimerRef.current) clearTimeout(confirmDeleteAccountTimerRef.current);
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

  const [exportingData, setExportingData] = useState(false);

  const handleExportAllData = async () => {
    if (exportingData) return;
    setExportingData(true);
    try {
      const token = localStorage.getItem("jarvis_token");
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${apiUrl}/api/compliance/export`, {
        method: "GET",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(`Export failed (${res.status})`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `jarvis-data-export-${new Date().toISOString().split("T")[0]}.zip`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success("Data exported", "All your data has been downloaded as a ZIP file.");
    } catch (err) {
      toast.error("Export failed", err instanceof Error ? err.message : "Could not export data.");
    } finally {
      setExportingData(false);
    }
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

  const handleDeleteAccount = async () => {
    if (!confirmDeleteAccount) {
      setConfirmDeleteAccount(true);
      if (confirmDeleteAccountTimerRef.current) clearTimeout(confirmDeleteAccountTimerRef.current);
      confirmDeleteAccountTimerRef.current = setTimeout(() => setConfirmDeleteAccount(false), 5000);
      return;
    }
    setDeletingAccount(true);
    try {
      await api.delete("/api/compliance/delete-account");
      localStorage.removeItem("jarvis_token");
      localStorage.removeItem("jarvis_user");
      window.location.href = "/login";
    } catch {
      toast.error("Failed", "Could not delete account. Please try again.");
      setConfirmDeleteAccount(false);
    } finally {
      setDeletingAccount(false);
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
                  {opt.id === "system" && theme === "system" && systemTheme && (
                    <span className="text-[10px] text-muted-foreground/50">
                      Currently {systemTheme}
                    </span>
                  )}
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

        {/* Chat Input */}
        <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Keyboard className="h-4 w-4 text-primary" />
              Chat Input
            </CardTitle>
            <CardDescription>Customize how the message input behaves</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <button
              onClick={() => handleToggleCtrlEnter(!ctrlEnterSend)}
              className={`flex w-full items-center justify-between rounded-xl border p-3 transition-all duration-200 ${
                ctrlEnterSend
                  ? "border-primary/50 bg-primary/5"
                  : "border-border/50 bg-muted/30 hover:border-border"
              }`}
            >
              <div className="text-left">
                <p className={`text-sm font-medium ${ctrlEnterSend ? "text-primary" : ""}`}>
                  Ctrl+Enter to Send
                </p>
                <p className="text-xs text-muted-foreground">
                  {ctrlEnterSend
                    ? "Press Ctrl+Enter to send, Enter for new line"
                    : "Press Enter to send, Shift+Enter for new line"}
                </p>
              </div>
              <div className={`relative h-6 w-11 rounded-full transition-colors ${ctrlEnterSend ? "bg-primary" : "bg-muted"}`}>
                <div className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow-sm transition-transform ${ctrlEnterSend ? "translate-x-5" : "translate-x-0.5"}`} />
              </div>
            </button>
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
              <p className="text-[10px] text-muted-foreground/50">Leave empty to use the server&apos;s default key</p>
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
                      className={`shrink-0 rounded-lg px-2 py-1.5 text-xs transition-colors ${
                        confirmRevokeKeyId === k.id
                          ? "bg-red-500/20 text-red-400 border border-red-500/30 font-medium"
                          : "text-muted-foreground/50 hover:text-red-400 hover:bg-red-400/10"
                      }`}
                      aria-label={confirmRevokeKeyId === k.id ? `Confirm revoke key ${k.label}` : `Revoke key ${k.label}`}
                      title={confirmRevokeKeyId === k.id ? "Click again to confirm" : "Revoke"}
                    >
                      {confirmRevokeKeyId === k.id ? "Confirm?" : <Trash2 className="h-3.5 w-3.5" />}
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
              {disabledTools.size > 0 && (
                <span className="ml-auto text-[10px] font-normal text-yellow-400 bg-yellow-400/10 rounded-full px-2 py-0.5">
                  {disabledTools.size} disabled
                </span>
              )}
            </CardTitle>
            <CardDescription>
              Toggle individual tools on or off. Disabled tools will not be available in chat.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {/* Tool group summary */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {toolGroups.length > 0 ? toolGroups.map((group) => {
                const groupTools = allTools.filter((t) => (t.category || "other").charAt(0).toUpperCase() + (t.category || "other").slice(1) === group.name);
                const disabledInGroup = groupTools.filter((t) => disabledTools.has(t.name)).length;
                return (
                  <div
                    key={group.name}
                    className="flex items-center gap-2 rounded-xl border border-border/50 bg-muted/30 p-2.5"
                  >
                    <div className={`text-xs font-medium ${group.color}`}>
                      {group.name}
                    </div>
                    <span className="ml-auto rounded-full bg-muted px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground">
                      {disabledInGroup > 0 ? `${group.count - disabledInGroup}/${group.count}` : group.count}
                    </span>
                  </div>
                );
              }) : (
                <div className="col-span-full text-xs text-muted-foreground/50">Loading tools...</div>
              )}
            </div>

            {/* Expand/collapse individual tools */}
            {allTools.length > 0 && (
              <>
                <button
                  onClick={() => setToolsExpanded(!toolsExpanded)}
                  className="flex items-center gap-1.5 text-xs text-primary/70 hover:text-primary transition-colors"
                >
                  {toolsExpanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                  {toolsExpanded ? "Hide individual tools" : `Configure individual tools (${allTools.length})`}
                </button>

                {toolsExpanded && (
                  <div className="space-y-1 max-h-[400px] overflow-y-auto rounded-xl border border-border/30 p-2">
                    {Object.entries(
                      allTools.reduce<Record<string, typeof allTools>>((acc, tool) => {
                        const cat = (tool.category || "other").charAt(0).toUpperCase() + (tool.category || "other").slice(1);
                        if (!acc[cat]) acc[cat] = [];
                        acc[cat].push(tool);
                        return acc;
                      }, {})
                    ).sort(([a], [b]) => a.localeCompare(b)).map(([category, tools]) => (
                      <div key={category}>
                        <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground/50 px-2 py-1.5">
                          {category}
                        </p>
                        {tools.sort((a, b) => a.name.localeCompare(b.name)).map((tool) => {
                          const isDisabled = disabledTools.has(tool.name);
                          return (
                            <button
                              key={tool.name}
                              onClick={() => handleToggleTool(tool.name)}
                              disabled={savingTools}
                              className={`flex items-center gap-3 w-full rounded-lg px-2 py-2 text-left transition-colors ${
                                isDisabled
                                  ? "opacity-50 hover:opacity-70"
                                  : "hover:bg-muted/50"
                              }`}
                            >
                              {isDisabled ? (
                                <ToggleLeft className="h-4 w-4 text-muted-foreground/40 shrink-0" />
                              ) : (
                                <ToggleRight className="h-4 w-4 text-green-400 shrink-0" />
                              )}
                              <div className="flex-1 min-w-0">
                                <p className={`text-xs font-medium ${isDisabled ? "text-muted-foreground/50 line-through" : "text-foreground"}`}>
                                  {tool.name}
                                </p>
                                <p className="text-[10px] text-muted-foreground/40 truncate">
                                  {tool.description}
                                </p>
                              </div>
                            </button>
                          );
                        })}
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
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
              onClick={handleExportAllData}
              disabled={exportingData}
              aria-label="Download all your data as a ZIP file"
            >
              {exportingData ? <Loader2 className="h-4 w-4 animate-spin text-primary" /> : <FileArchive className="h-4 w-4 text-primary" />}
              {exportingData ? "Preparing export..." : "Download All My Data (GDPR)"}
            </Button>
            <p className="text-[10px] text-muted-foreground/40 px-1">
              Downloads a ZIP containing your profile, sessions, settings, and audit logs.
            </p>
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

        {/* Webhooks */}
        <Card className="border-border/50 bg-card/30 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Webhook className="h-4 w-4 text-cyan-400" />
              Webhooks
            </CardTitle>
            <CardDescription>Receive HTTP notifications when events occur</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Existing webhooks */}
            {webhooksLoading ? (
              <p className="text-xs text-muted-foreground/40">Loading webhooks...</p>
            ) : webhooks.length > 0 ? (
              <div className="space-y-2">
                {webhooks.map((wh) => (
                  <div key={wh.id} className="flex items-center justify-between rounded-xl border border-border/30 bg-muted/20 px-3 py-2.5">
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-mono truncate">{wh.url}</p>
                      <div className="flex items-center gap-2 mt-1">
                        {wh.events.map((ev) => (
                          <span key={ev} className="text-[9px] rounded-full bg-cyan-400/10 text-cyan-400 px-1.5 py-0.5">{ev}</span>
                        ))}
                        {wh.has_secret && <span className="text-[9px] rounded-full bg-green-400/10 text-green-400 px-1.5 py-0.5">HMAC</span>}
                      </div>
                    </div>
                    <div className="flex items-center gap-1 shrink-0 ml-2">
                      <button
                        onClick={() => handleTestWebhook(wh.id)}
                        disabled={testingWebhookId === wh.id}
                        className="px-2 py-1.5 rounded-lg text-xs transition-colors text-muted-foreground/40 hover:text-cyan-400 hover:bg-cyan-400/10 disabled:opacity-50"
                        aria-label="Send test event"
                        title="Send test event"
                      >
                        {testingWebhookId === wh.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Zap className="h-3.5 w-3.5" />}
                      </button>
                      <button
                        onClick={() => handleDeleteWebhook(wh.id)}
                        className={`px-2 py-1.5 rounded-lg text-xs transition-colors ${
                          confirmDeleteWebhookId === wh.id
                            ? "bg-red-500/20 text-red-400 border border-red-500/30 font-medium"
                            : "text-muted-foreground/40 hover:text-red-400 hover:bg-red-400/10"
                        }`}
                        aria-label={confirmDeleteWebhookId === wh.id ? "Confirm delete webhook" : "Delete webhook"}
                      >
                        {confirmDeleteWebhookId === wh.id ? "Confirm?" : <Trash2 className="h-3.5 w-3.5" />}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground/40">No webhooks configured</p>
            )}

            {/* Add webhook form */}
            <Separator className="bg-border/30" />
            <div className="space-y-3">
              <div className="space-y-1.5">
                <Label className="text-xs">Webhook URL</Label>
                <Input
                  value={newWebhookUrl}
                  onChange={(e) => setNewWebhookUrl(e.target.value)}
                  placeholder="https://example.com/webhook"
                  className="h-10 rounded-xl bg-secondary/50 border-border/50 text-xs font-mono"
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">Events</Label>
                <div className="flex flex-wrap gap-1.5">
                  {WEBHOOK_EVENTS.map((ev) => (
                    <button
                      key={ev.value}
                      onClick={() => {
                        const next = new Set(newWebhookEvents);
                        if (ev.value === "*") {
                          next.clear();
                          next.add("*");
                        } else {
                          next.delete("*");
                          if (next.has(ev.value)) next.delete(ev.value);
                          else next.add(ev.value);
                          if (next.size === 0) next.add("*");
                        }
                        setNewWebhookEvents(next);
                      }}
                      className={`rounded-full px-2.5 py-1 text-[10px] font-medium border transition-colors ${
                        newWebhookEvents.has(ev.value)
                          ? "bg-cyan-400/10 text-cyan-400 border-cyan-400/30"
                          : "bg-muted/50 text-muted-foreground/50 border-border/30 hover:border-border"
                      }`}
                    >
                      {ev.label}
                    </button>
                  ))}
                </div>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">Secret <span className="text-muted-foreground/40">(optional, for HMAC verification)</span></Label>
                <Input
                  value={newWebhookSecret}
                  onChange={(e) => setNewWebhookSecret(e.target.value)}
                  placeholder="Optional signing secret"
                  type="password"
                  className="h-10 rounded-xl bg-secondary/50 border-border/50 text-xs font-mono"
                />
              </div>
              <Button
                onClick={handleCreateWebhook}
                disabled={creatingWebhook || !newWebhookUrl.trim()}
                variant="outline"
                className="gap-2 rounded-xl h-10 text-xs"
              >
                {creatingWebhook ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Plus className="h-3.5 w-3.5" />}
                Add Webhook
              </Button>
            </div>
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
            <Separator className="opacity-30" />
            <Button
              variant="outline"
              className={`w-full justify-start gap-2 h-11 rounded-xl transition-all duration-200 ${
                confirmDeleteAccount
                  ? "border-red-500/50 bg-red-500/10 text-red-400 hover:bg-red-500/20 animate-pulse"
                  : "border-red-500/20 text-muted-foreground hover:text-red-400 hover:border-red-500/30"
              }`}
              onClick={handleDeleteAccount}
              disabled={deletingAccount}
            >
              {deletingAccount ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Trash2 className="h-4 w-4" />
              )}
              {confirmDeleteAccount
                ? "Click again to permanently delete everything"
                : "Delete My Account & All Data"}
            </Button>
            <p className="text-[10px] text-muted-foreground/40">
              Permanently removes all sessions, settings, API keys, and anonymizes your account (GDPR Article 17).
            </p>
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
