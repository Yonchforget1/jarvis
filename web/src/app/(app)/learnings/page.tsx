"use client";

import { useState } from "react";
import { useLearnings } from "@/hooks/use-learnings";
import { LearningsTimeline } from "@/components/dashboard/learnings-timeline";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Search, Brain } from "lucide-react";
import { ErrorState } from "@/components/ui/error-state";

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
  const { learnings, loading, error, refetch } = useLearnings();
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null);

  const categories = [...new Set(learnings.map((l) => l.category))].sort();

  const filtered = learnings.filter((l) => {
    const matchesSearch =
      !search ||
      l.insight.toLowerCase().includes(search.toLowerCase()) ||
      l.context.toLowerCase().includes(search.toLowerCase()) ||
      l.task_description.toLowerCase().includes(search.toLowerCase());
    const matchesCategory = !categoryFilter || l.category === categoryFilter;
    return matchesSearch && matchesCategory;
  });

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
    <div className="h-full overflow-y-auto p-4 sm:p-6 space-y-5 pb-20">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Learnings</h1>
          <p className="text-sm text-muted-foreground/60 mt-0.5">
            {filtered.length} of {learnings.length} insights from past tasks
          </p>
        </div>
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-purple-400/10">
          <Brain className="h-5 w-5 text-purple-400" />
        </div>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground/50" />
        <Input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search insights, context, or tasks..."
          className="pl-9 h-10 rounded-xl bg-secondary/50 border-border"
        />
      </div>

      {/* Category filters */}
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => setCategoryFilter(null)}
          className={`rounded-full px-3 py-1.5 text-xs font-medium transition-all duration-200 ${
            !categoryFilter
              ? "bg-primary/20 text-primary border border-primary/30"
              : "bg-muted text-muted-foreground/70 border border-border/50 hover:bg-muted/80"
          }`}
        >
          All ({learnings.length})
        </button>
        {categories.map((cat) => {
          const style = getCatStyle(cat);
          const count = learnings.filter((l) => l.category === cat).length;
          return (
            <button
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
      {filtered.length === 0 ? (
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
  );
}
