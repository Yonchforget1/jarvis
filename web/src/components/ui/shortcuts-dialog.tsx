"use client";

import { useEffect, useCallback } from "react";
import { X, Keyboard } from "lucide-react";
import { FocusTrap } from "@/components/ui/focus-trap";

interface ShortcutsDialogProps {
  open: boolean;
  onClose: () => void;
}

const isMac = typeof navigator !== "undefined" && /Mac/i.test(navigator.userAgent);
const MOD = isMac ? "\u2318" : "Ctrl";

const SHORTCUT_GROUPS = [
  {
    title: "Chat",
    shortcuts: [
      { keys: ["Enter"], description: "Send message" },
      { keys: [MOD, "Enter"], description: "Send message (alternative)" },
      { keys: ["Shift", "Enter"], description: "New line" },
      { keys: [MOD, "/"], description: "Focus input" },
      { keys: ["\u2191"], description: "Previous message from history" },
      { keys: ["\u2193"], description: "Next message from history" },
      { keys: ["/"], description: "Slash commands" },
    ],
  },
  {
    title: "Navigation",
    shortcuts: [
      { keys: [MOD, "F"], description: "Search messages" },
      { keys: [MOD, "K"], description: "Command palette" },
      { keys: [MOD, "N"], description: "New chat" },
      { keys: [MOD, "B"], description: "Toggle sidebar" },
      { keys: [MOD, "Shift", "E"], description: "Export chat" },
      { keys: [MOD, "Shift", "R"], description: "Retry last failed" },
      { keys: [MOD, "L"], description: "Clear chat" },
      { keys: [MOD, "Shift", "F"], description: "Focus mode" },
      { keys: [MOD, "Home"], description: "Scroll to top" },
      { keys: [MOD, "?"], description: "This shortcuts dialog" },
      { keys: ["Esc"], description: "Close search / dialog" },
    ],
  },
  {
    title: "Voice",
    shortcuts: [
      { keys: ["Click mic"], description: "Start recording" },
      { keys: ["Click stop"], description: "Stop and transcribe" },
    ],
  },
];

export function ShortcutsDialog({ open, onClose }: ShortcutsDialogProps) {
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape" && open) {
        onClose();
      }
    },
    [open, onClose],
  );

  useEffect(() => {
    if (!open) return;
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, handleKeyDown]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm animate-fade-in"
        onClick={onClose}
      />
      <FocusTrap>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="shortcuts-title"
        className="relative z-10 w-full max-w-md mx-4 rounded-2xl border border-border/50 bg-card p-6 shadow-2xl animate-fade-in-up"
      >
        <button
          onClick={onClose}
          aria-label="Close shortcuts"
          className="absolute top-4 right-4 rounded-lg p-1 text-muted-foreground/50 hover:text-foreground hover:bg-muted transition-colors"
        >
          <X className="h-4 w-4" />
        </button>

        <div className="flex items-center gap-2.5 mb-5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10">
            <Keyboard className="h-4 w-4 text-primary" />
          </div>
          <div>
            <h3 id="shortcuts-title" className="text-sm font-semibold">
              Keyboard Shortcuts
            </h3>
            <p className="text-[10px] text-muted-foreground/50">
              Press <kbd className="rounded bg-muted px-1 py-0.5 font-mono text-[9px]">{MOD}+?</kbd> to open this dialog anytime
            </p>
          </div>
        </div>

        <div className="space-y-5">
          {SHORTCUT_GROUPS.map((group) => (
            <div key={group.title}>
              <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground/50 mb-2">
                {group.title}
              </p>
              <div className="space-y-1.5">
                {group.shortcuts.map((shortcut) => (
                  <div
                    key={shortcut.description}
                    className="flex items-center justify-between py-1"
                  >
                    <span className="text-xs text-muted-foreground">
                      {shortcut.description}
                    </span>
                    <div className="flex items-center gap-1">
                      {shortcut.keys.map((key, i) => (
                        <span key={i}>
                          <kbd className="inline-flex h-5 min-w-5 items-center justify-center rounded bg-muted border border-border/50 px-1.5 text-[10px] font-mono text-muted-foreground">
                            {key}
                          </kbd>
                          {i < shortcut.keys.length - 1 && (
                            <span className="text-[10px] text-muted-foreground/30 mx-0.5">+</span>
                          )}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
      </FocusTrap>
    </div>
  );
}
