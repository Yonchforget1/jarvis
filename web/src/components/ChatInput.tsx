"use client";

import { useRef, KeyboardEvent } from "react";

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const ref = useRef<HTMLTextAreaElement>(null);

  function handleKey(e: KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  function submit() {
    const text = ref.current?.value.trim();
    if (!text || disabled) return;
    onSend(text);
    if (ref.current) ref.current.value = "";
  }

  return (
    <div className="flex gap-2 p-3 bg-zinc-900 border-t border-zinc-800">
      <textarea
        ref={ref}
        placeholder="Message Jarvis..."
        rows={1}
        disabled={disabled}
        onKeyDown={handleKey}
        className="flex-1 bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-2.5 text-sm text-zinc-100 placeholder-zinc-500 resize-none outline-none focus:border-blue-500 disabled:opacity-50"
        onInput={(e) => {
          const el = e.currentTarget;
          el.style.height = "auto";
          el.style.height = Math.min(el.scrollHeight, 120) + "px";
        }}
      />
      <button
        onClick={submit}
        disabled={disabled}
        className="px-5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-colors"
      >
        Send
      </button>
    </div>
  );
}
