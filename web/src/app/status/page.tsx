"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:3000";

interface HealthData {
  status: string;
  uptime_seconds: number;
  python_version: string;
  platform: string;
  process: {
    pid: number;
    memory_mb: number;
    memory_percent: number;
    cpu_percent: number;
    threads: number;
  };
  sessions: {
    active: number;
    memory_entries: number;
  };
  scheduler: {
    running: boolean;
    schedules_count: number;
    enabled_count: number;
  };
  backend: string;
  usage: {
    total_users: number;
    total_requests: number;
    total_tokens: number;
    estimated_total_cost_usd: number;
  };
}

function formatUptime(seconds: number): string {
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  const parts: string[] = [];
  if (d > 0) parts.push(`${d}d`);
  if (h > 0) parts.push(`${h}h`);
  if (m > 0) parts.push(`${m}m`);
  parts.push(`${s}s`);
  return parts.join(" ");
}

export default function StatusPage() {
  const router = useRouter();
  const [data, setData] = useState<HealthData | null>(null);
  const [error, setError] = useState("");
  const [lastCheck, setLastCheck] = useState("");

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  async function fetchHealth() {
    try {
      const res = await fetch(`${API_BASE}/api/health/detailed`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setData(json);
      setError("");
      setLastCheck(new Date().toLocaleTimeString());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to connect");
    }
  }

  return (
    <div className="min-h-screen bg-white dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 p-6">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold">System Status</h1>
            <p className="text-sm text-zinc-500 mt-1">
              Auto-refreshes every 10s {lastCheck && `| Last: ${lastCheck}`}
            </p>
          </div>
          <button
            onClick={() => router.push("/chat")}
            className="text-sm text-blue-500 hover:text-blue-400"
          >
            Back to Chat
          </button>
        </div>

        {error && (
          <div className="mb-6 p-4 rounded-lg bg-red-500/10 border border-red-500/30">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-red-500" />
              <span className="font-semibold text-red-400">API Unreachable</span>
            </div>
            <p className="text-sm text-red-300 mt-1">{error}</p>
          </div>
        )}

        {data && (
          <div className="space-y-6">
            {/* Overall Status */}
            <div className="flex items-center gap-3 p-4 rounded-lg bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800">
              <div className={`w-4 h-4 rounded-full ${data.status === "ok" ? "bg-green-500" : "bg-red-500"}`} />
              <div>
                <span className="font-semibold text-lg">
                  {data.status === "ok" ? "All Systems Operational" : "Degraded"}
                </span>
                <span className="text-sm text-zinc-500 ml-3">
                  Uptime: {formatUptime(data.uptime_seconds)}
                </span>
              </div>
            </div>

            {/* Metrics Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <MetricCard label="Active Sessions" value={data.sessions.active} />
              <MetricCard label="Memory" value={`${data.process.memory_mb} MB`} />
              <MetricCard label="CPU" value={`${data.process.cpu_percent}%`} />
              <MetricCard label="Threads" value={data.process.threads} />
              <MetricCard label="Total Requests" value={data.usage.total_requests} />
              <MetricCard label="Total Tokens" value={data.usage.total_tokens.toLocaleString()} />
              <MetricCard label="Est. Cost" value={`$${data.usage.estimated_total_cost_usd.toFixed(2)}`} />
              <MetricCard label="Users" value={data.usage.total_users} />
            </div>

            {/* Details */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <DetailCard title="Server">
                <Row label="Platform" value={data.platform} />
                <Row label="Python" value={data.python_version} />
                <Row label="PID" value={data.process.pid} />
                <Row label="Memory %" value={`${data.process.memory_percent}%`} />
              </DetailCard>
              <DetailCard title="Backend">
                <Row label="Active" value={data.backend} />
                <Row label="Memory Entries" value={data.sessions.memory_entries} />
              </DetailCard>
              <DetailCard title="Scheduler">
                <Row label="Status" value={data.scheduler.running ? "Running" : "Stopped"} />
                <Row label="Total Schedules" value={data.scheduler.schedules_count} />
                <Row label="Enabled" value={data.scheduler.enabled_count} />
              </DetailCard>
            </div>
          </div>
        )}

        {!data && !error && (
          <div className="text-center py-20 text-zinc-500 animate-pulse">
            Connecting to API...
          </div>
        )}
      </div>
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="p-4 rounded-lg bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800">
      <div className="text-2xl font-bold">{value}</div>
      <div className="text-xs text-zinc-500 mt-1">{label}</div>
    </div>
  );
}

function DetailCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="p-4 rounded-lg bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800">
      <h3 className="font-semibold mb-3 text-sm text-zinc-400">{title}</h3>
      <div className="space-y-2">{children}</div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex justify-between text-sm">
      <span className="text-zinc-500">{label}</span>
      <span className="font-mono">{value}</span>
    </div>
  );
}
