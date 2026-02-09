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
} from "lucide-react";
import { useTools } from "@/hooks/use-tools";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import type { ToolInfo } from "@/lib/types";

const CATEGORY_META: Record<string, { icon: typeof Folder; color: string; label: string }> = {
  filesystem: { icon: Folder, color: "text-blue-400", label: "Filesystem" },
  execution: { icon: Terminal, color: "text-green-400", label: "Execution" },
  web: { icon: Globe, color: "text-orange-400", label: "Web" },
  gamedev: { icon: Gamepad2, color: "text-purple-400", label: "Game Dev" },
  memory: { icon: Lightbulb, color: "text-yellow-400", label: "Memory" },
  other: { icon: Terminal, color: "text-zinc-400", label: "Other" },
};

function ToolCard({ tool }: { tool: ToolInfo }) {
  const [expanded, setExpanded] = useState(false);
  const meta = CATEGORY_META[tool.category] || CATEGORY_META.other;

  return (
    <div className="rounded-xl border border-white/5 bg-white/[0.02] overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-3 p-4 text-left hover:bg-white/[0.02] transition-colors"
      >
        {expanded ? (
          <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
        ) : (
          <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />
        )}
        <meta.icon className={`h-4 w-4 ${meta.color} shrink-0`} />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium font-mono">{tool.name}</p>
          <p className="text-xs text-muted-foreground truncate">{tool.description}</p>
        </div>
        <Badge variant="secondary" className="text-[10px] shrink-0">
          {meta.label}
        </Badge>
      </button>
      {expanded && (
        <div className="border-t border-white/5 p-4">
          <p className="text-sm mb-3">{tool.description}</p>
          {tool.parameters.properties &&
            Object.keys(tool.parameters.properties).length > 0 && (
              <div>
                <p className="text-xs font-medium text-muted-foreground mb-2">Parameters</p>
                <div className="space-y-1.5">
                  {Object.entries(tool.parameters.properties).map(([name, schema]) => {
                    const s = schema as Record<string, string>;
                    const isRequired = tool.parameters.required?.includes(name);
                    return (
                      <div
                        key={name}
                        className="flex items-start gap-2 text-xs"
                      >
                        <code className="rounded bg-white/5 px-1.5 py-0.5 font-mono text-primary">
                          {name}
                        </code>
                        <span className="text-muted-foreground">
                          {s.type || "string"}
                          {isRequired && (
                            <span className="text-destructive ml-1">*</span>
                          )}
                        </span>
                        {s.description && (
                          <span className="text-muted-foreground">
                            - {s.description}
                          </span>
                        )}
                      </div>
                    );
                  })}
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

  const filtered = tools.filter(
    (t) =>
      t.name.toLowerCase().includes(search.toLowerCase()) ||
      t.description.toLowerCase().includes(search.toLowerCase()),
  );

  // Group by category
  const grouped: Record<string, ToolInfo[]> = {};
  for (const tool of filtered) {
    const cat = tool.category || "other";
    if (!grouped[cat]) grouped[cat] = [];
    grouped[cat].push(tool);
  }

  if (loading) {
    return (
      <div className="p-6 space-y-4">
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-16 rounded-xl" />
        ))}
      </div>
    );
  }

  return (
    <div className="overflow-y-auto h-full p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Tools</h1>
        <p className="text-sm text-muted-foreground">
          {tools.length} professional tools available
        </p>
      </div>

      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search tools..."
          className="pl-9"
        />
      </div>

      <div className="space-y-6">
        {Object.entries(grouped).map(([category, categoryTools]) => {
          const meta = CATEGORY_META[category] || CATEGORY_META.other;
          return (
            <div key={category}>
              <div className="flex items-center gap-2 mb-3">
                <meta.icon className={`h-4 w-4 ${meta.color}`} />
                <h3 className="text-sm font-semibold">{meta.label}</h3>
                <span className="text-xs text-muted-foreground">
                  ({categoryTools.length})
                </span>
              </div>
              <div className="space-y-2">
                {categoryTools.map((tool) => (
                  <ToolCard key={tool.name} tool={tool} />
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
