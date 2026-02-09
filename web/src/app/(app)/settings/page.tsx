"use client";

import { useState, useEffect } from "react";
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
} from "lucide-react";
import { useSettings } from "@/hooks/use-settings";
import { useToast } from "@/components/ui/toast";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

export default function SettingsPage() {
  const { settings, modelsData, loading, saving, updateSettings } = useSettings();
  const toast = useToast();

  const [backend, setBackend] = useState("");
  const [model, setModel] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [maxTokens, setMaxTokens] = useState(4096);
  const [showApiKey, setShowApiKey] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);

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

  const handleBackendChange = (newBackend: string) => {
    setBackend(newBackend);
    // Auto-select first model for the new backend
    const models = modelsData?.models[newBackend];
    if (models && models.length > 0) {
      setModel(models[0].id);
    }
  };

  const handleSave = async () => {
    try {
      const update: Record<string, unknown> = {};
      if (backend !== settings?.backend) update.backend = backend;
      if (model !== settings?.model) update.model = model;
      if (maxTokens !== settings?.max_tokens) update.max_tokens = maxTokens;
      if (apiKey) update.api_key = apiKey;

      await updateSettings(update);
      setApiKey(""); // Clear after save
      setHasChanges(false);
      toast.success("Settings saved", "Your preferences have been updated.");
    } catch {
      toast.error("Failed to save", "Please check your settings and try again.");
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

  const currentModels = modelsData?.models[backend] || [];

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-2xl space-y-6 p-4 sm:p-6 pb-20 animate-fade-in-up">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Configure your AI backend, model, and tools.
          </p>
        </div>

        {/* AI Backend */}
        <Card className="border-white/5 bg-card/50 backdrop-blur-sm">
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
                      : "border-white/5 bg-white/[0.02] hover:border-white/10 hover:bg-white/[0.04]"
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
        <Card className="border-white/5 bg-card/50 backdrop-blur-sm">
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
                      : "border-white/5 bg-white/[0.02] hover:border-white/10"
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

            <Separator className="bg-white/5" />

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
                  className="w-32 bg-secondary/50 border-white/10"
                />
                <span className="text-xs text-muted-foreground">
                  (256 - 32,768)
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* API Key */}
        <Card className="border-white/5 bg-card/50 backdrop-blur-sm">
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
                  className="pr-10 bg-secondary/50 border-white/10"
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
        <Card className="border-white/5 bg-card/50 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Wrench className="h-4 w-4 text-primary" />
              Tools
            </CardTitle>
            <CardDescription>
              All 16+ tools are enabled by default. Tool management coming soon.
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
                  className="flex items-center gap-2 rounded-xl border border-white/5 bg-white/[0.02] p-2.5"
                >
                  <div className={`text-xs font-medium ${group.color}`}>
                    {group.name}
                  </div>
                  <span className="ml-auto rounded-full bg-white/5 px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground">
                    {group.count}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Save Button */}
        <div className="sticky bottom-0 bg-background/80 backdrop-blur-xl py-4 -mx-4 sm:-mx-6 px-4 sm:px-6 border-t border-white/5">
          <Button
            onClick={handleSave}
            disabled={!hasChanges || saving}
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
