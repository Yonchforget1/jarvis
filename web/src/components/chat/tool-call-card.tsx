"use client";

import { useState, useMemo, useEffect, useRef } from "react";
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
  XCircle,
  Monitor,
  FileText,
  Clock,
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
  create_godot_project: { icon: Gamepad2, color: "text-purple-400", bg: "bg-purple-400/10" },
  generate_game_asset: { icon: Gamepad2, color: "text-purple-400", bg: "bg-purple-400/10" },
  reflect_on_task: { icon: Brain, color: "text-yellow-400", bg: "bg-yellow-400/10" },
  recall_learnings: { icon: Brain, color: "text-yellow-400", bg: "bg-yellow-400/10" },
  self_improve: { icon: Brain, color: "text-yellow-400", bg: "bg-yellow-400/10" },
  screenshot: { icon: Monitor, color: "text-cyan-400", bg: "bg-cyan-400/10" },
  create_pdf: { icon: FileText, color: "text-pink-400", bg: "bg-pink-400/10" },
  create_docx: { icon: FileText, color: "text-pink-400", bg: "bg-pink-400/10" },
};

const DEFAULT_META = { icon: Wrench, color: "text-muted-foreground", bg: "bg-muted" };

function getResultPreview(result: string): { preview: string; isError: boolean } {
  if (!result) return { preview: "", isError: false };
  const lower = result.toLowerCase();
  const isError = lower.startsWith("error") || lower.includes("traceback") || lower.includes("exception:");
  const firstLine = result.split("\n")[0].trim();
  const preview = firstLine.length > 80 ? firstLine.slice(0, 77) + "..." : firstLine;
  return { preview, isError };
}

export function ToolCallCard({ call }: { call: ToolCallDetail }) {
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const startTimeRef = useRef(Date.now());
  const frozenTimeRef = useRef<number | null>(null);
  const meta = TOOL_META[call.name] || DEFAULT_META;
  const Icon = meta.icon;

  // Timer: tick every 100ms while running, freeze when result arrives
  useEffect(() => {
    if (call.result) {
      if (frozenTimeRef.current === null) {
        frozenTimeRef.current = Date.now() - startTimeRef.current;
        setElapsed(frozenTimeRef.current);
      }
      return;
    }
    const timer = setInterval(() => {
      setElapsed(Date.now() - startTimeRef.current);
    }, 100);
    return () => clearInterval(timer);
  }, [call.result]);

  const elapsedLabel = frozenTimeRef.current !== null
    ? frozenTimeRef.current < 1000
      ? `${frozenTimeRef.current}ms`
      : `${(frozenTimeRef.current / 1000).toFixed(1)}s`
    : elapsed < 1000
      ? `${elapsed}ms`
      : `${(elapsed / 1000).toFixed(1)}s`;

  const handleCopyResult = () => {
    navigator.clipboard.writeText(call.result);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const argsSummary = useMemo(() => {
    return Object.entries(call.args)
      .map(([k, v]) => {
        const val = typeof v === "string" ? v : JSON.stringify(v);
        return `${k}: ${val.length > 40 ? val.slice(0, 40) + "..." : val}`;
      })
      .join(", ");
  }, [call.args]);

  const { preview: resultPreview, isError: isResultError } = useMemo(
    () => getResultPreview(call.result),
    [call.result],
  );

  const isRunning = !call.result;
  const resultLines = call.result ? call.result.split("\n").length : 0;

  return (
    <div
      className={`rounded-xl border overflow-hidden transition-all duration-200 animate-scale-in ${
        isResultError
          ? "border-red-500/30 bg-red-500/[0.03]"
          : "border-border/50 bg-card/50 hover:border-border"
      }`}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-2.5 px-3 py-2.5 text-left text-sm hover:bg-muted/50 transition-colors"
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
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className={`font-mono text-xs font-medium ${meta.color}`}>
              {call.name}
            </span>
            {argsSummary && !expanded && (
              <span className="text-xs text-muted-foreground/50 truncate">
                {argsSummary}
              </span>
            )}
          </div>
          {/* Result preview when collapsed */}
          {!expanded && resultPreview && (
            <p className={`text-[10px] mt-0.5 truncate ${
              isResultError ? "text-red-400/70" : "text-muted-foreground/40"
            }`}>
              {resultPreview}
            </p>
          )}
        </div>
        <div className="ml-auto flex items-center gap-1.5 shrink-0">
          <span className={`text-[10px] font-mono ${isRunning ? "text-primary/50 animate-pulse" : "text-muted-foreground/40"}`}>
            {elapsedLabel}
          </span>
          {isRunning ? (
            <Loader2 className="h-3.5 w-3.5 text-primary/60 animate-spin" />
          ) : isResultError ? (
            <XCircle className="h-3.5 w-3.5 text-red-400/60" />
          ) : (
            <CheckCircle2 className="h-3.5 w-3.5 text-green-500/60" />
          )}
        </div>
      </button>

      {expanded && (
        <div className="border-t border-border/50 animate-fade-in-up">
          {/* Arguments */}
          {Object.keys(call.args).length > 0 && (
            <div className="px-3 pt-2.5 pb-1.5">
              <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground/60 mb-1.5">
                Arguments
              </p>
              <pre className="text-xs bg-muted dark:bg-black/30 rounded-lg p-2.5 overflow-x-auto text-foreground font-mono leading-relaxed">
                {JSON.stringify(call.args, null, 2)}
              </pre>
            </div>
          )}

          {/* Result */}
          <div className="px-3 pt-1.5 pb-2.5">
            <div className="flex items-center justify-between mb-1.5">
              <div className="flex items-center gap-2">
                <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground/60">
                  Result
                </p>
                {resultLines > 0 && (
                  <span className="text-[9px] text-muted-foreground/40 font-mono">
                    {resultLines} line{resultLines !== 1 ? "s" : ""}
                  </span>
                )}
              </div>
              {call.result && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleCopyResult();
                  }}
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
              )}
            </div>
            {isRunning ? (
              <div className="flex items-center gap-2 text-xs text-muted-foreground/50 py-2">
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                <span>Running...</span>
              </div>
            ) : (
              <pre className={`text-xs rounded-lg p-2.5 overflow-x-auto max-h-56 overflow-y-auto font-mono leading-relaxed scrollbar-thin ${
                isResultError
                  ? "bg-red-500/5 dark:bg-red-500/10 text-red-300"
                  : "bg-muted dark:bg-black/30 text-foreground"
              }`}>
                {call.result}
              </pre>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
