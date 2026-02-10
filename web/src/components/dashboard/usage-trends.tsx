"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { TrendingUp, BarChart3 } from "lucide-react";
import { api } from "@/lib/api";

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

function formatDate(dateStr: string): string {
  const d = new Date(dateStr + "T00:00:00");
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function formatTokens(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(1) + "K";
  return String(n);
}

export function UsageTrends() {
  const [data, setData] = useState<TrendsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [days, setDays] = useState(7);
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const inflightRef = useRef(false);

  const fetchTrends = useCallback(async (period: number) => {
    if (inflightRef.current) return;
    inflightRef.current = true;
    try {
      const res = await api.get<TrendsResponse>(`/api/stats/usage-trends?days=${period}`);
      setData(res);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load trends");
    } finally {
      setLoading(false);
      inflightRef.current = false;
    }
  }, []);

  useEffect(() => {
    setLoading(true);
    fetchTrends(days);
  }, [days, fetchTrends]);

  if (loading) {
    return (
      <div className="rounded-2xl border border-border/50 bg-card/30 p-5 animate-pulse">
        <div className="h-4 w-32 bg-muted rounded mb-4" />
        <div className="h-32 bg-muted/50 rounded" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="rounded-2xl border border-border/50 bg-card/30 p-5">
        <p className="text-xs text-red-400">{error || "No data"}</p>
      </div>
    );
  }

  const maxTokens = Math.max(...data.days.map((d) => d.input_tokens + d.output_tokens), 1);
  const maxCost = Math.max(...data.days.map((d) => d.cost_usd), 0.0001);
  const hovered = hoveredIndex !== null ? data.days[hoveredIndex] : null;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-medium uppercase tracking-wider text-muted-foreground/60 flex items-center gap-1.5">
          <BarChart3 className="h-3 w-3" /> Usage Trends
        </h3>
        <div className="flex items-center gap-1">
          {[7, 14, 30].map((d) => (
            <button
              key={d}
              onClick={() => setDays(d)}
              className={`px-2 py-0.5 text-[10px] rounded-md transition-colors ${
                days === d
                  ? "bg-primary/20 text-primary font-medium"
                  : "text-muted-foreground/50 hover:text-muted-foreground hover:bg-muted"
              }`}
            >
              {d}d
            </button>
          ))}
        </div>
      </div>

      <div className="rounded-2xl border border-border/50 bg-card/30 p-4">
        {/* Summary line */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <span className="text-sm font-semibold text-foreground tabular-nums">
              ${data.total_cost_usd.toFixed(4)}
            </span>
            <span className="text-[10px] text-muted-foreground/50">
              total ({data.period_days} days)
            </span>
          </div>
          {data.days.length >= 2 && (() => {
            const recent = data.days.slice(-3).reduce((s, d) => s + d.cost_usd, 0);
            const earlier = data.days.slice(-6, -3).reduce((s, d) => s + d.cost_usd, 0);
            if (earlier === 0) return null;
            const pctChange = ((recent - earlier) / earlier) * 100;
            const isUp = pctChange > 5;
            const isDown = pctChange < -5;
            return (
              <span className={`inline-flex items-center gap-0.5 text-[10px] font-medium ${isUp ? "text-yellow-400" : isDown ? "text-green-400" : "text-muted-foreground/40"}`}>
                <TrendingUp className={`h-2.5 w-2.5 ${isDown ? "rotate-180" : ""} ${!isUp && !isDown ? "hidden" : ""}`} />
                {isUp ? "+" : ""}{pctChange.toFixed(0)}%
              </span>
            );
          })()}
        </div>

        {/* Tooltip */}
        {hovered && (
          <div className="mb-2 flex items-center gap-3 text-[10px] text-muted-foreground/70 bg-muted/30 rounded-lg px-3 py-1.5 transition-all">
            <span className="font-medium text-foreground">{formatDate(hovered.date)}</span>
            <span>{formatTokens(hovered.input_tokens + hovered.output_tokens)} tokens</span>
            <span>${hovered.cost_usd.toFixed(4)}</span>
            <span>{hovered.sessions} sessions</span>
            <span>{hovered.messages} msgs</span>
          </div>
        )}

        {/* Bar chart */}
        <div
          className="flex items-end gap-[2px] h-24"
          onMouseLeave={() => setHoveredIndex(null)}
          role="img"
          aria-label={`Usage trend chart for the last ${data.period_days} days`}
        >
          {data.days.map((day, i) => {
            const totalTokens = day.input_tokens + day.output_tokens;
            const heightPct = totalTokens > 0 ? Math.max((totalTokens / maxTokens) * 100, 4) : 0;
            const costIntensity = day.cost_usd / maxCost;
            const isHovered = hoveredIndex === i;
            const isToday = i === data.days.length - 1;

            return (
              <div
                key={day.date}
                className="flex-1 flex flex-col items-center justify-end cursor-pointer group"
                onMouseEnter={() => setHoveredIndex(i)}
              >
                <div
                  className={`w-full rounded-t-sm transition-all duration-150 ${
                    isHovered
                      ? "bg-primary"
                      : isToday
                        ? "bg-primary/60"
                        : costIntensity > 0.5
                          ? "bg-primary/40"
                          : "bg-primary/20"
                  }`}
                  style={{ height: `${heightPct}%`, minHeight: totalTokens > 0 ? "3px" : "0px" }}
                />
                {/* Day label (only show a few) */}
                {(i === 0 || i === data.days.length - 1 || (data.days.length > 14 && i % 7 === 0) || (data.days.length <= 14 && i % 2 === 0)) && (
                  <span className={`text-[8px] mt-1 tabular-nums ${isToday ? "text-muted-foreground/60 font-medium" : "text-muted-foreground/30"}`}>
                    {formatDate(day.date).replace(/\s+/g, "\u00a0")}
                  </span>
                )}
              </div>
            );
          })}
        </div>

        {/* Legend */}
        <div className="flex items-center gap-4 mt-2 text-[9px] text-muted-foreground/30">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-sm bg-primary/20" /> Low usage
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-sm bg-primary/60" /> High usage
          </span>
        </div>
      </div>
    </div>
  );
}
