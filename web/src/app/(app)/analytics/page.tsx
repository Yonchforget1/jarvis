"use client";

import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import {
  BarChart3,
  TrendingUp,
  TrendingDown,
  DollarSign,
  Zap,
  Hash,
  MessageSquare,
  Wrench,
  Calendar,
  Download,
  ArrowUpRight,
  ArrowDownRight,
} from "lucide-react";
import { api } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorBoundary } from "@/components/error-boundary";
import { ErrorState } from "@/components/ui/error-state";

interface DayData {
  date: string;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  sessions: number;
  messages: number;
  tool_calls: number;
}

interface TrendsResponse {
  days: DayData[];
  total_cost_usd: number;
  period_days: number;
}

interface SessionCost {
  session_id: string;
  title: string;
  cost_estimate_usd: number;
  input_tokens: number;
  output_tokens: number;
  message_count: number;
  tool_calls: number;
  last_active: string;
}

interface ToolStat {
  name: string;
  calls: number;
  errors: number;
  avg_ms: number;
}

function formatTokens(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(1) + "K";
  return String(n);
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr + "T00:00:00");
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function MetricCard({ icon: Icon, label, value, sub, color }: {
  icon: typeof Zap;
  label: string;
  value: string;
  sub?: string;
  color: string;
}) {
  return (
    <div className="rounded-xl border border-border/50 bg-card/50 p-4">
      <div className="flex items-center gap-2 mb-2">
        <Icon className={`h-4 w-4 ${color}`} />
        <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground/50">{label}</span>
      </div>
      <p className="text-xl font-bold tabular-nums">{value}</p>
      {sub && <p className="text-[10px] text-muted-foreground/40 mt-0.5">{sub}</p>}
    </div>
  );
}

export default function AnalyticsPage() {
  const [trends, setTrends] = useState<TrendsResponse | null>(null);
  const [sessions, setSessions] = useState<SessionCost[]>([]);
  const [totalCost, setTotalCost] = useState(0);
  const [tools, setTools] = useState<ToolStat[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [days, setDays] = useState(30);
  const [hoveredBar, setHoveredBar] = useState<number | null>(null);
  const [metric, setMetric] = useState<"tokens" | "cost" | "messages">("tokens");
  const inflightRef = useRef(false);

  const fetchAll = useCallback(async (period: number) => {
    if (inflightRef.current) return;
    inflightRef.current = true;
    try {
      const [trendsRes, sessionsRes, toolsRes] = await Promise.all([
        api.get<TrendsResponse>(`/api/stats/usage-trends?days=${period}`),
        api.get<{ sessions: SessionCost[]; total_cost_usd?: number }>("/api/stats/sessions?limit=50"),
        api.get<{ tools: ToolStat[] }>("/api/stats/tools"),
      ]);
      setTrends(trendsRes);
      setSessions(sessionsRes.sessions || []);
      setTotalCost(sessionsRes.total_cost_usd || 0);
      setTools(toolsRes.tools || []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load analytics");
    } finally {
      setLoading(false);
      inflightRef.current = false;
    }
  }, []);

  useEffect(() => {
    setLoading(true);
    fetchAll(days);
  }, [days, fetchAll]);

  // Computed aggregates
  const aggregates = useMemo(() => {
    if (!trends) return null;
    const d = trends.days;
    const totalTokens = d.reduce((s, day) => s + day.input_tokens + day.output_tokens, 0);
    const totalMessages = d.reduce((s, day) => s + day.messages, 0);
    const totalToolCalls = d.reduce((s, day) => s + day.tool_calls, 0);
    const totalSessions = d.reduce((s, day) => s + day.sessions, 0);
    const activeDays = d.filter((day) => day.messages > 0).length;
    const avgDailyCost = trends.total_cost_usd / Math.max(activeDays, 1);

    // Trend comparison: last half vs first half
    const mid = Math.floor(d.length / 2);
    const firstHalf = d.slice(0, mid);
    const secondHalf = d.slice(mid);
    const firstCost = firstHalf.reduce((s, day) => s + day.cost_usd, 0);
    const secondCost = secondHalf.reduce((s, day) => s + day.cost_usd, 0);
    const costTrend = firstCost > 0 ? ((secondCost - firstCost) / firstCost) * 100 : 0;

    return { totalTokens, totalMessages, totalToolCalls, totalSessions, activeDays, avgDailyCost, costTrend };
  }, [trends]);

  // Export analytics as CSV
  const exportCSV = useCallback(() => {
    if (!trends) return;
    const headers = "Date,Input Tokens,Output Tokens,Cost USD,Sessions,Messages,Tool Calls";
    const rows = trends.days.map((d) =>
      `${d.date},${d.input_tokens},${d.output_tokens},${d.cost_usd},${d.sessions},${d.messages},${d.tool_calls}`
    );
    const csv = [headers, ...rows].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `jarvis-analytics-${days}d-${new Date().toISOString().split("T")[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [trends, days]);

  if (loading) {
    return (
      <div className="h-full overflow-y-auto p-4 sm:p-6 space-y-4">
        <Skeleton className="h-10 w-48 rounded-xl" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-24 rounded-xl" />)}
        </div>
        <Skeleton className="h-48 rounded-xl" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full overflow-y-auto p-4 sm:p-6">
        <ErrorState message={error} onRetry={() => fetchAll(days)} />
      </div>
    );
  }

  const barData = trends?.days || [];
  const getBarValue = (d: DayData) => {
    if (metric === "cost") return d.cost_usd;
    if (metric === "messages") return d.messages;
    return d.input_tokens + d.output_tokens;
  };
  const maxBar = Math.max(...barData.map(getBarValue), 1);
  const hovered = hoveredBar !== null ? barData[hoveredBar] : null;

  return (
    <ErrorBoundary>
      <div className="h-full overflow-y-auto p-4 sm:p-6 pb-20">
        <div className="mx-auto max-w-6xl space-y-5">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold tracking-tight">Analytics</h1>
              <p className="text-sm text-muted-foreground/60 mt-0.5">Usage patterns and cost analysis</p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={exportCSV}
                className="flex items-center gap-1.5 rounded-lg border border-border/50 bg-muted/30 px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
              >
                <Download className="h-3.5 w-3.5" />
                Export CSV
              </button>
            </div>
          </div>

          {/* Summary cards */}
          {aggregates && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <MetricCard
                icon={DollarSign}
                label="Total Cost"
                value={`$${totalCost.toFixed(4)}`}
                sub={`$${aggregates.avgDailyCost.toFixed(4)}/active day`}
                color="text-green-400"
              />
              <MetricCard
                icon={Zap}
                label={`Tokens (${days}d)`}
                value={formatTokens(aggregates.totalTokens)}
                sub={`${aggregates.activeDays} active days`}
                color="text-yellow-400"
              />
              <MetricCard
                icon={MessageSquare}
                label="Messages"
                value={aggregates.totalMessages.toLocaleString()}
                sub={`${aggregates.totalSessions} sessions`}
                color="text-blue-400"
              />
              <div className="rounded-xl border border-border/50 bg-card/50 p-4">
                <div className="flex items-center gap-2 mb-2">
                  <TrendingUp className="h-4 w-4 text-cyan-400" />
                  <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground/50">Cost Trend</span>
                </div>
                <div className="flex items-center gap-2">
                  <p className={`text-xl font-bold tabular-nums ${
                    aggregates.costTrend > 10 ? "text-red-400" : aggregates.costTrend < -10 ? "text-green-400" : "text-foreground"
                  }`}>
                    {aggregates.costTrend > 0 ? "+" : ""}{aggregates.costTrend.toFixed(0)}%
                  </p>
                  {aggregates.costTrend > 5 ? (
                    <ArrowUpRight className="h-4 w-4 text-red-400" />
                  ) : aggregates.costTrend < -5 ? (
                    <ArrowDownRight className="h-4 w-4 text-green-400" />
                  ) : null}
                </div>
                <p className="text-[10px] text-muted-foreground/40 mt-0.5">vs first half of period</p>
              </div>
            </div>
          )}

          {/* Usage chart */}
          <div className="rounded-2xl border border-border/50 bg-card/30 p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-medium uppercase tracking-wider text-muted-foreground/60 flex items-center gap-1.5">
                <BarChart3 className="h-3 w-3" /> Daily Usage
              </h3>
              <div className="flex items-center gap-3">
                {/* Metric toggle */}
                <div className="flex items-center gap-1">
                  {(["tokens", "cost", "messages"] as const).map((m) => (
                    <button
                      key={m}
                      onClick={() => setMetric(m)}
                      className={`px-2 py-0.5 text-[10px] rounded-md transition-colors capitalize ${
                        metric === m ? "bg-primary/20 text-primary font-medium" : "text-muted-foreground/50 hover:text-muted-foreground hover:bg-muted"
                      }`}
                    >
                      {m}
                    </button>
                  ))}
                </div>
                {/* Period selector */}
                <div className="flex items-center gap-1">
                  {[7, 14, 30, 60, 90].map((d) => (
                    <button
                      key={d}
                      onClick={() => setDays(d)}
                      className={`px-2 py-0.5 text-[10px] rounded-md transition-colors ${
                        days === d ? "bg-primary/20 text-primary font-medium" : "text-muted-foreground/50 hover:text-muted-foreground hover:bg-muted"
                      }`}
                    >
                      {d}d
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Hover tooltip */}
            {hovered && (
              <div className="flex items-center gap-4 text-[10px] text-muted-foreground/70 bg-muted/30 rounded-lg px-3 py-1.5">
                <span className="font-medium text-foreground">{formatDate(hovered.date)}</span>
                <span>{formatTokens(hovered.input_tokens + hovered.output_tokens)} tokens</span>
                <span>${hovered.cost_usd.toFixed(4)}</span>
                <span>{hovered.messages} msgs</span>
                <span>{hovered.tool_calls} tools</span>
                <span>{hovered.sessions} sessions</span>
              </div>
            )}

            {/* Bar chart */}
            <div
              className="flex items-end gap-[2px] h-36"
              onMouseLeave={() => setHoveredBar(null)}
              role="img"
              aria-label={`Usage chart for the last ${days} days showing ${metric}`}
            >
              {barData.map((day, i) => {
                const val = getBarValue(day);
                const heightPct = val > 0 ? Math.max((val / maxBar) * 100, 3) : 0;
                const isHovered = hoveredBar === i;
                const isToday = i === barData.length - 1;
                return (
                  <div
                    key={day.date}
                    className="flex-1 flex flex-col items-center justify-end cursor-pointer"
                    onMouseEnter={() => setHoveredBar(i)}
                  >
                    <div
                      className={`w-full rounded-t-sm transition-all duration-150 ${
                        isHovered ? "bg-primary" : isToday ? "bg-primary/60" : "bg-primary/25"
                      }`}
                      style={{ height: `${heightPct}%`, minHeight: val > 0 ? "3px" : "0px" }}
                    />
                    {(i === 0 || i === barData.length - 1 || (barData.length <= 14 && i % 2 === 0) || (barData.length > 14 && barData.length <= 30 && i % 7 === 0) || (barData.length > 30 && i % 14 === 0)) && (
                      <span className={`text-[7px] mt-1 tabular-nums ${isToday ? "text-muted-foreground/60 font-medium" : "text-muted-foreground/25"}`}>
                        {formatDate(day.date).replace(/\s+/g, "\u00a0")}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Two-column: Session costs + Tool performance */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Session costs table */}
            <div className="rounded-xl border border-border/50 bg-card/50 p-4 space-y-3">
              <h3 className="text-xs font-medium flex items-center gap-1.5">
                <DollarSign className="h-3 w-3 text-green-400" />
                Session Costs
              </h3>
              <div className="space-y-1 max-h-72 overflow-y-auto">
                {sessions.length === 0 ? (
                  <p className="text-xs text-muted-foreground/40 py-4 text-center">No session data</p>
                ) : (
                  sessions.slice(0, 20).map((s) => (
                    <div key={s.session_id} className="flex items-center justify-between py-1.5 border-b border-border/20 last:border-0">
                      <div className="flex-1 min-w-0">
                        <p className="text-xs truncate">{s.title}</p>
                        <p className="text-[10px] text-muted-foreground/40">
                          {formatTokens(s.input_tokens + s.output_tokens)} tokens &middot; {s.message_count} msgs
                        </p>
                      </div>
                      <span className="text-xs font-mono tabular-nums text-muted-foreground/70 shrink-0 ml-2">
                        ${s.cost_estimate_usd.toFixed(4)}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Tool performance */}
            <div className="rounded-xl border border-border/50 bg-card/50 p-4 space-y-3">
              <h3 className="text-xs font-medium flex items-center gap-1.5">
                <Wrench className="h-3 w-3 text-purple-400" />
                Tool Performance
              </h3>
              <div className="space-y-1 max-h-72 overflow-y-auto">
                {tools.length === 0 ? (
                  <p className="text-xs text-muted-foreground/40 py-4 text-center">No tool usage data</p>
                ) : (
                  tools.map((t) => {
                    const errorRate = t.calls > 0 ? (t.errors / t.calls) * 100 : 0;
                    return (
                      <div key={t.name} className="flex items-center justify-between py-1.5 border-b border-border/20 last:border-0">
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-mono">{t.name}</p>
                          <div className="flex items-center gap-2 text-[10px] text-muted-foreground/40">
                            <span>{t.calls} calls</span>
                            {t.errors > 0 && (
                              <span className={`${errorRate > 10 ? "text-red-400" : "text-yellow-400"}`}>
                                {errorRate.toFixed(0)}% err
                              </span>
                            )}
                          </div>
                        </div>
                        <span className="text-[10px] font-mono tabular-nums text-muted-foreground/50 shrink-0 ml-2">
                          {t.avg_ms}ms
                        </span>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </ErrorBoundary>
  );
}
