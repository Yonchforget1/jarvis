"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, Wrench } from "lucide-react";
import type { ToolCallDetail } from "@/lib/types";

const CATEGORY_COLORS: Record<string, string> = {
  read_file: "text-blue-400",
  write_file: "text-blue-400",
  list_directory: "text-blue-400",
  delete_path: "text-blue-400",
  move_copy: "text-blue-400",
  make_directory: "text-blue-400",
  file_info: "text-blue-400",
  run_python: "text-green-400",
  run_shell: "text-green-400",
  search_web: "text-orange-400",
  fetch_url: "text-orange-400",
  create_game_project: "text-purple-400",
  generate_game_asset: "text-purple-400",
  reflect_on_task: "text-yellow-400",
  recall_learnings: "text-yellow-400",
  self_improve: "text-yellow-400",
};

export function ToolCallCard({ call }: { call: ToolCallDetail }) {
  const [expanded, setExpanded] = useState(false);
  const color = CATEGORY_COLORS[call.name] || "text-muted-foreground";

  return (
    <div className="my-2 rounded-xl border border-white/5 bg-white/[0.02] overflow-hidden animate-fade-in-up">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-white/5 transition-colors"
      >
        {expanded ? (
          <ChevronDown className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
        ) : (
          <ChevronRight className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
        )}
        <Wrench className={`h-3.5 w-3.5 ${color} shrink-0`} />
        <span className={`font-mono text-xs ${color}`}>{call.name}</span>
        <span className="text-xs text-muted-foreground truncate">
          {Object.keys(call.args).length > 0 &&
            `(${Object.entries(call.args)
              .map(([k, v]) => `${k}: ${JSON.stringify(v).slice(0, 30)}`)
              .join(", ")})`}
        </span>
      </button>
      {expanded && (
        <div className="border-t border-white/5 px-3 py-2 space-y-2">
          <div>
            <p className="text-xs font-medium text-muted-foreground mb-1">Arguments</p>
            <pre className="text-xs bg-black/30 rounded-lg p-2 overflow-x-auto text-zinc-300">
              {JSON.stringify(call.args, null, 2)}
            </pre>
          </div>
          <div>
            <p className="text-xs font-medium text-muted-foreground mb-1">Result</p>
            <pre className="text-xs bg-black/30 rounded-lg p-2 overflow-x-auto text-zinc-300 max-h-48 overflow-y-auto">
              {call.result}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
