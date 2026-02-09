import { Activity, Cpu, Clock } from "lucide-react";
import type { SystemStats } from "@/lib/types";

function formatUptime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

export function BackendStatus({ stats }: { stats: SystemStats }) {
  return (
    <div className="rounded-xl border border-white/5 bg-white/[0.02] p-5">
      <h3 className="mb-4 text-sm font-semibold">Backend Status</h3>
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Activity className="h-4 w-4 text-green-500" />
            Status
          </div>
          <span className="text-sm text-green-500">Online</span>
        </div>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Cpu className="h-4 w-4" />
            Model
          </div>
          <span className="text-sm font-mono">{stats.model}</span>
        </div>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Clock className="h-4 w-4" />
            Uptime
          </div>
          <span className="text-sm">{formatUptime(stats.uptime_seconds)}</span>
        </div>
      </div>
    </div>
  );
}
