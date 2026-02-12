"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

interface UsageData {
  total_input_tokens: number;
  total_output_tokens: number;
  total_tokens: number;
  total_requests: number;
  estimated_cost_usd: number;
}

export default function UsagePage() {
  const router = useRouter();
  const [usage, setUsage] = useState<UsageData | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!api.isLoggedIn()) {
      router.push("/");
      return;
    }
    loadUsage();
  }, []);

  async function loadUsage() {
    try {
      const data = await api.getUsage();
      setUsage(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load usage data");
    }
  }

  function formatTokens(n: number): string {
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
    if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
    return n.toString();
  }

  function formatCost(usd: number): string {
    return `$${usd.toFixed(4)}`;
  }

  const inputPct = usage && usage.total_tokens > 0
    ? Math.round((usage.total_input_tokens / usage.total_tokens) * 100)
    : 0;
  const outputPct = 100 - inputPct;

  return (
    <div className="min-h-screen bg-zinc-950 text-white">
      <div className="max-w-3xl mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-3xl font-bold">Usage</h1>
          <button
            onClick={() => router.push("/chat")}
            className="px-4 py-2 bg-zinc-800 rounded-lg hover:bg-zinc-700 text-sm"
          >
            Back to Chat
          </button>
        </div>

        {error && (
          <div className="bg-red-900/30 border border-red-800 text-red-300 px-4 py-2 rounded-lg mb-4">
            {error}
          </div>
        )}

        {!usage && !error && (
          <div className="text-zinc-500 text-center py-12">Loading usage data...</div>
        )}

        {usage && (
          <>
            {/* Summary Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
              <div className="bg-zinc-900 rounded-xl p-4">
                <p className="text-sm text-zinc-400 mb-1">Total Tokens</p>
                <p className="text-2xl font-bold">{formatTokens(usage.total_tokens)}</p>
              </div>
              <div className="bg-zinc-900 rounded-xl p-4">
                <p className="text-sm text-zinc-400 mb-1">Requests</p>
                <p className="text-2xl font-bold">{usage.total_requests}</p>
              </div>
              <div className="bg-zinc-900 rounded-xl p-4">
                <p className="text-sm text-zinc-400 mb-1">Est. Cost</p>
                <p className="text-2xl font-bold text-yellow-400">
                  {formatCost(usage.estimated_cost_usd)}
                </p>
              </div>
              <div className="bg-zinc-900 rounded-xl p-4">
                <p className="text-sm text-zinc-400 mb-1">Avg Tokens/Req</p>
                <p className="text-2xl font-bold">
                  {usage.total_requests > 0
                    ? formatTokens(Math.round(usage.total_tokens / usage.total_requests))
                    : "0"}
                </p>
              </div>
            </div>

            {/* Token Breakdown */}
            <div className="bg-zinc-900 rounded-xl p-6 mb-8">
              <h2 className="text-lg font-semibold mb-4">Token Breakdown</h2>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-zinc-400">Input Tokens</span>
                    <span>{formatTokens(usage.total_input_tokens)} ({inputPct}%)</span>
                  </div>
                  <div className="h-3 bg-zinc-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-blue-500 rounded-full transition-all"
                      style={{ width: `${inputPct}%` }}
                    />
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-zinc-400">Output Tokens</span>
                    <span>{formatTokens(usage.total_output_tokens)} ({outputPct}%)</span>
                  </div>
                  <div className="h-3 bg-zinc-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-green-500 rounded-full transition-all"
                      style={{ width: `${outputPct}%` }}
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Cost Info */}
            <div className="bg-zinc-900 rounded-xl p-6">
              <h2 className="text-lg font-semibold mb-3">Cost Estimate</h2>
              <p className="text-zinc-400 text-sm mb-4">
                Based on current model pricing. Actual costs may vary.
              </p>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-zinc-800 rounded-lg p-3">
                  <p className="text-xs text-zinc-500 mb-1">Input Cost</p>
                  <p className="text-lg font-mono">
                    {formatCost(usage.total_input_tokens * 0.000003)}
                  </p>
                </div>
                <div className="bg-zinc-800 rounded-lg p-3">
                  <p className="text-xs text-zinc-500 mb-1">Output Cost</p>
                  <p className="text-lg font-mono">
                    {formatCost(usage.total_output_tokens * 0.000015)}
                  </p>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
