"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Send, Loader2, Keyboard, Paperclip, Mic, MicOff, Square, Upload, Image, Trash2, Download, HelpCircle, Sparkles, Info, X, FileText } from "lucide-react";
import { useVoice } from "@/hooks/use-voice";
import { api } from "@/lib/api";

interface UploadedFile {
  filename: string;
  saved_as: string;
  size: number;
}

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB
const ALLOWED_EXTENSIONS = new Set([
  ".txt", ".md", ".py", ".js", ".ts", ".json", ".yaml", ".yml",
  ".csv", ".xml", ".html", ".css", ".sql", ".sh", ".bat",
  ".pdf", ".docx", ".xlsx", ".pptx",
  ".png", ".jpg", ".jpeg", ".gif", ".svg",
  ".zip", ".tar", ".gz",
  ".log", ".env", ".cfg", ".ini", ".toml",
]);

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getFileExt(name: string): string {
  const idx = name.lastIndexOf(".");
  return idx >= 0 ? name.slice(idx).toLowerCase() : "";
}

function isImageFile(name: string): boolean {
  const ext = getFileExt(name);
  return [".png", ".jpg", ".jpeg", ".gif", ".svg"].includes(ext);
}

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
  const [showSlash, setShowSlash] = useState(false);
  const [slashIndex, setSlashIndex] = useState(0);
  const [attachments, setAttachments] = useState<UploadedFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const isOnline = useOnlineStatus();

  // Ctrl+Enter to send preference
  const [ctrlEnterSend, setCtrlEnterSend] = useState(() => {
    if (typeof window === "undefined") return false;
    try { return localStorage.getItem("jarvis_ctrl_enter_send") === "true"; } catch { return false; }
  });
  useEffect(() => {
    const handler = () => {
      try { setCtrlEnterSend(localStorage.getItem("jarvis_ctrl_enter_send") === "true"); } catch { /* ignore */ }
    };
    window.addEventListener("storage", handler);
    window.addEventListener("ctrl-enter-pref-changed", handler);
    return () => {
      window.removeEventListener("storage", handler);
      window.removeEventListener("ctrl-enter-pref-changed", handler);
    };
  }, []);

  const voice = useVoice({
    onTranscript: (text) => {
      setValue((prev) => {
        const separator = prev.trim() ? " " : "";
        return prev + separator + text;
      });
      textareaRef.current?.focus();
    },
  });
  const uploadFile = useCallback(async (file: File) => {
    const ext = getFileExt(file.name);
    if (!ALLOWED_EXTENSIONS.has(ext)) {
      setUploadError(`File type '${ext}' not supported`);
      return;
    }
    if (file.size > MAX_FILE_SIZE) {
      setUploadError(`File too large (${formatFileSize(file.size)}, max 10 MB)`);
      return;
    }
    if (attachments.length >= 5) {
      setUploadError("Maximum 5 attachments per message");
      return;
    }
    setUploading(true);
    setUploadError(null);
    try {
      const res = await api.upload<{ filename: string; saved_as: string; size: number }>("/api/upload", file);
      setAttachments((prev) => [...prev, { filename: res.filename, saved_as: res.saved_as, size: res.size }]);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }, [attachments.length]);

  const removeAttachment = useCallback((savedAs: string) => {
    setAttachments((prev) => prev.filter((a) => a.saved_as !== savedAs));
    // Delete from server (fire-and-forget)
    api.delete(`/api/uploads/${encodeURIComponent(savedAs)}`).catch(() => {});
  }, []);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;
    for (const file of Array.from(files)) {
      uploadFile(file);
    }
    // Reset input so the same file can be selected again
    e.target.value = "";
  }, [uploadFile]);

  const dragCountRef = useRef(0);
  const historyRef = useRef<string[]>([]);
  const historyIndexRef = useRef(-1);
  const draftRef = useRef("");
  const draftTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Listen for files dropped on the chat container (full-page drop zone)
  useEffect(() => {
    const handler = (e: Event) => {
      const files = (e as CustomEvent<{ files: File[] }>).detail?.files;
      if (files) {
        for (const file of files) {
          uploadFile(file);
        }
      }
    };
    window.addEventListener("chat-drop-files", handler);
    return () => window.removeEventListener("chat-drop-files", handler);
  }, [uploadFile]);

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
    if ((!trimmed && attachments.length === 0) || disabled || trimmed.length > MAX_LENGTH) return;
    // Build message with attachment references
    let message = trimmed;
    if (attachments.length > 0) {
      const fileList = attachments.map((a) => `[Attached: ${a.filename} (${formatFileSize(a.size)})]`).join("\n");
      message = message ? `${message}\n\n${fileList}` : fileList;
    }
    historyRef.current.push(trimmed || message);
    if (historyRef.current.length > 50) historyRef.current.shift();
    historyIndexRef.current = -1;
    draftRef.current = "";
    try { localStorage.setItem("jarvis_input_history", JSON.stringify(historyRef.current)); } catch { /* ignore */ }
    onSend(message);
    setValue("");
    setAttachments([]);
    try { localStorage.removeItem("jarvis_draft"); } catch { /* ignore */ }
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }, [value, disabled, onSend, attachments]);

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
    // Send behavior depends on user preference
    if (e.key === "Enter") {
      if (ctrlEnterSend) {
        // Ctrl+Enter mode: only Ctrl/Cmd+Enter sends
        if (e.ctrlKey || e.metaKey) {
          e.preventDefault();
          handleSubmit();
        }
        // Plain Enter / Shift+Enter -> new line (default textarea behavior)
      } else {
        // Enter mode: Enter sends (unless Shift held), Ctrl/Cmd+Enter also sends
        if (!e.shiftKey || e.metaKey || e.ctrlKey) {
          e.preventDefault();
          handleSubmit();
        }
      }
    }
  };

  const handlePaste = useCallback((e: React.ClipboardEvent) => {
    const items = e.clipboardData?.items;
    if (!items) return;
    for (const item of Array.from(items)) {
      if (item.type.startsWith("image/")) {
        e.preventDefault();
        const blob = item.getAsFile();
        if (blob) {
          // Create a file with proper name and extension
          const ext = blob.type.split("/")[1]?.replace("jpeg", "jpg") || "png";
          const name = `pasted-image-${Date.now()}.${ext}`;
          const file = new File([blob], name, { type: blob.type });
          uploadFile(file);
        }
        return;
      }
    }
  }, [uploadFile]);

  const [showTips, setShowTips] = useState(false);

  const charCount = value.length;
  const wordCount = value.trim() ? value.trim().split(/\s+/).length : 0;
  const isNearLimit = charCount > WARN_THRESHOLD;
  const isOverLimit = charCount > MAX_LENGTH;
  const canSend = (value.trim().length > 0 || attachments.length > 0) && !disabled && !isOverLimit && isOnline;

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
        const files = e.dataTransfer?.files;
        if (files) {
          for (const file of Array.from(files)) {
            uploadFile(file);
          }
        }
      }}
    >
      {/* Drop zone overlay */}
      {isDragOver && (
        <div className="absolute inset-0 z-10 flex items-center justify-center rounded-2xl border-2 border-dashed border-primary/40 bg-primary/5 backdrop-blur-sm animate-fade-in">
          <div className="flex items-center gap-2 text-sm text-primary/70">
            <Upload className="h-5 w-5" />
            <span>Drop files to attach (max 10 MB)</span>
          </div>
        </div>
      )}
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        className="hidden"
        onChange={handleFileInput}
        accept={Array.from(ALLOWED_EXTENSIONS).join(",")}
      />
      <div className="mx-auto max-w-3xl p-3 sm:p-4">
        <div className="relative flex items-end gap-2">
          {/* Attachment button */}
          <div className="flex shrink-0">
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={disabled || uploading}
              className={`flex h-11 w-11 items-center justify-center rounded-2xl transition-colors ${
                disabled || uploading
                  ? "text-muted-foreground/30 cursor-not-allowed"
                  : "text-muted-foreground/60 hover:text-primary hover:bg-primary/10"
              }`}
              title={uploading ? "Uploading..." : "Attach file (max 10 MB)"}
            >
              {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Paperclip className="h-4 w-4" />}
            </button>
          </div>

          <div className="relative flex-1">
            {/* Slash commands dropdown */}
            {showSlash && filteredSlash.length > 0 && (
              <div role="listbox" aria-label="Slash commands" aria-activedescendant={`slash-cmd-${slashIndex}`} className="absolute bottom-full left-0 right-0 mb-2 rounded-xl border border-border/50 bg-card/95 backdrop-blur-xl shadow-xl overflow-hidden z-20 animate-fade-in">
                {filteredSlash.map((cmd, i) => (
                  <button
                    key={cmd.cmd}
                    id={`slash-cmd-${i}`}
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
        {/* Attached files */}
        {attachments.length > 0 && (
          <div className="mt-2 space-y-1.5 animate-fade-in">
            <div className="flex flex-wrap gap-2">
              {attachments.map((att) => (
                <div
                  key={att.saved_as}
                  className="flex items-center gap-2 rounded-xl border border-border/50 bg-muted/30 px-3 py-1.5 text-xs group"
                >
                  {isImageFile(att.filename) ? (
                    <Image className="h-3.5 w-3.5 text-purple-400 shrink-0" />
                  ) : (
                    <FileText className="h-3.5 w-3.5 text-blue-400 shrink-0" />
                  )}
                  <span className="text-muted-foreground truncate max-w-[150px]" title={att.filename}>{att.filename}</span>
                  <span className="text-muted-foreground/40 text-[10px]">{formatFileSize(att.size)}</span>
                  <button
                    onClick={() => removeAttachment(att.saved_as)}
                    className="p-0.5 rounded-md text-muted-foreground/40 hover:text-red-400 hover:bg-red-400/10 transition-colors"
                    title="Remove"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </div>
              ))}
            </div>
            <div className="flex items-center gap-3 px-1">
              <span className="text-[10px] text-muted-foreground/40">
                {attachments.length} file{attachments.length !== 1 ? "s" : ""} · {formatFileSize(attachments.reduce((sum, a) => sum + a.size, 0))} total
              </span>
              {attachments.length > 1 && (
                <button
                  onClick={() => {
                    for (const att of attachments) {
                      api.delete(`/api/uploads/${encodeURIComponent(att.saved_as)}`).catch(() => {});
                    }
                    setAttachments([]);
                  }}
                  className="text-[10px] text-muted-foreground/40 hover:text-red-400 transition-colors"
                >
                  Clear all
                </button>
              )}
            </div>
          </div>
        )}
        {/* Upload error */}
        {uploadError && (
          <div className="mt-2 flex items-center gap-2 rounded-xl bg-red-500/10 border border-red-500/20 px-3 py-2 animate-fade-in">
            <span className="text-xs text-red-400">{uploadError}</span>
            <button onClick={() => setUploadError(null)} className="ml-auto p-0.5 text-red-400/60 hover:text-red-400">
              <X className="h-3 w-3" />
            </button>
          </div>
        )}
        {/* Offline indicator */}
        {!isOnline && (
          <div role="status" className="mt-2 flex items-center gap-2 rounded-xl bg-red-500/10 border border-red-500/20 px-3 py-2 animate-fade-in">
            <div className="h-2 w-2 rounded-full bg-red-500" />
            <span className="text-xs text-red-400">You&apos;re offline. Messages will send when connection is restored.</span>
          </div>
        )}
        {/* Over character limit warning */}
        {isOverLimit && (
          <div className="mt-2 flex items-center gap-2 rounded-xl bg-red-500/10 border border-red-500/20 px-3 py-2 animate-fade-in">
            <span className="text-xs text-red-400">
              Message exceeds {MAX_LENGTH.toLocaleString()} character limit ({(charCount - MAX_LENGTH).toLocaleString()} over). Shorten your message to send.
            </span>
          </div>
        )}
        {/* Uploading indicator */}
        {uploading && (
          <div className="mt-2 flex items-center gap-2 rounded-xl bg-primary/5 border border-primary/20 px-3 py-2 animate-fade-in">
            <Loader2 className="h-3.5 w-3.5 text-primary animate-spin" />
            <span className="text-xs text-primary/70">Uploading file...</span>
          </div>
        )}
        {/* Expandable tips panel */}
        {showTips && (
          <div role="note" aria-label="Keyboard shortcuts" className="mt-2 rounded-xl border border-border/30 bg-muted/30 p-3 animate-fade-in text-[11px] text-muted-foreground/60 space-y-1.5">
            <div className="flex items-center gap-2"><kbd aria-label={ctrlEnterSend ? "Control plus Enter" : "Enter key"} className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px]">{ctrlEnterSend ? (typeof navigator !== "undefined" && /Mac/i.test(navigator.userAgent) ? "\u2318" : "Ctrl") + "+Enter" : "Enter"}</kbd> Send message</div>
            <div className="flex items-center gap-2"><kbd aria-label={ctrlEnterSend ? "Enter key" : "Shift plus Enter"} className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px]">{ctrlEnterSend ? "Enter" : "Shift+Enter"}</kbd> New line</div>
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
              <kbd className="rounded bg-muted px-1 py-0.5 font-mono text-[9px]">{ctrlEnterSend ? (typeof navigator !== "undefined" && /Mac/i.test(navigator.userAgent) ? "\u2318" : "Ctrl") + "+Enter" : "Enter"}</kbd> send
              <span className="mx-1">&middot;</span>
              <kbd className="rounded bg-muted px-1 py-0.5 font-mono text-[9px]">{ctrlEnterSend ? "Enter" : "Shift+Enter"}</kbd> new line
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
