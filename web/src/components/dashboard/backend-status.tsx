"use client";

import { useEffect, useState } from "react";
import { Activity, Cpu, Clock, Zap, HardDrive, Server, MemoryStick } from "lucide-react";
import type { SystemStats } from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface HealthData {
  system?: {
    python_version?: string;
    platform?: string;
    architecture?: string;
    memory_mb?: number;
    cpu_percent?: number;
  };
  version?: string;
  tool_count?: number;
  learnings_count?: number;
}

function formatUptime(seconds: number): string {
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (d > 0) return `${d}d ${h}h ${m}m`;
  if (h > 0) return `${h}h ${m}m ${s}s`;
  return `${m}m ${s}s`;
}

function LiveUptime({ initialSeconds }: { initialSeconds: number }) {
  const [seconds, setSeconds] = useState(initialSeconds);

  useEffect(() => {
    setSeconds(initialSeconds);
  }, [initialSeconds]);

  useEffect(() => {
    const interval = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(interval);
  }, []);

  return <span className="text-sm font-mono tabular-nums">{formatUptime(seconds)}</span>;
}

export function BackendStatus({ stats }: { stats: SystemStats }) {
  const [health, setHealth] = useState<HealthData | null>(null);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const res = await fetch(`${API_URL}/api/health`);
        if (res.ok) {
          setHealth(await res.json());
        }
      } catch {
        // ignore
      }
    };
    fetchHealth();
    const interval = setInterval(fetchHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const items = [
    {
      icon: Activity,
      label: "Status",
      value: (
        <span className="flex items-center gap-2 text-green-400 font-medium">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500" />
          </span>
          Online
        </span>
      ),
      color: "text-green-500",
    },
    {
      icon: Cpu,
      label: "Model",
      value: (
        <span className="text-sm font-mono text-foreground truncate max-w-[140px]" title={stats.model}>
          {stats.model.split("-").slice(0, 2).join(" ")}
        </span>
      ),
      color: "text-blue-400",
    },
    {
      icon: Clock,
      label: "Uptime",
      value: <LiveUptime initialSeconds={stats.uptime_seconds} />,
      color: "text-yellow-400",
    },
    {
      icon: Zap,
      label: "Backend",
      value: <span className="text-sm font-medium capitalize">{stats.backend}</span>,
      color: "text-purple-400",
    },
  ];

  // Add system info from health endpoint
  const sysInfo = health?.system;
  const systemItems = [];

  if (sysInfo?.python_version) {
    systemItems.push({
      icon: Server,
      label: "Python",
      value: <span className="text-sm font-mono">{sysInfo.python_version}</span>,
      color: "text-cyan-400",
    });
  }
  if (sysInfo?.platform) {
    systemItems.push({
      icon: HardDrive,
      label: "Platform",
      value: (
        <span className="text-sm font-mono">
          {sysInfo.platform} {sysInfo.architecture ? `(${sysInfo.architecture})` : ""}
        </span>
      ),
      color: "text-orange-400",
    });
  }
  if (sysInfo?.cpu_percent !== undefined) {
    const cpuPct = Math.round(sysInfo.cpu_percent);
    const cpuColor = cpuPct > 80 ? "text-red-400" : cpuPct > 50 ? "text-yellow-400" : "text-green-400";
    systemItems.push({
      icon: Cpu,
      label: "CPU Usage",
      value: (
        <div className="flex items-center gap-2">
          <div className="w-16 h-1.5 rounded-full bg-muted overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                cpuPct > 80 ? "bg-red-400" : cpuPct > 50 ? "bg-yellow-400" : "bg-green-400"
              }`}
              style={{ width: `${cpuPct}%` }}
            />
          </div>
          <span className={`text-sm font-mono tabular-nums ${cpuColor}`}>{cpuPct}%</span>
        </div>
      ),
      color: "text-cyan-400",
    });
  }
  if (sysInfo?.memory_mb) {
    systemItems.push({
      icon: MemoryStick,
      label: "Memory",
      value: (
        <span className="text-sm font-mono tabular-nums">
          {sysInfo.memory_mb >= 1024
            ? `${(sysInfo.memory_mb / 1024).toFixed(1)} GB`
            : `${sysInfo.memory_mb} MB`}
        </span>
      ),
      color: "text-pink-400",
    });
  }

  return (
    <div className="rounded-2xl border border-border/50 bg-card/50 p-5 animate-fade-in-up">
      <h3 className="mb-4 text-xs font-medium uppercase tracking-wider text-muted-foreground/60">
        System Status
      </h3>
      <div className="space-y-4">
        {items.map((item) => (
          <div key={item.label} className="flex items-center justify-between">
            <div className="flex items-center gap-2.5 text-sm text-muted-foreground">
              <item.icon className={`h-4 w-4 ${item.color}`} />
              {item.label}
            </div>
            {item.value}
          </div>
        ))}
      </div>

      {/* System details */}
      {systemItems.length > 0 && (
        <>
          <div className="my-4 border-t border-border/30" />
          <h4 className="mb-3 text-[10px] font-medium uppercase tracking-wider text-muted-foreground/40">
            Runtime
          </h4>
          <div className="space-y-3">
            {systemItems.map((item) => (
              <div key={item.label} className="flex items-center justify-between">
                <div className="flex items-center gap-2.5 text-sm text-muted-foreground">
                  <item.icon className={`h-4 w-4 ${item.color}`} />
                  {item.label}
                </div>
                {item.value}
              </div>
            ))}
          </div>
        </>
      )}

      {/* API Version */}
      {health?.version && (
        <div className="mt-4 pt-3 border-t border-border/30 flex items-center justify-between">
          <span className="text-[10px] text-muted-foreground/40 uppercase tracking-wider">API Version</span>
          <span className="text-xs font-mono text-muted-foreground/60">v{health.version}</span>
        </div>
      )}
    </div>
  );
}
