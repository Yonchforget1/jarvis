"use client";

import { useState, useMemo, useEffect, useRef } from "react";
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
  ChevronsUpDown,
  ArrowUpDown,
  Copy,
  Check,
} from "lucide-react";
import { useTools } from "@/hooks/use-tools";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { ErrorBoundary } from "@/components/error-boundary";
import { api } from "@/lib/api";
import type { ToolInfo } from "@/lib/types";

interface ToolStat {
  name: string;
  calls: number;
  errors: number;
  avg_ms: number;
}

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

// Format a JSON schema type for display
function formatParamType(schema: Record<string, unknown>): string {
  const type = schema.type as string | undefined;
  if (schema.enum) return `enum(${(schema.enum as string[]).join("|")})`;
  if (type === "array" && schema.items) {
    const items = schema.items as Record<string, unknown>;
    return `${items.type || "any"}[]`;
  }
  return type || "string";
}

function ToolCard({ tool, forceExpanded, usage }: { tool: ToolInfo; forceExpanded?: boolean; usage?: ToolStat }) {
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);
  const isExpanded = forceExpanded !== undefined ? forceExpanded : expanded;
  const meta = CATEGORY_META[tool.category] || CATEGORY_META.other;
  const paramCount = Object.keys(tool.parameters?.properties || {}).length;

  const copyName = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(tool.name).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };

  return (
    <div
      className={`rounded-xl border border-border/50 border-l-2 ${meta.border} bg-card/50 overflow-hidden transition-all duration-200 hover:border-border hover:bg-card/80`}
    >
      <button
        onClick={() => setExpanded(!isExpanded)}
        className="flex w-full items-center gap-3 p-4 text-left transition-colors"
        aria-expanded={isExpanded}
        aria-label={`${isExpanded ? "Collapse" : "Expand"} ${tool.name} details`}
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
            {usage && usage.calls > 0 && (
              <span className="text-[10px] font-medium text-primary/70 bg-primary/10 rounded-full px-1.5 py-0.5 tabular-nums">
                {usage.calls} call{usage.calls !== 1 ? "s" : ""}
              </span>
            )}
          </div>
          <p className="text-xs text-muted-foreground/70 truncate mt-0.5">
            {tool.description}
          </p>
        </div>
        {isExpanded ? (
          <ChevronDown className="h-4 w-4 text-muted-foreground/50 shrink-0" />
        ) : (
          <ChevronRight className="h-4 w-4 text-muted-foreground/50 shrink-0" />
        )}
      </button>
      {isExpanded && (
        <div className="border-t border-border/50 p-4 animate-fade-in-up">
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm leading-relaxed">{tool.description}</p>
            <button
              onClick={copyName}
              className="flex items-center gap-1 shrink-0 ml-2 rounded-md border border-border/50 bg-muted/30 px-2 py-1 text-[10px] text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
              title="Copy tool name"
            >
              {copied ? <Check className="h-3 w-3 text-green-400" /> : <Copy className="h-3 w-3" />}
              {copied ? "Copied" : "Copy name"}
            </button>
          </div>
          {usage && usage.calls > 0 && (
            <div className="flex items-center gap-4 mb-3 text-[10px] text-muted-foreground/60 bg-muted/30 rounded-lg px-3 py-2">
              <span className="flex items-center gap-1">
                <span className="font-medium text-foreground/80">{usage.calls}</span> calls
              </span>
              {usage.errors > 0 && (
                <span className="flex items-center gap-1 text-red-400/70">
                  <span className="font-medium">{usage.errors}</span> errors
                </span>
              )}
              <span className="flex items-center gap-1">
                avg <span className="font-medium text-foreground/80">{usage.avg_ms}ms</span>
              </span>
            </div>
          )}
          {tool.parameters?.properties &&
            Object.keys(tool.parameters.properties).length > 0 && (
              <div>
                <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground/60 mb-2">
                  Parameters
                </p>
                <div className="space-y-2 bg-muted dark:bg-black/20 rounded-lg p-3">
                  {Object.entries(tool.parameters.properties).map(
                    ([name, schema]) => {
                      const s = schema as Record<string, unknown>;
                      const isRequired =
                        tool.parameters.required?.includes(name);
                      return (
                        <div key={name} className="flex items-start gap-2 text-xs">
                          <code className="rounded bg-primary/10 px-1.5 py-0.5 font-mono text-primary shrink-0">
                            {name}
                          </code>
                          <span className="text-muted-foreground/60 shrink-0 font-mono text-[10px]">
                            {formatParamType(s)}
                            {isRequired && (
                              <span className="text-red-400 ml-0.5">*</span>
                            )}
                          </span>
                          {typeof s.description === "string" && s.description && (
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
  const { tools, loading, error, refetch } = useTools();
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const searchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [activeCategory, setActiveCategory] = useState<string | null>(null);
  const [allExpanded, setAllExpanded] = useState<boolean | undefined>(undefined);
  const [sortBy, setSortBy] = useState<"name" | "calls" | "errors" | "speed">("name");
  const [toolStats, setToolStats] = useState<Record<string, ToolStat>>({});

  // Fetch tool usage stats
  useEffect(() => {
    api.get<{ tools: ToolStat[] }>("/api/stats/tools")
      .then((res) => {
        const map: Record<string, ToolStat> = {};
        for (const s of res.tools) map[s.name] = s;
        setToolStats(map);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    searchTimerRef.current = setTimeout(() => setDebouncedSearch(search), 200);
    return () => { if (searchTimerRef.current) clearTimeout(searchTimerRef.current); };
  }, [search]);

  const filtered = useMemo(() => {
    const list = tools.filter((t) => {
      const matchesSearch =
        !debouncedSearch ||
        t.name.toLowerCase().includes(debouncedSearch.toLowerCase()) ||
        t.description.toLowerCase().includes(debouncedSearch.toLowerCase());
      const matchesCategory =
        !activeCategory || (t.category || "other") === activeCategory;
      return matchesSearch && matchesCategory;
    });
    if (sortBy === "name") return list.sort((a, b) => a.name.localeCompare(b.name));
    if (sortBy === "calls") return list.sort((a, b) => (toolStats[b.name]?.calls || 0) - (toolStats[a.name]?.calls || 0));
    if (sortBy === "errors") return list.sort((a, b) => (toolStats[b.name]?.errors || 0) - (toolStats[a.name]?.errors || 0));
    if (sortBy === "speed") return list.sort((a, b) => (toolStats[a.name]?.avg_ms || 9999) - (toolStats[b.name]?.avg_ms || 9999));
    return list;
  }, [tools, debouncedSearch, activeCategory, sortBy, toolStats]);

  // Get unique categories from actual tools
  const categories = useMemo(
    () => Array.from(new Set(tools.map((t) => t.category || "other"))).sort(),
    [tools],
  );

  if (loading) {
    return (
      <div className="h-full overflow-y-auto p-4 sm:p-6 space-y-4">
        <Skeleton className="h-10 w-48 rounded-xl" />
        <div className="flex gap-2">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-8 w-24 rounded-full" />
          ))}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Skeleton key={i} className="h-20 rounded-xl" />
          ))}
        </div>
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
          <h1 className="text-2xl font-bold tracking-tight">Tools</h1>
          <p className="text-sm text-muted-foreground/60 mt-0.5" role="status" aria-live="polite" aria-atomic="true">
            {filtered.length} of {tools.length} professional tools
          </p>
        </div>
        {tools.length > 0 && (
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1 rounded-lg border border-border/50 bg-muted/30 p-0.5">
              <ArrowUpDown className="h-3 w-3 text-muted-foreground/50 ml-1.5" />
              {(["name", "calls", "errors", "speed"] as const).map((s) => (
                <button
                  key={s}
                  onClick={() => setSortBy(s)}
                  className={`rounded-md px-2 py-1 text-[10px] font-medium transition-colors ${
                    sortBy === s
                      ? "bg-background text-foreground shadow-sm"
                      : "text-muted-foreground/60 hover:text-foreground"
                  }`}
                >
                  {s === "name" ? "A-Z" : s === "calls" ? "Most Used" : s === "errors" ? "Errors" : "Fastest"}
                </button>
              ))}
            </div>
            <button
              onClick={() => setAllExpanded(allExpanded === true ? undefined : true)}
              className="flex items-center gap-1.5 rounded-lg border border-border/50 bg-muted/30 px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
            >
              <ChevronsUpDown className="h-3.5 w-3.5" />
              {allExpanded ? "Collapse All" : "Expand All"}
            </button>
          </div>
        )}
      </div>

      {/* Search */}
      <div role="search" className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground/50" />
        <Input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search tools by name or description..."
          className="pl-9 h-10 rounded-xl bg-secondary/50 border-border"
          aria-label="Search tools by name or description"
          aria-controls="tools-results"
        />
      </div>

      {/* Category filters */}
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => setActiveCategory(null)}
          className={`rounded-full px-3 py-1.5 text-xs font-medium transition-all duration-200 hover:scale-[1.03] active:scale-[0.97] ${
            !activeCategory
              ? "bg-primary/20 text-primary border border-primary/30"
              : "bg-muted text-muted-foreground/70 border border-border/50 hover:bg-muted/80"
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
              className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition-all duration-200 hover:scale-[1.03] active:scale-[0.97] ${
                activeCategory === cat
                  ? `${meta.bg} ${meta.color} border border-current/30`
                  : "bg-muted text-muted-foreground/70 border border-border/50 hover:bg-muted/80"
              }`}
            >
              <meta.icon className="h-3 w-3" />
              {meta.label} ({count})
            </button>
          );
        })}
      </div>

      {/* Tools grid */}
      {tools.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 px-4 animate-fade-in-up">
          <div className="relative mb-6">
            <div className="absolute -inset-3 rounded-3xl bg-gradient-to-r from-blue-500/10 via-green-500/10 to-orange-500/10 blur-xl animate-glow-pulse" />
            <div className="relative flex h-16 w-16 items-center justify-center rounded-2xl bg-card border border-border/50">
              <Wrench className="h-8 w-8 text-blue-400" />
            </div>
          </div>
          <h3 className="text-lg font-semibold mb-1 text-center">No tools loaded</h3>
          <p className="text-sm text-muted-foreground/60 max-w-sm text-center leading-relaxed">
            Tools will appear here once the API server is connected and tools are registered.
          </p>
        </div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 animate-fade-in-up">
          <Search className="h-10 w-10 text-muted-foreground/20 mb-3" />
          <p className="text-sm text-muted-foreground">No tools found</p>
          <p className="text-xs text-muted-foreground/50 mt-1">
            {debouncedSearch ? `"${debouncedSearch}" matched 0 of ${tools.length} tools` : `No tools in this category (${tools.length} total)`}
          </p>
        </div>
      ) : (
        <div id="tools-results" className="grid grid-cols-1 md:grid-cols-2 gap-3" role="region" aria-label="Tools list">
          {filtered.map((tool) => (
            <ToolCard key={tool.name} tool={tool} forceExpanded={allExpanded} usage={toolStats[tool.name]} />
          ))}
        </div>
      )}
      </div>
    </div>
    </ErrorBoundary>
  );
}
