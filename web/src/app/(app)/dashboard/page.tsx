"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Wrench, Brain, Cpu, Users, RefreshCw, Zap, Hash, MessageSquare, Settings, ArrowRight, Clock, AlertTriangle, DollarSign, BarChart3 } from "lucide-react";
import { useStats } from "@/hooks/use-stats";
import { useLearnings } from "@/hooks/use-learnings";
import { StatsCard } from "@/components/dashboard/stats-card";
import { BackendStatus } from "@/components/dashboard/backend-status";
import { LearningsTimeline } from "@/components/dashboard/learnings-timeline";
import { UsageTrends } from "@/components/dashboard/usage-trends";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/error-state";
import { api } from "@/lib/api";

function formatTokens(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(1) + "K";
  return String(n);
}

function formatUptime(seconds: number): string {
  if (seconds < 60) return `${Math.floor(seconds)}s`;
  const mins = Math.floor(seconds / 60);
  if (mins < 60) return `${mins}m`;
  const hours = Math.floor(mins / 60);
  const remMins = mins % 60;
  if (hours < 24) return remMins > 0 ? `${hours}h ${remMins}m` : `${hours}h`;
  const days = Math.floor(hours / 24);
  const remHours = hours % 24;
  return remHours > 0 ? `${days}d ${remHours}h` : `${days}d`;
}

const STALE_THRESHOLD_SECONDS = 45;

export default function DashboardPage() {
  const { stats, loading: statsLoading, refetching, error: statsError, refetch, lastUpdated } = useStats(15000);
  const { learnings, loading: learningsLoading, error: learningsError } = useLearnings();
  const [lastUpdatedText, setLastUpdatedText] = useState("");
  const [isStale, setIsStale] = useState(false);
  const [sessionStats, setSessionStats] = useState<{ session_id: string; title: string; cost_estimate_usd: number; input_tokens: number; output_tokens: number; message_count: number }[]>([]);
  const [sessionStatsError, setSessionStatsError] = useState<string | null>(null);
  const [totalCostAllSessions, setTotalCostAllSessions] = useState<number>(0);

  // Fetch session cost breakdown
  useEffect(() => {
    api.get<{ sessions: typeof sessionStats; total_cost_usd?: number }>("/api/stats/sessions?limit=10")
      .then((res) => {
        setSessionStats(res.sessions || []);
        setTotalCostAllSessions(res.total_cost_usd ?? res.sessions?.reduce((s, x) => s + x.cost_estimate_usd, 0) ?? 0);
        setSessionStatsError(null);
      })
      .catch((err) => {
        setSessionStatsError(err instanceof Error ? err.message : "Failed to load sessions");
      });
  }, []);

  // Update "last updated" text every second and detect stale data
  useEffect(() => {
    if (!lastUpdated) return;
    const update = () => {
      const secs = Math.floor((Date.now() - lastUpdated.getTime()) / 1000);
      if (secs < 5) setLastUpdatedText("just now");
      else if (secs < 60) setLastUpdatedText(`${secs}s ago`);
      else setLastUpdatedText(`${Math.floor(secs / 60)}m ago`);
      setIsStale(secs > STALE_THRESHOLD_SECONDS);
    };
    update();
    const timer = setInterval(update, 1000);
    return () => clearInterval(timer);
  }, [lastUpdated]);

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

  if (statsError && !stats) {
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
        <div className="flex items-center gap-2">
          {lastUpdatedText && (
            <span className="text-[10px] text-muted-foreground/40 font-mono tabular-nums hidden sm:inline">
              Updated {lastUpdatedText}
            </span>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={refetch}
            disabled={refetching}
            className="h-8 gap-1.5 text-xs rounded-lg border-border/50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${refetching ? "animate-spin" : ""}`} />
            <span className="hidden sm:inline">{refetching ? "Refreshing..." : "Refresh"}</span>
          </Button>
        </div>
      </div>

      {/* Connection error with stale data */}
      {statsError && stats && (
        <div className="flex items-center gap-2 rounded-xl border border-red-500/20 bg-red-500/5 px-4 py-2.5 animate-fade-in">
          <AlertTriangle className="h-4 w-4 text-red-400 shrink-0" />
          <span className="text-xs text-red-400">Showing cached data &mdash; {statsError}</span>
          <button
            onClick={refetch}
            disabled={refetching}
            className="ml-auto text-xs text-red-400 underline underline-offset-2 hover:text-red-300 transition-colors"
          >
            {refetching ? "Retrying..." : "Retry"}
          </button>
        </div>
      )}

      {/* Stale data warning */}
      {isStale && !statsError && (
        <div className={`flex items-center gap-2 rounded-xl border border-yellow-500/20 bg-yellow-500/5 px-4 py-2.5 animate-fade-in transition-opacity ${refetching ? "opacity-50" : ""}`}>
          <AlertTriangle className="h-4 w-4 text-yellow-500 shrink-0" />
          <span className="text-xs text-yellow-400">Data may be outdated (last update {lastUpdatedText})</span>
          <button
            onClick={refetch}
            disabled={refetching}
            className="ml-auto text-xs text-yellow-400 underline underline-offset-2 hover:text-yellow-300 transition-colors"
          >
            {refetching ? "Refreshing..." : "Refresh now"}
          </button>
        </div>
      )}

      {/* Stats Grid */}
      <div role="region" aria-live="polite" aria-label="System statistics" className="grid grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
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
          description={`Uptime: ${formatUptime(stats?.uptime_seconds || 0)}`}
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
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          {[
            { href: "/chat", label: "New Chat", icon: MessageSquare, color: "text-primary", bg: "bg-primary/10 border-primary/20 hover:bg-primary/15" },
            { href: "/tools", label: "View Tools", icon: Wrench, color: "text-blue-400", bg: "bg-blue-400/10 border-blue-400/20 hover:bg-blue-400/15" },
            { href: "/learnings", label: "Learnings", icon: Brain, color: "text-purple-400", bg: "bg-purple-400/10 border-purple-400/20 hover:bg-purple-400/15" },
            { href: "/analytics", label: "Analytics", icon: BarChart3, color: "text-cyan-400", bg: "bg-cyan-400/10 border-cyan-400/20 hover:bg-cyan-400/15" },
            { href: "/settings", label: "Settings", icon: Settings, color: "text-orange-400", bg: "bg-orange-400/10 border-orange-400/20 hover:bg-orange-400/15" },
          ].map((action) => (
            <Link
              key={action.href}
              href={action.href}
              aria-label={action.label}
              className={`group flex items-center gap-2.5 rounded-xl border p-3 transition-all duration-200 hover:scale-[1.02] active:scale-[0.98] ${action.bg}`}
            >
              <action.icon className={`h-4 w-4 ${action.color} shrink-0`} />
              <span className="text-xs font-medium text-foreground">{action.label}</span>
              <ArrowRight className="ml-auto h-3 w-3 text-muted-foreground/30 group-hover:text-muted-foreground/60 transition-all group-hover:translate-x-0.5" />
            </Link>
          ))}
        </div>
      </div>

      {/* Quick-start Prompts */}
      <div className="space-y-3">
        <h3 className="text-xs font-medium uppercase tracking-wider text-muted-foreground/60">
          Try These
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {[
            { icon: Zap, label: "Build a Godot game", prompt: "Create a simple 2D platformer game in Godot with a player character that can run and jump", color: "text-yellow-400" },
            { icon: Brain, label: "Review my learnings", prompt: "Search my learnings and summarize key patterns and areas for improvement", color: "text-purple-400" },
            { icon: Wrench, label: "Automate a workflow", prompt: "Help me automate a repetitive task on my computer step by step", color: "text-blue-400" },
            { icon: MessageSquare, label: "Research a topic", prompt: "Search the web and provide a comprehensive summary about", color: "text-green-400" },
          ].map((p) => (
            <Link
              key={p.label}
              href={`/chat?prompt=${encodeURIComponent(p.prompt)}`}
              aria-label={`Try: ${p.label}`}
              className="group flex items-start gap-3 rounded-xl border border-border/30 bg-card/30 p-3.5 text-left transition-all duration-200 hover:border-border hover:bg-card/60 hover:scale-[1.01] active:scale-[0.99]"
            >
              <p.icon className={`h-4 w-4 ${p.color} shrink-0 mt-0.5`} />
              <span className="text-xs text-muted-foreground group-hover:text-foreground transition-colors">{p.label}</span>
            </Link>
          ))}
        </div>
      </div>

      {/* Usage Trends Chart */}
      <UsageTrends />

      {/* Session Cost Breakdown */}
      {sessionStatsError && (
        <p className="text-xs text-red-400">Failed to load session costs</p>
      )}
      {sessionStats.length > 0 && (() => {
        const maxCost = Math.max(...sessionStats.map((s) => s.cost_estimate_usd));
        return (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-medium uppercase tracking-wider text-muted-foreground/60 flex items-center gap-1.5">
              <DollarSign className="h-3 w-3" /> Session Costs
            </h3>
            <span className="text-xs font-medium text-primary tabular-nums">
              Total: ${totalCostAllSessions.toFixed(4)}
            </span>
          </div>
          <div className="rounded-2xl border border-border/50 bg-card/30 overflow-hidden">
            <div className="grid grid-cols-[1fr_auto_auto] gap-x-4 px-4 py-2 text-[10px] font-medium uppercase tracking-wider text-muted-foreground/50 border-b border-border/30">
              <span>Session</span>
              <span>Tokens</span>
              <span>Est. Cost</span>
            </div>
            {sessionStats.map((s) => (
              <Link
                key={s.session_id}
                href={`/chat?session=${s.session_id}`}
                className="relative grid grid-cols-[1fr_auto_auto] gap-x-4 px-4 py-2.5 text-xs hover:bg-muted/50 transition-colors border-b border-border/20 last:border-b-0 overflow-hidden"
              >
                {maxCost > 0 && (
                  <div
                    className="absolute inset-y-0 left-0 bg-primary/5"
                    style={{ width: `${(s.cost_estimate_usd / maxCost) * 100}%` }}
                  />
                )}
                <span className="relative truncate text-foreground/80">{s.title}</span>
                <span className="relative text-muted-foreground/60 tabular-nums">{formatTokens(s.input_tokens + s.output_tokens)}</span>
                <span className="relative text-primary/80 font-medium tabular-nums">${s.cost_estimate_usd.toFixed(4)}</span>
              </Link>
            ))}
          </div>
        </div>
        );
      })()}

      {/* Two-column layout */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
        <div className="md:col-span-2 lg:col-span-2 space-y-3">
          <h3 className="text-xs font-medium uppercase tracking-wider text-muted-foreground/60">
            Recent Learnings
          </h3>
          {learningsLoading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-20 rounded-2xl" />
              ))}
            </div>
          ) : learningsError ? (
            <ErrorState message="Failed to load recent learnings" />
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
