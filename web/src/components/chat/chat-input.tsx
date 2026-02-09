"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Send, Loader2, Keyboard, Paperclip, Mic } from "lucide-react";

const MAX_LENGTH = 50_000;
const WARN_THRESHOLD = 45_000;

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = Math.min(el.scrollHeight, 200) + "px";
    }
  }, [value]);

  // Auto-focus on mount and when not disabled
  useEffect(() => {
    if (!disabled) {
      textareaRef.current?.focus();
    }
  }, [disabled]);

  // Global Ctrl+/ to focus input
  useEffect(() => {
    const handleGlobalKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "/") {
        e.preventDefault();
        textareaRef.current?.focus();
      }
    };
    document.addEventListener("keydown", handleGlobalKey);
    return () => document.removeEventListener("keydown", handleGlobalKey);
  }, []);

  const handleSubmit = useCallback(() => {
    const trimmed = value.trim();
    if (!trimmed || disabled || trimmed.length > MAX_LENGTH) return;
    onSend(trimmed);
    setValue("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }, [value, disabled, onSend]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const charCount = value.length;
  const isNearLimit = charCount > WARN_THRESHOLD;
  const isOverLimit = charCount > MAX_LENGTH;
  const canSend = value.trim().length > 0 && !disabled && !isOverLimit;

  return (
    <div className="border-t border-border/50 bg-background/80 backdrop-blur-xl">
      <div className="mx-auto max-w-3xl p-3 sm:p-4">
        <div className="relative flex items-end gap-2">
          {/* Attachment button (coming soon) */}
          <div className="hidden sm:flex shrink-0">
            <button
              disabled
              className="flex h-11 w-11 items-center justify-center rounded-2xl text-muted-foreground/30 cursor-not-allowed transition-colors"
              title="File attachments coming soon"
            >
              <Paperclip className="h-4 w-4" />
            </button>
          </div>

          <div className="relative flex-1">
            <textarea
              ref={textareaRef}
              value={value}
              onChange={(e) => setValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                disabled
                  ? "Jarvis is working..."
                  : "Ask Jarvis anything..."
              }
              disabled={disabled}
              rows={1}
              aria-label="Message input"
              className={`w-full resize-none rounded-2xl border bg-secondary/50 px-4 py-3 pr-4 text-sm leading-relaxed placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-primary/20 disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-200 ${
                isOverLimit
                  ? "border-red-500/50 focus:border-red-500/50"
                  : "border-border focus:border-primary/40"
              }`}
            />
          </div>

          {/* Voice button (coming soon) */}
          <div className="hidden sm:flex shrink-0">
            <button
              disabled
              className="flex h-11 w-11 items-center justify-center rounded-2xl text-muted-foreground/30 cursor-not-allowed transition-colors"
              title="Voice input coming soon"
            >
              <Mic className="h-4 w-4" />
            </button>
          </div>

          <button
            onClick={handleSubmit}
            disabled={!canSend}
            aria-label={disabled ? "Sending message" : "Send message"}
            className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 ${
              canSend
                ? "bg-primary text-primary-foreground hover:bg-primary/90 shadow-lg shadow-primary/20 active:scale-95"
                : "bg-secondary text-muted-foreground/30 cursor-not-allowed"
            }`}
          >
            {disabled ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </button>
        </div>
        <div className="mt-1.5 flex items-center justify-between px-1">
          <div className="flex items-center gap-3 text-[10px] text-muted-foreground/40">
            <span className="hidden sm:flex items-center gap-1">
              <Keyboard className="h-2.5 w-2.5" />
              <kbd className="rounded bg-muted px-1 py-0.5 font-mono text-[9px]">Enter</kbd> send
              <span className="mx-1">&middot;</span>
              <kbd className="rounded bg-muted px-1 py-0.5 font-mono text-[9px]">Shift+Enter</kbd> new line
              <span className="mx-1">&middot;</span>
              <kbd className="rounded bg-muted px-1 py-0.5 font-mono text-[9px]">Ctrl+/</kbd> focus
            </span>
          </div>
          {isNearLimit && (
            <span
              className={`text-[10px] font-mono ${
                isOverLimit ? "text-red-400" : "text-yellow-400/60"
              }`}
            >
              {charCount.toLocaleString()}/{MAX_LENGTH.toLocaleString()}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
