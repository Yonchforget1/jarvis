"use client";

import { Wrench, Brain, Cpu, Users } from "lucide-react";
import { useStats } from "@/hooks/use-stats";
import { useLearnings } from "@/hooks/use-learnings";
import { StatsCard } from "@/components/dashboard/stats-card";
import { BackendStatus } from "@/components/dashboard/backend-status";
import { LearningsTimeline } from "@/components/dashboard/learnings-timeline";
import { Skeleton } from "@/components/ui/skeleton";

export default function DashboardPage() {
  const { stats, loading: statsLoading } = useStats();
  const { learnings, loading: learningsLoading } = useLearnings();

  if (statsLoading) {
    return (
      <div className="p-6 space-y-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-28 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="overflow-y-auto h-full p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-sm text-muted-foreground">System overview and performance metrics</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard
          title="Backend"
          value={stats?.backend?.toUpperCase() || "N/A"}
          description={stats?.model || "No model"}
          icon={Cpu}
          iconColor="text-green-500"
        />
        <StatsCard
          title="Tools Available"
          value={stats?.tool_count || 0}
          description="Professional tools loaded"
          icon={Wrench}
          iconColor="text-blue-400"
        />
        <StatsCard
          title="Learnings"
          value={stats?.learnings_count || 0}
          description="Insights from past tasks"
          icon={Brain}
          iconColor="text-purple-400"
        />
        <StatsCard
          title="Active Sessions"
          value={stats?.active_sessions || 0}
          description="Currently connected"
          icon={Users}
          iconColor="text-orange-400"
        />
      </div>

      {/* Two-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <h3 className="mb-3 text-sm font-semibold">Recent Learnings</h3>
          {learningsLoading ? (
            <Skeleton className="h-48 rounded-xl" />
          ) : (
            <LearningsTimeline learnings={learnings.slice(-5)} />
          )}
        </div>
        <div>
          {stats && <BackendStatus stats={stats} />}
        </div>
      </div>
    </div>
  );
}
