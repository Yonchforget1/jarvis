"use client";

import { useState } from "react";
import { useLearnings } from "@/hooks/use-learnings";
import { LearningsTimeline } from "@/components/dashboard/learnings-timeline";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Search } from "lucide-react";

export default function LearningsPage() {
  const { learnings, loading } = useLearnings();
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null);

  const categories = [...new Set(learnings.map((l) => l.category))];

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
      <div className="p-6 space-y-4">
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-24 rounded-xl" />
        ))}
      </div>
    );
  }

  return (
    <div className="overflow-y-auto h-full p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Learnings</h1>
        <p className="text-sm text-muted-foreground">
          {learnings.length} insights from past tasks
        </p>
      </div>

      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search learnings..."
            className="pl-9"
          />
        </div>
        <div className="flex gap-1.5 flex-wrap">
          <button
            onClick={() => setCategoryFilter(null)}
            className={`rounded-full px-2.5 py-1 text-xs transition-colors ${
              !categoryFilter
                ? "bg-primary/20 text-primary"
                : "bg-white/5 text-muted-foreground hover:bg-white/10"
            }`}
          >
            All
          </button>
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setCategoryFilter(categoryFilter === cat ? null : cat)}
              className={`rounded-full px-2.5 py-1 text-xs transition-colors ${
                categoryFilter === cat
                  ? "bg-primary/20 text-primary"
                  : "bg-white/5 text-muted-foreground hover:bg-white/10"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="rounded-xl border border-white/5 bg-white/[0.02] p-8 text-center">
          <p className="text-sm text-muted-foreground">No learnings match your filters</p>
        </div>
      ) : (
        <LearningsTimeline learnings={filtered} />
      )}
    </div>
  );
}
