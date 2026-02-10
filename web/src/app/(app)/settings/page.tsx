"use client";

import { useState, useEffect, useRef } from "react";
import {
  Cpu,
  Key,
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
  const [clearingAllSessions, setClearingAllSessions] = useState(false);
  const [confirmClear, setConfirmClear] = useState(false);
  const confirmTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

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

  const handleSave = async () => {
    if (saving) return;
    try {
      const update: Record<string, unknown> = {};
      if (backend !== settings?.backend) update.backend = backend;
      if (model !== settings?.model) update.model = model;
      if (maxTokens !== settings?.max_tokens) update.max_tokens = maxTokens;
      if (apiKey) update.api_key = apiKey;

      await updateSettings(update);
      setApiKey("");
      setHasChanges(false);
      toast.success("Settings saved", "Your preferences have been updated.");
    } catch {
      toast.error("Failed to save", "Please check your settings and try again.");
    }
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
      const sessions = await api.get<{ session_id: string }[]>("/api/sessions");
      await Promise.all(sessions.map((s) => api.delete(`/api/sessions/${s.session_id}`)));
      setConfirmClear(false);
      toast.success("Sessions cleared", `${sessions.length} sessions deleted.`);
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
        <ErrorState message={settingsError} onRetry={refetch} />
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
                  className="pr-10 bg-secondary/50 border-border/50"
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
              <p className="text-[10px] text-muted-foreground/60">
                Your key is stored securely and used only for your sessions.
              </p>
            </div>
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
              {[
                { name: "Filesystem", count: 7, color: "text-blue-400" },
                { name: "Execution", count: 2, color: "text-green-400" },
                { name: "Web", count: 2, color: "text-orange-400" },
                { name: "Game Dev", count: 2, color: "text-purple-400" },
                { name: "Memory", count: 3, color: "text-yellow-400" },
                { name: "Computer", count: 12, color: "text-cyan-400" },
                { name: "Browser", count: 11, color: "text-pink-400" },
              ].map((group) => (
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
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Data & Export */}
        <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Download className="h-4 w-4 text-primary" />
              Data Export
            </CardTitle>
            <CardDescription>Download your data for backup or analysis</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Button
              variant="outline"
              className="w-full justify-start gap-2 h-11 rounded-xl border-border/50"
              onClick={handleExportLearnings}
            >
              <Download className="h-4 w-4 text-primary" />
              Export Learnings ({learnings.length} entries)
            </Button>
            <Button
              variant="outline"
              className="w-full justify-start gap-2 h-11 rounded-xl border-border/50"
              onClick={handleExportSettings}
            >
              <Upload className="h-4 w-4 text-primary" />
              Export Current Settings
            </Button>
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
