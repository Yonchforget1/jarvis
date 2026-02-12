"use client";

interface ShortcutsModalProps {
  onClose: () => void;
}

const shortcuts = [
  { keys: "Ctrl + N", description: "New chat" },
  { keys: "Ctrl + K", description: "Search conversations" },
  { keys: "Ctrl + /", description: "Show keyboard shortcuts" },
  { keys: "Escape", description: "Focus chat input" },
  { keys: "Enter", description: "Send message" },
  { keys: "Shift + Enter", description: "New line in message" },
  { keys: "/", description: "Open slash commands" },
];

export function ShortcutsModal({ onClose }: ShortcutsModalProps) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={onClose}
    >
      <div
        className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-700 rounded-xl shadow-2xl w-full max-w-md mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-200 dark:border-zinc-800">
          <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">Keyboard Shortcuts</h2>
          <button
            onClick={onClose}
            className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 text-lg"
          >
            {"\u2715"}
          </button>
        </div>
        <div className="p-5 space-y-3">
          {shortcuts.map((s) => (
            <div key={s.keys} className="flex items-center justify-between">
              <span className="text-sm text-zinc-600 dark:text-zinc-400">{s.description}</span>
              <kbd className="px-2 py-1 text-xs font-mono bg-zinc-100 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 rounded text-zinc-700 dark:text-zinc-300">
                {s.keys}
              </kbd>
            </div>
          ))}
        </div>
        <div className="px-5 py-3 border-t border-zinc-200 dark:border-zinc-800 text-xs text-zinc-500 text-center">
          Press Esc to close
        </div>
      </div>
    </div>
  );
}
