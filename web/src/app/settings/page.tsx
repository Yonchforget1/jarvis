"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

const MODEL_SUGGESTIONS: Record<string, string[]> = {
  claude_code: [""],
  anthropic: ["claude-sonnet-4-5-20250929", "claude-haiku-4-5-20251001", "claude-opus-4-6"],
  openai: ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "o1", "o1-mini"],
  gemini: ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
};

export default function SettingsPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  const [backend, setBackend] = useState("claude_code");
  const [model, setModel] = useState("");
  const [maxTokens, setMaxTokens] = useState(4096);
  const [systemPrompt, setSystemPrompt] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [backends, setBackends] = useState<string[]>([]);

  useEffect(() => {
    if (!api.isLoggedIn()) {
      router.push("/");
      return;
    }
    loadSettings();
  }, [router]);

  async function loadSettings() {
    try {
      const data = await api.getSettings();
      setBackend(data.backend);
      setModel(data.model);
      setMaxTokens(data.max_tokens);
      setSystemPrompt(data.system_prompt);
      setBackends(data.available_backends);
    } catch (err) {
      setMessage("Failed to load settings");
    } finally {
      setLoading(false);
    }
  }

  async function handleSave() {
    setSaving(true);
    setMessage("");
    try {
      const updates: Record<string, unknown> = {};
      updates.backend = backend;
      updates.model = model;
      updates.max_tokens = maxTokens;
      updates.system_prompt = systemPrompt;
      if (apiKey) updates.api_key = apiKey;

      const res = await api.updateSettings(updates as Parameters<typeof api.updateSettings>[0]);
      setMessage(`Settings saved: ${res.changed.join(", ")}`);
      setApiKey(""); // Clear API key field after save
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to save";
      setMessage(`Error: ${msg}`);
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-zinc-950 text-zinc-400">
        Loading settings...
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <header className="flex items-center justify-between px-6 py-4 bg-zinc-900 border-b border-zinc-800">
        <h1 className="text-lg font-semibold">Settings</h1>
        <button
          onClick={() => router.push("/chat")}
          className="text-sm text-zinc-400 hover:text-white border border-zinc-700 rounded px-3 py-1"
        >
          Back to Chat
        </button>
      </header>

      <div className="max-w-2xl mx-auto p-6 space-y-6">
        {/* Backend */}
        <div>
          <label className="block text-sm font-medium text-zinc-400 mb-1">AI Backend</label>
          <select
            value={backend}
            onChange={(e) => {
              setBackend(e.target.value);
              const suggestions = MODEL_SUGGESTIONS[e.target.value] || [""];
              setModel(suggestions[0]);
            }}
            className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
          >
            {backends.map((b) => (
              <option key={b} value={b}>
                {b === "claude_code" ? "Claude Code CLI (Free via Max)" :
                 b === "anthropic" ? "Anthropic (Claude API)" :
                 b === "openai" ? "OpenAI (GPT-4o)" :
                 b === "gemini" ? "Google Gemini" : b}
              </option>
            ))}
          </select>
          <p className="mt-1 text-xs text-zinc-500">
            {backend === "claude_code"
              ? "Routes through your Claude Max subscription. No API key needed."
              : `Requires ${backend === "anthropic" ? "ANTHROPIC_API_KEY" : backend === "openai" ? "OPENAI_API_KEY" : "GOOGLE_API_KEY"}.`}
          </p>
        </div>

        {/* Model */}
        <div>
          <label className="block text-sm font-medium text-zinc-400 mb-1">Model</label>
          <input
            type="text"
            value={model}
            onChange={(e) => setModel(e.target.value)}
            placeholder={backend === "claude_code" ? "Automatic" : "Enter model name"}
            className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
          />
          {MODEL_SUGGESTIONS[backend] && MODEL_SUGGESTIONS[backend].length > 0 && (
            <div className="mt-1 flex gap-1 flex-wrap">
              {MODEL_SUGGESTIONS[backend].filter(Boolean).map((m) => (
                <button
                  key={m}
                  onClick={() => setModel(m)}
                  className={`text-xs px-2 py-0.5 rounded border ${
                    model === m
                      ? "border-blue-500 text-blue-400"
                      : "border-zinc-700 text-zinc-500 hover:text-zinc-300"
                  }`}
                >
                  {m}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* API Key */}
        {backend !== "claude_code" && (
          <div>
            <label className="block text-sm font-medium text-zinc-400 mb-1">API Key</label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="Enter API key (leave blank to keep current)"
              className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
            />
            <p className="mt-1 text-xs text-zinc-500">
              Stored in server memory only, not written to config file.
            </p>
          </div>
        )}

        {/* Max Tokens */}
        <div>
          <label className="block text-sm font-medium text-zinc-400 mb-1">
            Max Tokens: {maxTokens.toLocaleString()}
          </label>
          <input
            type="range"
            min={256}
            max={32768}
            step={256}
            value={maxTokens}
            onChange={(e) => setMaxTokens(Number(e.target.value))}
            className="w-full"
          />
        </div>

        {/* System Prompt */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="text-sm font-medium text-zinc-400">System Prompt</label>
            <div className="flex items-center gap-2">
              <span className="text-xs text-zinc-500">{systemPrompt.length.toLocaleString()} chars</span>
              <button
                onClick={() => setSystemPrompt("You are Jarvis, an advanced AI agent.")}
                className="text-xs text-zinc-500 hover:text-orange-400 transition-colors"
              >
                Reset to default
              </button>
            </div>
          </div>
          <textarea
            value={systemPrompt}
            onChange={(e) => setSystemPrompt(e.target.value)}
            rows={6}
            className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500 resize-y font-mono"
            placeholder="Define Jarvis's personality and capabilities..."
          />
          <p className="mt-1 text-xs text-zinc-500">
            Controls how Jarvis responds. Memory context is automatically appended to this prompt.
          </p>
        </div>

        {/* Save */}
        <div className="flex items-center gap-4">
          <button
            onClick={handleSave}
            disabled={saving}
            className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg text-sm font-medium disabled:opacity-50"
          >
            {saving ? "Saving..." : "Save Settings"}
          </button>
          {message && (
            <span className={`text-sm ${message.startsWith("Error") ? "text-red-400" : "text-green-400"}`}>
              {message}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
