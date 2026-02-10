"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Send, Loader2, Keyboard, Paperclip, Mic, MicOff, Square, Upload, Image, Trash2, Download, HelpCircle, Sparkles } from "lucide-react";
import { useVoice } from "@/hooks/use-voice";

const MAX_LENGTH = 50_000;
const WARN_THRESHOLD = 45_000;

const SLASH_COMMANDS = [
  { cmd: "/clear", description: "Clear conversation", icon: Trash2, action: "clear" as const },
  { cmd: "/export", description: "Export chat as Markdown", icon: Download, action: "export" as const },
  { cmd: "/new", description: "Start a new chat", icon: Sparkles, action: "new" as const },
  { cmd: "/help", description: "Show keyboard shortcuts", icon: HelpCircle, action: "help" as const },
];

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  onSlashCommand?: (action: "clear" | "export" | "new" | "help") => void;
}

export function ChatInput({ onSend, disabled, onSlashCommand }: ChatInputProps) {
  const [value, setValue] = useState("");
  const [isDragOver, setIsDragOver] = useState(false);
  const [pastedImage, setPastedImage] = useState(false);
  const [showSlash, setShowSlash] = useState(false);
  const [slashIndex, setSlashIndex] = useState(0);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const voice = useVoice({
    onTranscript: (text) => {
      setValue((prev) => {
        const separator = prev.trim() ? " " : "";
        return prev + separator + text;
      });
      textareaRef.current?.focus();
    },
  });
  const dragCountRef = useRef(0);
  const historyRef = useRef<string[]>([]);
  const historyIndexRef = useRef(-1);
  const draftRef = useRef("");

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

  // Compute filtered slash commands
  const slashQuery = showSlash ? value.slice(1).toLowerCase() : "";
  const filteredSlash = SLASH_COMMANDS.filter((c) =>
    c.cmd.toLowerCase().includes("/" + slashQuery),
  );

  const handleSlashSelect = useCallback((action: "clear" | "export" | "new" | "help") => {
    setValue("");
    setShowSlash(false);
    onSlashCommand?.(action);
  }, [onSlashCommand]);

  const handleSubmit = useCallback(() => {
    const trimmed = value.trim();
    if (!trimmed || disabled || trimmed.length > MAX_LENGTH) return;
    historyRef.current.push(trimmed);
    if (historyRef.current.length > 50) historyRef.current.shift();
    historyIndexRef.current = -1;
    draftRef.current = "";
    onSend(trimmed);
    setValue("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }, [value, disabled, onSend]);

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const v = e.target.value;
    setValue(v);
    if (v.startsWith("/") && !v.includes(" ") && v.length <= 10) {
      setShowSlash(true);
      setSlashIndex(0);
    } else {
      setShowSlash(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (showSlash && filteredSlash.length > 0) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSlashIndex((i) => Math.min(i + 1, filteredSlash.length - 1));
        return;
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        setSlashIndex((i) => Math.max(i - 1, 0));
        return;
      }
      if (e.key === "Enter" || e.key === "Tab") {
        e.preventDefault();
        handleSlashSelect(filteredSlash[slashIndex].action);
        return;
      }
      if (e.key === "Escape") {
        setShowSlash(false);
        return;
      }
    }
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handlePaste = useCallback((e: React.ClipboardEvent) => {
    const items = e.clipboardData?.items;
    if (!items) return;
    for (const item of Array.from(items)) {
      if (item.type.startsWith("image/")) {
        e.preventDefault();
        setPastedImage(true);
        setTimeout(() => setPastedImage(false), 3000);
        return;
      }
    }
  }, []);

  const charCount = value.length;
  const isNearLimit = charCount > WARN_THRESHOLD;
  const isOverLimit = charCount > MAX_LENGTH;
  const canSend = value.trim().length > 0 && !disabled && !isOverLimit;

  return (
    <div
      className="border-t border-border/50 bg-background/80 backdrop-blur-xl relative"
      onDragEnter={(e) => {
        e.preventDefault();
        dragCountRef.current++;
        setIsDragOver(true);
      }}
      onDragOver={(e) => e.preventDefault()}
      onDragLeave={() => {
        dragCountRef.current--;
        if (dragCountRef.current <= 0) {
          dragCountRef.current = 0;
          setIsDragOver(false);
        }
      }}
      onDrop={(e) => {
        e.preventDefault();
        dragCountRef.current = 0;
        setIsDragOver(false);
      }}
    >
      {/* Drop zone overlay */}
      {isDragOver && (
        <div className="absolute inset-0 z-10 flex items-center justify-center rounded-2xl border-2 border-dashed border-primary/40 bg-primary/5 backdrop-blur-sm animate-fade-in">
          <div className="flex items-center gap-2 text-sm text-primary/70">
            <Upload className="h-5 w-5" />
            <span>File attachments coming soon</span>
          </div>
        </div>
      )}
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
            {/* Slash commands dropdown */}
            {showSlash && filteredSlash.length > 0 && (
              <div className="absolute bottom-full left-0 right-0 mb-2 rounded-xl border border-border/50 bg-card/95 backdrop-blur-xl shadow-xl overflow-hidden z-20 animate-fade-in">
                {filteredSlash.map((cmd, i) => (
                  <button
                    key={cmd.cmd}
                    onMouseDown={(e) => {
                      e.preventDefault();
                      handleSlashSelect(cmd.action);
                    }}
                    onMouseEnter={() => setSlashIndex(i)}
                    className={`flex w-full items-center gap-3 px-3 py-2.5 text-left text-sm transition-colors ${
                      i === slashIndex ? "bg-primary/10 text-foreground" : "text-muted-foreground hover:bg-muted/50"
                    }`}
                  >
                    <cmd.icon className={`h-3.5 w-3.5 shrink-0 ${i === slashIndex ? "text-primary" : ""}`} />
                    <span className="font-mono text-xs font-medium">{cmd.cmd}</span>
                    <span className="text-xs text-muted-foreground/60">{cmd.description}</span>
                  </button>
                ))}
              </div>
            )}
            <textarea
              ref={textareaRef}
              value={value}
              onChange={handleChange}
              onKeyDown={handleKeyDown}
              onPaste={handlePaste}
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

          {/* Voice input button */}
          {voice.isAvailable && (
            <div className="shrink-0">
              {voice.isRecording ? (
                <div className="flex items-center gap-1.5">
                  <div className="flex items-center gap-1.5 rounded-2xl bg-red-500/10 border border-red-500/20 px-2.5 py-1.5">
                    <div className="h-2 w-2 rounded-full bg-red-500 animate-pulse" />
                    <span className="text-xs font-mono text-red-400 tabular-nums">
                      {Math.floor(voice.duration / 60)}:{String(Math.floor(voice.duration % 60)).padStart(2, "0")}
                    </span>
                  </div>
                  <button
                    onClick={voice.stopRecording}
                    className="flex h-11 w-11 items-center justify-center rounded-2xl bg-red-500 text-white hover:bg-red-600 transition-colors shadow-lg shadow-red-500/20 active:scale-95"
                    title="Stop recording and transcribe"
                  >
                    <Square className="h-4 w-4" />
                  </button>
                </div>
              ) : voice.isTranscribing ? (
                <button
                  disabled
                  className="flex h-11 w-11 items-center justify-center rounded-2xl bg-primary/10 text-primary transition-colors"
                  title="Transcribing..."
                >
                  <Loader2 className="h-4 w-4 animate-spin" />
                </button>
              ) : (
                <button
                  onClick={voice.startRecording}
                  disabled={disabled}
                  className={`flex h-11 w-11 items-center justify-center rounded-2xl transition-all duration-200 ${
                    voice.error
                      ? "text-red-400 bg-red-500/10"
                      : disabled
                      ? "text-muted-foreground/30 cursor-not-allowed"
                      : "text-muted-foreground/60 hover:text-primary hover:bg-primary/10"
                  }`}
                  title={voice.error || "Record voice message"}
                >
                  {voice.error ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
                </button>
              )}
            </div>
          )}

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
        {/* Paste image notification */}
        {pastedImage && (
          <div className="mt-2 flex items-center gap-2 rounded-xl bg-amber-500/10 border border-amber-500/20 px-3 py-2 animate-fade-in">
            <Image className="h-3.5 w-3.5 text-amber-500" />
            <span className="text-xs text-amber-500">Image attachments coming soon</span>
          </div>
        )}
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
          {charCount > 0 && (
            <span
              className={`text-[10px] font-mono transition-colors ${
                isOverLimit
                  ? "text-red-400"
                  : isNearLimit
                  ? "text-yellow-400/60"
                  : "text-muted-foreground/30"
              }`}
            >
              {isNearLimit
                ? `${charCount.toLocaleString()}/${MAX_LENGTH.toLocaleString()}`
                : `${charCount.toLocaleString()} chars`}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
