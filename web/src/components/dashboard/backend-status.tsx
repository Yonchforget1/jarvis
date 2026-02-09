"use client";

import { useEffect, useState } from "react";
import { Activity, Cpu, Clock, Zap } from "lucide-react";
import type { SystemStats } from "@/lib/types";

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
  const items = [
    {
      icon: Activity,
      label: "Status",
      value: <span className="text-green-400 font-medium">Online</span>,
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

  return (
    <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-5 animate-fade-in-up">
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
    </div>
  );
}
