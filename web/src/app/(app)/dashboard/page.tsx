"use client";

import Link from "next/link";
import { Wrench, Brain, Cpu, Users, RefreshCw, Zap, Hash, MessageSquare, Settings, Download, ArrowRight } from "lucide-react";
import { useStats } from "@/hooks/use-stats";
import { useLearnings } from "@/hooks/use-learnings";
import { StatsCard } from "@/components/dashboard/stats-card";
import { BackendStatus } from "@/components/dashboard/backend-status";
import { LearningsTimeline } from "@/components/dashboard/learnings-timeline";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/error-state";

function formatTokens(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(1) + "K";
  return String(n);
}

export default function DashboardPage() {
  const { stats, loading: statsLoading, error: statsError, refetch } = useStats(15000);
  const { learnings, loading: learningsLoading } = useLearnings();

  if (statsLoading) {
    return (
      <div className="h-full overflow-y-auto p-4 sm:p-6">
        <div className="mx-auto max-w-6xl space-y-6">
        {/* Header skeleton */}
        <div className="flex items-center justify-between">
          <div className="space-y-2">
            <Skeleton className="h-7 w-36 rounded-lg" />
            <Skeleton className="h-4 w-64 rounded-lg" />
          </div>
          <Skeleton className="h-8 w-20 rounded-lg" />
        </div>
        {/* Stats grid skeleton */}
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="rounded-2xl border border-border/50 bg-card/50 p-4 space-y-3">
              <div className="flex items-center gap-2">
                <Skeleton className="h-9 w-9 rounded-xl" />
                <Skeleton className="h-3 w-16 rounded" />
              </div>
              <Skeleton className="h-7 w-12 rounded" />
              <Skeleton className="h-3 w-24 rounded" />
            </div>
          ))}
        </div>
        {/* Quick actions skeleton */}
        <div className="space-y-3">
          <Skeleton className="h-3 w-24 rounded" />
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-11 rounded-xl" />
            ))}
          </div>
        </div>
        {/* Bottom sections skeleton */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
          <Skeleton className="md:col-span-2 lg:col-span-2 h-48 rounded-2xl" />
          <Skeleton className="h-48 rounded-2xl" />
        </div>
        </div>
      </div>
    );
  }

  if (statsError) {
    return (
      <div className="h-full overflow-y-auto p-4 sm:p-6">
        <ErrorState message={statsError} onRetry={refetch} />
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto p-4 sm:p-6 pb-20">
      <div className="mx-auto max-w-6xl space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-sm text-muted-foreground/60 mt-0.5">
            Real-time system overview and performance metrics
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={refetch}
          className="h-8 gap-1.5 text-xs rounded-lg border-border/50"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">Refresh</span>
        </Button>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
        <StatsCard
          title="Backend"
          value={stats?.backend?.toUpperCase() || "N/A"}
          description={stats?.model?.split("-").slice(0, 3).join("-") || "No model"}
          icon={Cpu}
          iconColor="text-green-400"
          bgColor="bg-green-400/10"
        />
        <StatsCard
          title="Tools"
          value={stats?.tool_count || 0}
          description="Professional tools loaded"
          icon={Wrench}
          iconColor="text-blue-400"
          bgColor="bg-blue-400/10"
        />
        <StatsCard
          title="Learnings"
          value={stats?.learnings_count || 0}
          description="Insights from past tasks"
          icon={Brain}
          iconColor="text-purple-400"
          bgColor="bg-purple-400/10"
        />
        <StatsCard
          title="Tokens Used"
          value={formatTokens((stats?.total_input_tokens || 0) + (stats?.total_output_tokens || 0))}
          description={`${formatTokens(stats?.total_input_tokens || 0)} in / ${formatTokens(stats?.total_output_tokens || 0)} out`}
          icon={Zap}
          iconColor="text-yellow-400"
          bgColor="bg-yellow-400/10"
        />
        <StatsCard
          title="Tool Calls"
          value={stats?.total_tool_calls || 0}
          description="Tools executed this session"
          icon={Hash}
          iconColor="text-cyan-400"
          bgColor="bg-cyan-400/10"
        />
        <StatsCard
          title="Sessions"
          value={stats?.active_sessions || 0}
          description="Currently active"
          icon={Users}
          iconColor="text-orange-400"
          bgColor="bg-orange-400/10"
        />
      </div>

      {/* Quick Actions */}
      <div className="space-y-3">
        <h3 className="text-xs font-medium uppercase tracking-wider text-muted-foreground/60">
          Quick Actions
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { href: "/chat", label: "New Chat", icon: MessageSquare, color: "text-primary", bg: "bg-primary/10 border-primary/20 hover:bg-primary/15" },
            { href: "/tools", label: "View Tools", icon: Wrench, color: "text-blue-400", bg: "bg-blue-400/10 border-blue-400/20 hover:bg-blue-400/15" },
            { href: "/learnings", label: "Learnings", icon: Brain, color: "text-purple-400", bg: "bg-purple-400/10 border-purple-400/20 hover:bg-purple-400/15" },
            { href: "/settings", label: "Settings", icon: Settings, color: "text-orange-400", bg: "bg-orange-400/10 border-orange-400/20 hover:bg-orange-400/15" },
          ].map((action) => (
            <Link
              key={action.href}
              href={action.href}
              className={`group flex items-center gap-2.5 rounded-xl border p-3 transition-all duration-200 hover:scale-[1.02] active:scale-[0.98] ${action.bg}`}
            >
              <action.icon className={`h-4 w-4 ${action.color} shrink-0`} />
              <span className="text-xs font-medium text-foreground">{action.label}</span>
              <ArrowRight className="ml-auto h-3 w-3 text-muted-foreground/30 group-hover:text-muted-foreground/60 transition-all group-hover:translate-x-0.5" />
            </Link>
          ))}
        </div>
      </div>

      {/* Two-column layout */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
        <div className="md:col-span-2 lg:col-span-2 space-y-3">
          <h3 className="text-xs font-medium uppercase tracking-wider text-muted-foreground/60">
            Recent Learnings
          </h3>
          {learningsLoading ? (
            <Skeleton className="h-48 rounded-2xl" />
          ) : (
            <LearningsTimeline learnings={learnings.slice(-5)} />
          )}
        </div>
        <div className="space-y-3">
          <h3 className="text-xs font-medium uppercase tracking-wider text-muted-foreground/60">
            System Status
          </h3>
          {stats && <BackendStatus stats={stats} />}
        </div>
      </div>
      </div>
    </div>
  );
}
