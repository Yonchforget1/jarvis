"use client";

import { useState, useMemo, useCallback } from "react";
import { useLearnings } from "@/hooks/use-learnings";
import { LearningsTimeline } from "@/components/dashboard/learnings-timeline";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Search, Brain, Download, ArrowUpDown, TrendingUp, Calendar, Tag } from "lucide-react";
import { ErrorState } from "@/components/ui/error-state";
import { ErrorBoundary } from "@/components/error-boundary";

const CATEGORY_COLORS: Record<string, { bg: string; text: string }> = {
  game_dev: { bg: "bg-purple-500/10", text: "text-purple-400" },
  workflow: { bg: "bg-blue-500/10", text: "text-blue-400" },
  error_handling: { bg: "bg-red-500/10", text: "text-red-400" },
  tool_usage: { bg: "bg-green-500/10", text: "text-green-400" },
  coding: { bg: "bg-yellow-500/10", text: "text-yellow-400" },
  general: { bg: "bg-zinc-500/10", text: "text-zinc-400" },
  implement: { bg: "bg-cyan-500/10", text: "text-cyan-400" },
  database: { bg: "bg-orange-500/10", text: "text-orange-400" },
};

function getCatStyle(cat: string) {
  return CATEGORY_COLORS[cat] || CATEGORY_COLORS.general;
}

export default function LearningsPage() {
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null);
  const [sortOrder, setSortOrder] = useState<"newest" | "oldest">("newest");

  // Server-side search, sort, and filtering via hook
  const { learnings, total, loading, error, refetch } = useLearnings({
    search: search || undefined,
    sort: sortOrder,
    category: categoryFilter || undefined,
    pageSize: 200,
  });

  // Also fetch unfiltered to get all categories
  const { learnings: allLearnings } = useLearnings({ pageSize: 200 });

  const categories = useMemo(
    () => [...new Set(allLearnings.map((l) => l.category))].sort(),
    [allLearnings],
  );

  const filtered = learnings;

  const handleExport = useCallback(() => {
    const markdown = filtered
      .map(
        (l) =>
          `### ${l.category}\n> ${l.insight}\n\n${l.context ? `_Context:_ ${l.context}\n` : ""}${l.task_description ? `_Task:_ ${l.task_description}\n` : ""}\n_${new Date(l.timestamp).toLocaleString()}_\n\n---`,
      )
      .join("\n\n");
    const filterNote = (search || categoryFilter)
      ? `\n> Filtered: ${filtered.length} of ${learnings.length} learnings${categoryFilter ? ` (category: ${categoryFilter})` : ""}${search ? ` (search: "${search}")` : ""}\n`
      : `\n> ${learnings.length} total learnings\n`;
    const blob = new Blob([`# JARVIS Learnings Export\n${filterNote}\n${markdown}`], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `jarvis-learnings-${new Date().toISOString().slice(0, 10)}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [filtered, learnings.length, search, categoryFilter]);

  if (loading) {
    return (
      <div className="h-full overflow-y-auto p-4 sm:p-6 space-y-4">
        <Skeleton className="h-10 w-48 rounded-xl" />
        <div className="flex gap-2">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-8 w-20 rounded-full" />
          ))}
        </div>
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-24 rounded-2xl" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full overflow-y-auto p-4 sm:p-6">
        <ErrorState message={error} onRetry={refetch} />
      </div>
    );
  }

  return (
    <ErrorBoundary>
    <div className="h-full overflow-y-auto p-4 sm:p-6 pb-20">
      <div className="mx-auto max-w-6xl space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Learnings</h1>
          <p className="text-sm text-muted-foreground/60 mt-0.5">
            {filtered.length} of {total} insights from past tasks
          </p>
        </div>
        <div className="flex items-center gap-2">
          {learnings.length > 0 && (
            <>
              <button
                onClick={() => setSortOrder(sortOrder === "newest" ? "oldest" : "newest")}
                className="flex items-center gap-1.5 rounded-lg border border-border/50 bg-muted/30 px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                title={`Sort by ${sortOrder === "newest" ? "oldest" : "newest"} first`}
              >
                <ArrowUpDown className="h-3.5 w-3.5" />
                {sortOrder === "newest" ? "Newest" : "Oldest"}
              </button>
              <button
                onClick={handleExport}
                className="flex items-center gap-1.5 rounded-lg border border-border/50 bg-muted/30 px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
              >
                <Download className="h-3.5 w-3.5" />
                Export
              </button>
            </>
          )}
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-purple-400/10">
            <Brain className="h-5 w-5 text-purple-400" />
          </div>
        </div>
      </div>

      {/* Quick Stats */}
      {total > 0 && (
        <div className="grid grid-cols-3 gap-3">
          <div className="rounded-xl border border-border/50 bg-card/30 p-3 flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-purple-400/10">
              <TrendingUp className="h-4 w-4 text-purple-400" />
            </div>
            <div>
              <p className="text-lg font-bold tabular-nums">{total}</p>
              <p className="text-[10px] text-muted-foreground/50">Total Insights</p>
            </div>
          </div>
          <div className="rounded-xl border border-border/50 bg-card/30 p-3 flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-cyan-400/10">
              <Tag className="h-4 w-4 text-cyan-400" />
            </div>
            <div>
              <p className="text-lg font-bold tabular-nums">{categories.length}</p>
              <p className="text-[10px] text-muted-foreground/50">Categories</p>
            </div>
          </div>
          <div className="rounded-xl border border-border/50 bg-card/30 p-3 flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-yellow-400/10">
              <Calendar className="h-4 w-4 text-yellow-400" />
            </div>
            <div>
              <p className="text-lg font-bold tabular-nums">
                {allLearnings.length > 0
                  ? new Date(allLearnings[allLearnings.length - 1]?.timestamp || Date.now()).toLocaleDateString(undefined, { month: "short", day: "numeric" })
                  : "—"}
              </p>
              <p className="text-[10px] text-muted-foreground/50">Latest Entry</p>
            </div>
          </div>
        </div>
      )}

      {/* Search */}
      <div role="search" className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground/50" />
        <Input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search insights, context, or tasks..."
          className="pl-9 h-10 rounded-xl bg-secondary/50 border-border"
        />
      </div>

      {/* Category filters */}
      <div role="tablist" aria-label="Filter by category" className="flex flex-wrap gap-2">
        <button
          role="tab"
          aria-selected={!categoryFilter}
          onClick={() => setCategoryFilter(null)}
          className={`rounded-full px-3 py-1.5 text-xs font-medium transition-all duration-200 ${
            !categoryFilter
              ? "bg-primary/20 text-primary border border-primary/30"
              : "bg-muted text-muted-foreground/70 border border-border/50 hover:bg-muted/80"
          }`}
        >
          All ({total})
        </button>
        {categories.map((cat) => {
          const style = getCatStyle(cat);
          const count = allLearnings.filter((l) => l.category === cat).length;
          return (
            <button
              role="tab"
              aria-selected={categoryFilter === cat}
              key={cat}
              onClick={() =>
                setCategoryFilter(categoryFilter === cat ? null : cat)
              }
              className={`rounded-full px-3 py-1.5 text-xs font-medium transition-all duration-200 ${
                categoryFilter === cat
                  ? `${style.bg} ${style.text} border border-current/30`
                  : "bg-muted text-muted-foreground/70 border border-border/50 hover:bg-muted/80"
              }`}
            >
              {cat.replace(/_/g, " ")} ({count})
            </button>
          );
        })}
      </div>

      {/* Timeline */}
      {learnings.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 animate-fade-in-up">
          <div className="relative mb-6">
            <div className="absolute -inset-3 rounded-3xl bg-gradient-to-r from-purple-500/10 via-cyan-500/10 to-yellow-500/10 blur-xl animate-glow-pulse" />
            <div className="relative flex h-16 w-16 items-center justify-center rounded-2xl bg-card border border-border/50">
              <Brain className="h-8 w-8 text-purple-400" />
            </div>
          </div>
          <h3 className="text-lg font-semibold mb-1">No learnings yet</h3>
          <p className="text-sm text-muted-foreground/60 max-w-xs text-center leading-relaxed">
            As JARVIS completes tasks, it saves insights here. Start a conversation to build your knowledge base.
          </p>
        </div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 animate-fade-in-up">
          <Brain className="h-10 w-10 text-muted-foreground/20 mb-3" />
          <p className="text-sm text-muted-foreground">No learnings match your filters</p>
          <p className="text-xs text-muted-foreground/50 mt-1">
            Try a different search or category
          </p>
        </div>
      ) : (
        <LearningsTimeline learnings={filtered} />
      )}
      </div>
    </div>
    </ErrorBoundary>
  );
}
