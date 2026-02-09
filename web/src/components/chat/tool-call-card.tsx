"use client";

import { useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  Folder,
  Terminal,
  Globe,
  Gamepad2,
  Brain,
  Wrench,
  CheckCircle2,
  Loader2,
  Copy,
  Check,
} from "lucide-react";
import type { ToolCallDetail } from "@/lib/types";

const TOOL_META: Record<string, { icon: typeof Wrench; color: string; bg: string }> = {
  read_file: { icon: Folder, color: "text-blue-400", bg: "bg-blue-400/10" },
  write_file: { icon: Folder, color: "text-blue-400", bg: "bg-blue-400/10" },
  list_directory: { icon: Folder, color: "text-blue-400", bg: "bg-blue-400/10" },
  delete_path: { icon: Folder, color: "text-blue-400", bg: "bg-blue-400/10" },
  move_copy: { icon: Folder, color: "text-blue-400", bg: "bg-blue-400/10" },
  make_directory: { icon: Folder, color: "text-blue-400", bg: "bg-blue-400/10" },
  file_info: { icon: Folder, color: "text-blue-400", bg: "bg-blue-400/10" },
  run_python: { icon: Terminal, color: "text-green-400", bg: "bg-green-400/10" },
  run_shell: { icon: Terminal, color: "text-green-400", bg: "bg-green-400/10" },
  search_web: { icon: Globe, color: "text-orange-400", bg: "bg-orange-400/10" },
  fetch_url: { icon: Globe, color: "text-orange-400", bg: "bg-orange-400/10" },
  create_game_project: { icon: Gamepad2, color: "text-purple-400", bg: "bg-purple-400/10" },
  generate_game_asset: { icon: Gamepad2, color: "text-purple-400", bg: "bg-purple-400/10" },
  reflect_on_task: { icon: Brain, color: "text-yellow-400", bg: "bg-yellow-400/10" },
  recall_learnings: { icon: Brain, color: "text-yellow-400", bg: "bg-yellow-400/10" },
  self_improve: { icon: Brain, color: "text-yellow-400", bg: "bg-yellow-400/10" },
};

const DEFAULT_META = { icon: Wrench, color: "text-muted-foreground", bg: "bg-white/5" };

export function ToolCallCard({ call }: { call: ToolCallDetail }) {
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);
  const meta = TOOL_META[call.name] || DEFAULT_META;
  const Icon = meta.icon;

  const handleCopyResult = () => {
    navigator.clipboard.writeText(call.result);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const argsSummary = Object.entries(call.args)
    .map(([k, v]) => {
      const val = typeof v === "string" ? v : JSON.stringify(v);
      return `${k}: ${val.length > 40 ? val.slice(0, 40) + "..." : val}`;
    })
    .join(", ");

  return (
    <div className="rounded-xl border border-white/5 bg-white/[0.02] overflow-hidden transition-all duration-200 hover:border-white/10 animate-scale-in">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-2.5 px-3 py-2.5 text-left text-sm hover:bg-white/[0.03] transition-colors"
      >
        <div className="flex items-center gap-2 shrink-0">
          {expanded ? (
            <ChevronDown className="h-3.5 w-3.5 text-muted-foreground transition-transform" />
          ) : (
            <ChevronRight className="h-3.5 w-3.5 text-muted-foreground transition-transform" />
          )}
          <div className={`flex h-5 w-5 items-center justify-center rounded ${meta.bg}`}>
            <Icon className={`h-3 w-3 ${meta.color}`} />
          </div>
        </div>
        <span className={`font-mono text-xs font-medium ${meta.color}`}>
          {call.name}
        </span>
        {argsSummary && (
          <span className="text-xs text-muted-foreground/60 truncate">
            {argsSummary}
          </span>
        )}
        {call.result ? (
          <CheckCircle2 className="ml-auto h-3.5 w-3.5 text-green-500/60 shrink-0" />
        ) : (
          <Loader2 className="ml-auto h-3.5 w-3.5 text-primary/60 shrink-0 animate-spin" />
        )}
      </button>

      {expanded && (
        <div className="border-t border-white/5 animate-fade-in-up">
          {/* Arguments */}
          {Object.keys(call.args).length > 0 && (
            <div className="px-3 pt-2.5 pb-1.5">
              <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground/60 mb-1.5">
                Arguments
              </p>
              <pre className="text-xs bg-black/30 rounded-lg p-2.5 overflow-x-auto text-zinc-300 font-mono leading-relaxed">
                {JSON.stringify(call.args, null, 2)}
              </pre>
            </div>
          )}

          {/* Result */}
          <div className="px-3 pt-1.5 pb-2.5">
            <div className="flex items-center justify-between mb-1.5">
              <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground/60">
                Result
              </p>
              <button
                onClick={handleCopyResult}
                className="flex items-center gap-1 text-[10px] text-muted-foreground/50 hover:text-muted-foreground transition-colors"
              >
                {copied ? (
                  <>
                    <Check className="h-3 w-3 text-green-400" />
                    <span className="text-green-400">Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="h-3 w-3" />
                    Copy
                  </>
                )}
              </button>
            </div>
            <pre className="text-xs bg-black/30 rounded-lg p-2.5 overflow-x-auto text-zinc-300 max-h-56 overflow-y-auto font-mono leading-relaxed scrollbar-thin">
              {call.result}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
