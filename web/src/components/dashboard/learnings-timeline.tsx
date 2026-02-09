import { Badge } from "@/components/ui/badge";
import type { LearningEntry } from "@/lib/types";

const CATEGORY_COLORS: Record<string, string> = {
  game_dev: "bg-purple-500/10 text-purple-400",
  workflow: "bg-blue-500/10 text-blue-400",
  error_handling: "bg-red-500/10 text-red-400",
  tool_usage: "bg-green-500/10 text-green-400",
  coding: "bg-yellow-500/10 text-yellow-400",
  general: "bg-zinc-500/10 text-zinc-400",
};

export function LearningsTimeline({ learnings }: { learnings: LearningEntry[] }) {
  if (learnings.length === 0) {
    return (
      <div className="rounded-xl border border-white/5 bg-white/[0.02] p-8 text-center">
        <p className="text-sm text-muted-foreground">No learnings yet</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {[...learnings].reverse().map((entry, i) => (
        <div
          key={i}
          className="rounded-xl border border-white/5 bg-white/[0.02] p-4"
        >
          <div className="flex items-center gap-2 mb-2">
            <Badge
              variant="secondary"
              className={`text-[10px] ${CATEGORY_COLORS[entry.category] || CATEGORY_COLORS.general}`}
            >
              {entry.category}
            </Badge>
            <span className="text-[10px] text-muted-foreground">
              {new Date(entry.timestamp).toLocaleDateString()}
            </span>
          </div>
          <p className="text-sm">{entry.insight}</p>
          {entry.context && (
            <p className="mt-2 text-xs text-muted-foreground">
              Context: {entry.context}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}
