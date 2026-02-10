"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Send, Loader2, Keyboard, Paperclip, Mic, MicOff, Square, Upload, Image, Trash2, Download, HelpCircle, Sparkles, Info } from "lucide-react";
import { useVoice } from "@/hooks/use-voice";

const MAX_LENGTH = 50_000;
const WARN_THRESHOLD = 45_000;

function useOnlineStatus() {
  const [online, setOnline] = useState(typeof navigator !== "undefined" ? navigator.onLine : true);
  useEffect(() => {
    const on = () => setOnline(true);
    const off = () => setOnline(false);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", off);
    };
  }, []);
  return online;
}

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
  const isOnline = useOnlineStatus();

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
  const draftTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Restore input history and draft from localStorage on mount
  useEffect(() => {
    try {
      const savedHistory = localStorage.getItem("jarvis_input_history");
      if (savedHistory) {
        const parsed = JSON.parse(savedHistory);
        if (Array.isArray(parsed)) historyRef.current = parsed.slice(-50);
      }
    } catch { /* ignore */ }
    try {
      const saved = localStorage.getItem("jarvis_draft");
      if (saved) setValue(saved);
    } catch { /* ignore */ }
  }, []);

  // Auto-save draft to localStorage (debounced 500ms)
  useEffect(() => {
    if (draftTimerRef.current) clearTimeout(draftTimerRef.current);
    draftTimerRef.current = setTimeout(() => {
      try {
        if (value.trim()) {
          localStorage.setItem("jarvis_draft", value);
        } else {
          localStorage.removeItem("jarvis_draft");
        }
      } catch { /* ignore */ }
    }, 500);
    return () => { if (draftTimerRef.current) clearTimeout(draftTimerRef.current); };
  }, [value]);

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
    try { localStorage.setItem("jarvis_input_history", JSON.stringify(historyRef.current)); } catch { /* ignore */ }
    onSend(trimmed);
    setValue("");
    try { localStorage.removeItem("jarvis_draft"); } catch { /* ignore */ }
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }, [value, disabled, onSend]);

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const v = e.target.value;
    setValue(v);
    if (v.startsWith("/") && !v.includes(" ") && v.length > 0 && v.length <= 10) {
      setShowSlash(true);
      setSlashIndex(0);
    } else if (showSlash) {
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
        const clamped = Math.min(slashIndex, filteredSlash.length - 1);
        handleSlashSelect(filteredSlash[clamped].action);
        return;
      }
      if (e.key === "Escape") {
        setShowSlash(false);
        return;
      }
    }
    // Input history navigation (only when at first/last line)
    if (e.key === "ArrowUp" && !e.shiftKey && historyRef.current.length > 0) {
      const el = textareaRef.current;
      const isAtStart = el && el.selectionStart === 0 && el.selectionEnd === 0;
      if (isAtStart || !value) {
        e.preventDefault();
        if (historyIndexRef.current === -1) {
          draftRef.current = value;
          historyIndexRef.current = historyRef.current.length - 1;
        } else if (historyIndexRef.current > 0) {
          historyIndexRef.current--;
        }
        setValue(historyRef.current[historyIndexRef.current]);
      }
    }
    if (e.key === "ArrowDown" && !e.shiftKey && historyIndexRef.current >= 0) {
      const el = textareaRef.current;
      const isAtEnd = el && el.selectionStart === el.value.length;
      if (isAtEnd) {
        e.preventDefault();
        if (historyIndexRef.current < historyRef.current.length - 1) {
          historyIndexRef.current++;
          setValue(historyRef.current[historyIndexRef.current]);
        } else {
          historyIndexRef.current = -1;
          setValue(draftRef.current);
        }
      }
    }
    // Send on Enter (without Shift) or Cmd/Ctrl+Enter
    if (e.key === "Enter" && (!e.shiftKey || e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const pastedImageTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => () => {
    if (pastedImageTimerRef.current) clearTimeout(pastedImageTimerRef.current);
  }, []);

  const handlePaste = useCallback((e: React.ClipboardEvent) => {
    const items = e.clipboardData?.items;
    if (!items) return;
    for (const item of Array.from(items)) {
      if (item.type.startsWith("image/")) {
        e.preventDefault();
        setPastedImage(true);
        if (pastedImageTimerRef.current) clearTimeout(pastedImageTimerRef.current);
        pastedImageTimerRef.current = setTimeout(() => setPastedImage(false), 3000);
        return;
      }
    }
  }, []);

  const [showTips, setShowTips] = useState(false);

  const charCount = value.length;
  const wordCount = value.trim() ? value.trim().split(/\s+/).length : 0;
  const isNearLimit = charCount > WARN_THRESHOLD;
  const isOverLimit = charCount > MAX_LENGTH;
  const canSend = value.trim().length > 0 && !disabled && !isOverLimit && isOnline;

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
              <div role="listbox" aria-label="Slash commands" className="absolute bottom-full left-0 right-0 mb-2 rounded-xl border border-border/50 bg-card/95 backdrop-blur-xl shadow-xl overflow-hidden z-20 animate-fade-in">
                {filteredSlash.map((cmd, i) => (
                  <button
                    key={cmd.cmd}
                    role="option"
                    aria-selected={i === slashIndex}
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
                  : "Ask Jarvis anything... (type / for commands)"
              }
              disabled={disabled}
              rows={1}
              aria-label="Message input"
              aria-haspopup="listbox"
              aria-expanded={showSlash && filteredSlash.length > 0}
              aria-autocomplete={showSlash ? "list" : "none"}
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
        {/* Offline indicator */}
        {!isOnline && (
          <div role="status" className="mt-2 flex items-center gap-2 rounded-xl bg-red-500/10 border border-red-500/20 px-3 py-2 animate-fade-in">
            <div className="h-2 w-2 rounded-full bg-red-500" />
            <span className="text-xs text-red-400">You&apos;re offline. Messages will send when connection is restored.</span>
          </div>
        )}
        {/* Paste image notification */}
        {pastedImage && (
          <div className="mt-2 flex items-center gap-2 rounded-xl bg-amber-500/10 border border-amber-500/20 px-3 py-2 animate-fade-in">
            <Image className="h-3.5 w-3.5 text-amber-500" />
            <span className="text-xs text-amber-500">Image attachments coming soon</span>
          </div>
        )}
        {/* Expandable tips panel */}
        {showTips && (
          <div role="note" aria-label="Keyboard shortcuts" className="mt-2 rounded-xl border border-border/30 bg-muted/30 p-3 animate-fade-in text-[11px] text-muted-foreground/60 space-y-1.5">
            <div className="flex items-center gap-2"><kbd aria-label="Enter key" className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px]">Enter</kbd> Send message</div>
            <div className="flex items-center gap-2"><kbd aria-label="Shift plus Enter" className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px]">Shift+Enter</kbd> New line</div>
            <div className="flex items-center gap-2"><kbd aria-label="Control plus slash" className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px]">{typeof navigator !== "undefined" && /Mac/i.test(navigator.userAgent) ? "\u2318" : "Ctrl"}+/</kbd> Focus input</div>
            <div className="flex items-center gap-2"><kbd aria-label="Forward slash" className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px]">/</kbd> Slash commands (/clear, /export, /new, /help)</div>
            <div className="flex items-center gap-2"><kbd aria-label="Up and down arrows" className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px]">&uarr; &darr;</kbd> Navigate input history</div>
            <div className="text-[10px] text-muted-foreground/40 pt-1">Drafts are auto-saved and restored on next visit.</div>
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
              <kbd className="rounded bg-muted px-1 py-0.5 font-mono text-[9px]">{typeof navigator !== "undefined" && /Mac/i.test(navigator.userAgent) ? "\u2318" : "Ctrl"}+/</kbd> focus
            </span>
            <button
              onClick={() => setShowTips((v) => !v)}
              className="sm:hidden flex items-center gap-1 text-muted-foreground/40 hover:text-muted-foreground/70 transition-colors"
              aria-label="Toggle keyboard shortcuts"
            >
              <Info className="h-2.5 w-2.5" />
              <span>Tips</span>
            </button>
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
                : `${wordCount} word${wordCount !== 1 ? "s" : ""} · ${charCount.toLocaleString()} chars`}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
