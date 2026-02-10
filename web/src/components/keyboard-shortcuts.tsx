"use client";

import { useEffect, useState, useMemo } from "react";
import { X, Keyboard } from "lucide-react";
import { FocusTrap } from "@/components/ui/focus-trap";

function useModKey() {
  return typeof navigator !== "undefined" && /Mac/i.test(navigator.userAgent) ? "\u2318" : "Ctrl";
}

function buildShortcuts(mod: string) {
  return [
    {
      category: "Navigation",
      items: [
        { keys: [mod, "K"], description: "Open command palette" },
        { keys: [mod, "N"], description: "New chat" },
        { keys: [mod, "B"], description: "Toggle sidebar" },
        { keys: [mod, "Shift", "F"], description: "Toggle focus mode" },
        { keys: ["Esc"], description: "Close sidebar / modal" },
      ],
    },
    {
      category: "Chat",
      items: [
        { keys: ["Enter"], description: "Send message" },
        { keys: ["Shift", "Enter"], description: "New line in message" },
        { keys: [mod, "/"], description: "Focus chat input" },
        { keys: [mod, "F"], description: "Search in messages" },
        { keys: [mod, "Shift", "E"], description: "Export chat as Markdown" },
        { keys: [mod, "Shift", "R"], description: "Regenerate last response" },
        { keys: [mod, "Home"], description: "Scroll to top" },
        { keys: [mod, "L"], description: "Clear chat" },
        { keys: ["\u2191", "\u2193"], description: "Navigate input history" },
      ],
    },
    {
      category: "Search",
      items: [
        { keys: ["Enter"], description: "Next match" },
        { keys: ["Shift", "Enter"], description: "Previous match" },
        { keys: ["Esc"], description: "Close search" },
      ],
    },
    {
      category: "Input",
      items: [
        { keys: ["/"], description: "Open slash commands" },
        { keys: ["Tab"], description: "Accept slash command" },
      ],
    },
    {
      category: "Sessions",
      items: [
        { keys: ["Double-click"], description: "Rename session" },
      ],
    },
    {
      category: "General",
      items: [
        { keys: [mod, "?"], description: "Show this help" },
      ],
    },
  ];
}

export function KeyboardShortcuts() {
  const [open, setOpen] = useState(false);
  const mod = useModKey();
  const SHORTCUTS = useMemo(() => buildShortcuts(mod), [mod]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "?") {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
      if (e.key === "Escape" && open) {
        setOpen(false);
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center animate-fade-in-up">
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={() => setOpen(false)}
      />
      <FocusTrap>
      <div role="dialog" aria-modal="true" aria-labelledby="kbd-shortcuts-title" className="relative w-full max-w-lg mx-4 rounded-2xl border border-border/50 bg-card/95 backdrop-blur-xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border/50">
          <div className="flex items-center gap-2.5">
            <Keyboard className="h-5 w-5 text-primary" />
            <h2 id="kbd-shortcuts-title" className="text-base font-semibold">Keyboard Shortcuts</h2>
          </div>
          <button
            onClick={() => setOpen(false)}
            className="rounded-lg p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Shortcuts */}
        <div className="px-6 py-4 max-h-[60vh] overflow-y-auto space-y-5">
          {SHORTCUTS.map((group) => (
            <div key={group.category}>
              <h3 className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground/50 mb-2.5">
                {group.category}
              </h3>
              <div className="space-y-2">
                {group.items.map((item) => (
                  <div
                    key={item.description}
                    className="flex items-center justify-between py-1"
                  >
                    <span className="text-sm text-muted-foreground">
                      {item.description}
                    </span>
                    <div className="flex items-center gap-1">
                      {item.keys.map((key, i) => (
                        <span key={i}>
                          {i > 0 && (
                            <span className="text-[10px] text-muted-foreground/30 mx-0.5">
                              +
                            </span>
                          )}
                          <kbd className="inline-flex h-6 min-w-6 items-center justify-center rounded-md bg-muted border border-border/50 px-1.5 text-[11px] font-mono text-muted-foreground">
                            {key}
                          </kbd>
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-border/50 bg-muted/30">
          <p className="text-[10px] text-muted-foreground/40 text-center">
            Press <kbd className="rounded bg-muted px-1 py-0.5 text-[9px] font-mono border border-border/50">{mod}+?</kbd> to toggle this dialog
          </p>
        </div>
      </div>
      </FocusTrap>
    </div>
  );
}
