"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

interface APIKeyInfo {
  key_id: string;
  name: string;
  prefix: string;
  created_at: string;
  usage_count: number;
}

export default function KeysPage() {
  const router = useRouter();
  const [keys, setKeys] = useState<APIKeyInfo[]>([]);
  const [newKeyName, setNewKeyName] = useState("");
  const [newRawKey, setNewRawKey] = useState("");
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!api.isLoggedIn()) {
      router.push("/");
      return;
    }
    loadKeys();
  }, []);

  async function loadKeys() {
    try {
      const data = await api.getApiKeys();
      setKeys(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load keys");
    }
  }

  async function handleCreate() {
    if (!newKeyName.trim()) return;
    setError("");
    setNewRawKey("");
    try {
      const result = await api.createApiKey(newKeyName.trim());
      setNewRawKey(result.key);
      setNewKeyName("");
      loadKeys();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create key");
    }
  }

  async function handleRevoke(keyId: string) {
    if (!confirm("Revoke this API key? This cannot be undone.")) return;
    try {
      await api.revokeApiKey(keyId);
      loadKeys();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to revoke key");
    }
  }

  function copyKey() {
    navigator.clipboard.writeText(newRawKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-white">
      <div className="max-w-3xl mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-3xl font-bold">API Keys</h1>
          <button
            onClick={() => router.push("/chat")}
            className="px-4 py-2 bg-zinc-800 rounded-lg hover:bg-zinc-700 text-sm"
          >
            Back to Chat
          </button>
        </div>

        <p className="text-zinc-400 mb-6">
          API keys let you access Jarvis programmatically. Use them in the
          Authorization header as <code className="bg-zinc-800 px-1 rounded">Bearer jrv_...</code>
        </p>

        {error && (
          <div className="bg-red-900/30 border border-red-800 text-red-300 px-4 py-2 rounded-lg mb-4">
            {error}
          </div>
        )}

        {/* New key creation */}
        {newRawKey && (
          <div className="bg-green-900/20 border border-green-800 rounded-xl p-4 mb-6">
            <p className="text-green-300 font-medium mb-2">
              Key created! Save it now — you won't see it again.
            </p>
            <div className="flex items-center gap-2">
              <code className="flex-1 bg-zinc-900 px-3 py-2 rounded font-mono text-sm break-all">
                {newRawKey}
              </code>
              <button
                onClick={copyKey}
                className="px-3 py-2 bg-green-700 rounded hover:bg-green-600 text-sm whitespace-nowrap"
              >
                {copied ? "Copied!" : "Copy"}
              </button>
            </div>
          </div>
        )}

        {/* Create form */}
        <div className="bg-zinc-900 rounded-xl p-4 mb-6">
          <h2 className="text-lg font-semibold mb-3">Create New Key</h2>
          <div className="flex gap-2">
            <input
              type="text"
              value={newKeyName}
              onChange={(e) => setNewKeyName(e.target.value)}
              placeholder="Key name (e.g., 'Production API')"
              className="flex-1 bg-zinc-800 text-white px-3 py-2 rounded-lg border border-zinc-700 focus:border-blue-500 focus:outline-none"
              onKeyDown={(e) => e.key === "Enter" && handleCreate()}
            />
            <button
              onClick={handleCreate}
              disabled={!newKeyName.trim()}
              className="px-4 py-2 bg-blue-600 rounded-lg hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Create
            </button>
          </div>
        </div>

        {/* Key list */}
        <div className="bg-zinc-900 rounded-xl overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-zinc-800">
                <th className="text-left px-4 py-3 text-sm text-zinc-400">Name</th>
                <th className="text-left px-4 py-3 text-sm text-zinc-400">Prefix</th>
                <th className="text-left px-4 py-3 text-sm text-zinc-400">Created</th>
                <th className="text-left px-4 py-3 text-sm text-zinc-400">Uses</th>
                <th className="text-right px-4 py-3 text-sm text-zinc-400">Actions</th>
              </tr>
            </thead>
            <tbody>
              {keys.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-zinc-500">
                    No API keys yet
                  </td>
                </tr>
              ) : (
                keys.map((k) => (
                  <tr key={k.key_id} className="border-b border-zinc-800/50 hover:bg-zinc-800/30">
                    <td className="px-4 py-3 font-medium">{k.name}</td>
                    <td className="px-4 py-3 font-mono text-sm text-zinc-400">{k.prefix}...</td>
                    <td className="px-4 py-3 text-zinc-400 text-sm">
                      {new Date(k.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3 text-zinc-400">{k.usage_count}</td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => handleRevoke(k.key_id)}
                        className="px-3 py-1 bg-red-900/50 text-red-300 rounded text-xs hover:bg-red-900"
                      >
                        Revoke
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
