import { Brain } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { LearningEntry } from "@/lib/types";

const CATEGORY_COLORS: Record<string, string> = {
  game_dev: "bg-purple-500/10 text-purple-400 border-purple-500/20",
  workflow: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  error_handling: "bg-red-500/10 text-red-400 border-red-500/20",
  tool_usage: "bg-green-500/10 text-green-400 border-green-500/20",
  coding: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
  general: "bg-zinc-500/10 text-zinc-400 border-zinc-500/20",
  implement: "bg-cyan-500/10 text-cyan-400 border-cyan-500/20",
  database: "bg-orange-500/10 text-orange-400 border-orange-500/20",
};

function getCategoryColor(category: string): string {
  return CATEGORY_COLORS[category] || CATEGORY_COLORS.general;
}

export function LearningsTimeline({ learnings }: { learnings: LearningEntry[] }) {
  if (learnings.length === 0) {
    return (
      <div className="rounded-2xl border border-border/50 bg-card/50 p-8 text-center animate-fade-in-up">
        <Brain className="mx-auto mb-3 h-8 w-8 text-muted-foreground/30" />
        <p className="text-sm text-muted-foreground">No learnings yet</p>
        <p className="mt-1 text-xs text-muted-foreground/50">
          Jarvis will learn and improve with each task
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {[...learnings].reverse().map((entry, i) => (
        <div
          key={`${entry.timestamp}-${i}`}
          className="group rounded-2xl border border-border/50 bg-card/50 p-4 transition-all duration-200 hover:border-border hover:bg-card/80 animate-fade-in-up"
          style={{ animationDelay: `${i * 0.05}s` }}
        >
          <div className="flex items-center gap-2 mb-2">
            <Badge
              variant="outline"
              className={`text-[10px] border ${getCategoryColor(entry.category)}`}
            >
              {entry.category}
            </Badge>
            <span className="text-[10px] text-muted-foreground/50">
              {new Date(entry.timestamp).toLocaleDateString(undefined, {
                month: "short",
                day: "numeric",
                hour: "2-digit",
                minute: "2-digit",
              })}
            </span>
          </div>
          <p className="text-sm leading-relaxed">{entry.insight}</p>
          {entry.context && (
            <p className="mt-2 text-xs text-muted-foreground/60 leading-relaxed">
              {entry.context}
            </p>
          )}
          {entry.task_description && (
            <p className="mt-1 text-[10px] text-muted-foreground/40 italic">
              Task: {entry.task_description}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}
