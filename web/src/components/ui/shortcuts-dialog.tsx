"use client";

import { useEffect, useCallback } from "react";
import { X, Keyboard } from "lucide-react";

interface ShortcutsDialogProps {
  open: boolean;
  onClose: () => void;
}

const SHORTCUT_GROUPS = [
  {
    title: "Chat",
    shortcuts: [
      { keys: ["Enter"], description: "Send message" },
      { keys: ["Shift", "Enter"], description: "New line" },
      { keys: ["Ctrl", "/"], description: "Focus input" },
      { keys: ["\u2191"], description: "Previous message from history" },
      { keys: ["\u2193"], description: "Next message from history" },
      { keys: ["/"], description: "Slash commands" },
    ],
  },
  {
    title: "Navigation",
    shortcuts: [
      { keys: ["Ctrl", "F"], description: "Search messages" },
      { keys: ["Ctrl", "K"], description: "Command palette" },
      { keys: ["Ctrl", "N"], description: "New chat" },
      { keys: ["Ctrl", "B"], description: "Toggle sidebar" },
      { keys: ["Ctrl", "Shift", "E"], description: "Export chat" },
      { keys: ["Ctrl", "L"], description: "Clear chat" },
      { keys: ["Ctrl", "Shift", "F"], description: "Focus mode" },
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
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm animate-fade-in"
        onClick={onClose}
      />
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
          <h3 id="shortcuts-title" className="text-sm font-semibold">
            Keyboard Shortcuts
          </h3>
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
    </div>
  );
}
