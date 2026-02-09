"use client";

import { useState } from "react";
import {
  Folder,
  Terminal,
  Globe,
  Gamepad2,
  Lightbulb,
  Search,
  ChevronDown,
  ChevronRight,
  Wrench,
  Monitor,
  Eye,
} from "lucide-react";
import { useTools } from "@/hooks/use-tools";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import type { ToolInfo } from "@/lib/types";

const CATEGORY_META: Record<
  string,
  { icon: typeof Folder; color: string; bg: string; border: string; label: string }
> = {
  filesystem: {
    icon: Folder,
    color: "text-blue-400",
    bg: "bg-blue-400/10",
    border: "border-l-blue-400/50",
    label: "Filesystem",
  },
  execution: {
    icon: Terminal,
    color: "text-green-400",
    bg: "bg-green-400/10",
    border: "border-l-green-400/50",
    label: "Execution",
  },
  web: {
    icon: Globe,
    color: "text-orange-400",
    bg: "bg-orange-400/10",
    border: "border-l-orange-400/50",
    label: "Web",
  },
  gamedev: {
    icon: Gamepad2,
    color: "text-purple-400",
    bg: "bg-purple-400/10",
    border: "border-l-purple-400/50",
    label: "Game Dev",
  },
  memory: {
    icon: Lightbulb,
    color: "text-yellow-400",
    bg: "bg-yellow-400/10",
    border: "border-l-yellow-400/50",
    label: "Memory",
  },
  computer_use: {
    icon: Monitor,
    color: "text-cyan-400",
    bg: "bg-cyan-400/10",
    border: "border-l-cyan-400/50",
    label: "Computer Use",
  },
  vision: {
    icon: Eye,
    color: "text-pink-400",
    bg: "bg-pink-400/10",
    border: "border-l-pink-400/50",
    label: "Vision",
  },
  other: {
    icon: Wrench,
    color: "text-zinc-400",
    bg: "bg-zinc-400/10",
    border: "border-l-zinc-400/50",
    label: "Other",
  },
};

function ToolCard({ tool }: { tool: ToolInfo }) {
  const [expanded, setExpanded] = useState(false);
  const meta = CATEGORY_META[tool.category] || CATEGORY_META.other;
  const paramCount = Object.keys(tool.parameters?.properties || {}).length;

  return (
    <div
      className={`rounded-xl border border-white/5 border-l-2 ${meta.border} bg-white/[0.02] overflow-hidden transition-all duration-200 hover:border-white/10 hover:bg-white/[0.04]`}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-3 p-4 text-left transition-colors"
      >
        <div className={`flex h-8 w-8 items-center justify-center rounded-lg ${meta.bg} shrink-0`}>
          <meta.icon className={`h-4 w-4 ${meta.color}`} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <p className="text-sm font-medium font-mono">{tool.name}</p>
            {paramCount > 0 && (
              <span className="text-[10px] text-muted-foreground/50 font-mono">
                {paramCount} param{paramCount !== 1 ? "s" : ""}
              </span>
            )}
          </div>
          <p className="text-xs text-muted-foreground/70 truncate mt-0.5">
            {tool.description}
          </p>
        </div>
        {expanded ? (
          <ChevronDown className="h-4 w-4 text-muted-foreground/50 shrink-0" />
        ) : (
          <ChevronRight className="h-4 w-4 text-muted-foreground/50 shrink-0" />
        )}
      </button>
      {expanded && (
        <div className="border-t border-white/5 p-4 animate-fade-in-up">
          <p className="text-sm leading-relaxed mb-3">{tool.description}</p>
          {tool.parameters?.properties &&
            Object.keys(tool.parameters.properties).length > 0 && (
              <div>
                <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground/60 mb-2">
                  Parameters
                </p>
                <div className="space-y-2 bg-black/20 rounded-lg p-3">
                  {Object.entries(tool.parameters.properties).map(
                    ([name, schema]) => {
                      const s = schema as Record<string, string>;
                      const isRequired =
                        tool.parameters.required?.includes(name);
                      return (
                        <div key={name} className="flex items-start gap-2 text-xs">
                          <code className="rounded bg-white/10 px-1.5 py-0.5 font-mono text-primary shrink-0">
                            {name}
                          </code>
                          <span className="text-muted-foreground/60 shrink-0">
                            {s.type || "string"}
                            {isRequired && (
                              <span className="text-red-400 ml-0.5">*</span>
                            )}
                          </span>
                          {s.description && (
                            <span className="text-muted-foreground/50 leading-relaxed">
                              {s.description}
                            </span>
                          )}
                        </div>
                      );
                    },
                  )}
                </div>
              </div>
            )}
        </div>
      )}
    </div>
  );
}

export default function ToolsPage() {
  const { tools, loading } = useTools();
  const [search, setSearch] = useState("");
  const [activeCategory, setActiveCategory] = useState<string | null>(null);

  const filtered = tools.filter((t) => {
    const matchesSearch =
      !search ||
      t.name.toLowerCase().includes(search.toLowerCase()) ||
      t.description.toLowerCase().includes(search.toLowerCase());
    const matchesCategory =
      !activeCategory || (t.category || "other") === activeCategory;
    return matchesSearch && matchesCategory;
  });

  // Get unique categories from actual tools
  const categories = Array.from(
    new Set(tools.map((t) => t.category || "other")),
  ).sort();

  if (loading) {
    return (
      <div className="h-full overflow-y-auto p-4 sm:p-6 space-y-4">
        <Skeleton className="h-10 w-48 rounded-xl" />
        <div className="flex gap-2">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-8 w-24 rounded-full" />
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Skeleton key={i} className="h-20 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto p-4 sm:p-6 space-y-5 pb-20">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Tools</h1>
        <p className="text-sm text-muted-foreground/60 mt-0.5">
          {filtered.length} of {tools.length} professional tools
        </p>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground/50" />
        <Input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search tools by name or description..."
          className="pl-9 h-10 rounded-xl bg-secondary/50 border-white/10"
        />
      </div>

      {/* Category filters */}
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => setActiveCategory(null)}
          className={`rounded-full px-3 py-1.5 text-xs font-medium transition-all duration-200 ${
            !activeCategory
              ? "bg-primary/20 text-primary border border-primary/30"
              : "bg-white/5 text-muted-foreground/70 border border-white/5 hover:bg-white/10"
          }`}
        >
          All ({tools.length})
        </button>
        {categories.map((cat) => {
          const meta = CATEGORY_META[cat] || CATEGORY_META.other;
          const count = tools.filter((t) => (t.category || "other") === cat).length;
          return (
            <button
              key={cat}
              onClick={() =>
                setActiveCategory(activeCategory === cat ? null : cat)
              }
              className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition-all duration-200 ${
                activeCategory === cat
                  ? `${meta.bg} ${meta.color} border border-current/30`
                  : "bg-white/5 text-muted-foreground/70 border border-white/5 hover:bg-white/10"
              }`}
            >
              <meta.icon className="h-3 w-3" />
              {meta.label} ({count})
            </button>
          );
        })}
      </div>

      {/* Tools grid */}
      {filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 animate-fade-in-up">
          <Search className="h-10 w-10 text-muted-foreground/20 mb-3" />
          <p className="text-sm text-muted-foreground">No tools found</p>
          <p className="text-xs text-muted-foreground/50 mt-1">
            Try a different search or filter
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          {filtered.map((tool) => (
            <ToolCard key={tool.name} tool={tool} />
          ))}
        </div>
      )}
    </div>
  );
}
