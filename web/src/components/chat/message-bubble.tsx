"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import "highlight.js/styles/github-dark.css";
import { User, Bot, Copy, Check, AlertTriangle, RotateCcw, RefreshCw, Loader2, Square, ThumbsUp, ThumbsDown, ExternalLink, Pencil, X } from "lucide-react";
import { useState, useMemo, useCallback, useRef, useEffect, memo } from "react";
import type { ChatMessage } from "@/lib/types";
import { ToolCallCard } from "./tool-call-card";
import { Tooltip } from "@/components/ui/tooltip";

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => () => { if (timerRef.current) clearTimeout(timerRef.current); }, []);
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
    } catch {
      setCopied(false);
    }
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button
      onClick={handleCopy}
      aria-label={copied ? "Copied to clipboard" : "Copy code"}
      className="absolute top-2 right-2 rounded-lg bg-background/80 backdrop-blur-sm p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted transition-all duration-200 opacity-0 group-hover:opacity-100 border border-border/50"
      title="Copy code"
    >
      {copied ? (
        <Check className="h-3.5 w-3.5 text-green-400" />
      ) : (
        <Copy className="h-3.5 w-3.5" />
      )}
    </button>
  );
}

function MessageCopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => () => { if (timerRef.current) clearTimeout(timerRef.current); }, []);
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
    } catch {
      setCopied(false);
    }
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button
      onClick={handleCopy}
      aria-label={copied ? "Copied to clipboard" : "Copy message"}
      className="flex items-center gap-1 text-[10px] text-muted-foreground/60 hover:text-foreground transition-colors"
      title="Copy message"
    >
      {copied ? (
        <>
          <Check className="h-3 w-3 text-green-400" />
          <span className="text-green-400">Copied</span>
        </>
      ) : (
        <>
          <Copy className="h-3 w-3" />
          <span>Copy</span>
        </>
      )}
    </button>
  );
}

type Reaction = "up" | "down" | null;

function getReaction(messageId: string): Reaction {
  try {
    const stored = localStorage.getItem("jarvis-reactions");
    const reactions = stored ? JSON.parse(stored) : {};
    return reactions[messageId] || null;
  } catch {
    return null;
  }
}

const MAX_REACTIONS = 500;

function setReaction(messageId: string, reaction: Reaction) {
  try {
    const stored = localStorage.getItem("jarvis-reactions");
    const reactions: Record<string, string> = stored ? JSON.parse(stored) : {};
    if (reaction) {
      reactions[messageId] = reaction;
      // Cap storage: if over limit, remove oldest entries
      const keys = Object.keys(reactions);
      if (keys.length > MAX_REACTIONS) {
        const toRemove = keys.slice(0, keys.length - MAX_REACTIONS);
        for (const k of toRemove) delete reactions[k];
      }
    } else {
      delete reactions[messageId];
    }
    localStorage.setItem("jarvis-reactions", JSON.stringify(reactions));
  } catch {
    // ignore
  }
}

function MessageReactions({ messageId }: { messageId: string }) {
  const [reaction, setReactionState] = useState<Reaction>(() => getReaction(messageId));
  const [syncFailed, setSyncFailed] = useState(false);

  const toggle = useCallback(
    (type: "up" | "down") => {
      const next = reaction === type ? null : type;
      setReactionState(next);
      setReaction(messageId, next);
      setSyncFailed(false);
      const token = localStorage.getItem("jarvis_token");
      if (token) {
        fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/chat/reactions`, {
          method: "POST",
          headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
          body: JSON.stringify({ message_id: messageId, reaction: next }),
        }).catch(() => setSyncFailed(true));
      }
    },
    [messageId, reaction]
  );

  return (
    <div className="flex items-center gap-0.5">
      <button
        onClick={() => toggle("up")}
        aria-label="Mark as helpful"
        aria-pressed={reaction === "up"}
        className={`flex items-center rounded-md p-0.5 transition-colors ${
          reaction === "up"
            ? "text-green-400"
            : "text-muted-foreground/40 hover:text-green-400/70"
        }`}
        title="Helpful"
      >
        <ThumbsUp className="h-3 w-3" />
      </button>
      <button
        onClick={() => toggle("down")}
        aria-label="Mark as not helpful"
        aria-pressed={reaction === "down"}
        className={`flex items-center rounded-md p-0.5 transition-colors ${
          reaction === "down"
            ? "text-red-400"
            : "text-muted-foreground/40 hover:text-red-400/70"
        }`}
        title="Not helpful"
      >
        <ThumbsDown className="h-3 w-3" />
      </button>
      {syncFailed && (
        <span className="text-[9px] text-yellow-500/70 ml-0.5" title="Feedback saved locally but failed to sync">!</span>
      )}
    </div>
  );
}

const URL_REGEX = /https?:\/\/[^\s<>"{}|\\^`[\]]+/g;

function extractUrls(text: string): string[] {
  const matches = text.match(URL_REGEX);
  if (!matches) return [];
  // Deduplicate
  return [...new Set(matches)].slice(0, 3);
}

const LinkBadges = memo(function LinkBadges({ urls }: { urls: string[] }) {
  if (urls.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-1.5 mt-1">
      {urls.map((url) => {
        let domain: string;
        try {
          domain = new URL(url).hostname.replace("www.", "");
        } catch {
          domain = url.slice(0, 30);
        }
        return (
          <a
            key={url}
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 rounded-lg bg-primary/5 border border-primary/10 px-2 py-0.5 text-[10px] text-primary/70 hover:text-primary hover:bg-primary/10 transition-colors"
          >
            <ExternalLink className="h-2.5 w-2.5" />
            {domain}
          </a>
        );
      })}
    </div>
  );
});

function HighlightedText({ text, query }: { text: string; query: string }) {
  if (!query.trim()) return <>{text}</>;

  const parts: React.ReactNode[] = [];
  const lowerText = text.toLowerCase();
  const lowerQuery = query.toLowerCase();
  let lastIndex = 0;

  let idx = lowerText.indexOf(lowerQuery, lastIndex);
  while (idx !== -1) {
    if (idx > lastIndex) {
      parts.push(text.slice(lastIndex, idx));
    }
    parts.push(
      <mark key={idx} className="bg-yellow-400/30 text-inherit rounded-sm px-0.5">
        {text.slice(idx, idx + query.length)}
      </mark>
    );
    lastIndex = idx + query.length;
    idx = lowerText.indexOf(lowerQuery, lastIndex);
  }
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }
  return <>{parts}</>;
}

export const MessageBubble = memo(function MessageBubble({
  message,
  onRetry,
  onRegenerate,
  onStop,
  onEdit,
  searchQuery = "",
  isActiveMatch = false,
  isGrouped = false,
}: {
  message: ChatMessage;
  onRetry?: () => void;
  onRegenerate?: () => void;
  onStop?: () => void;
  onEdit?: (newContent: string) => void;
  searchQuery?: string;
  isActiveMatch?: boolean;
  isGrouped?: boolean;
}) {
  const isUser = message.role === "user";
  const isError = message.isError;
  const isStreaming = message.isStreaming;
  const [editing, setEditing] = useState(false);
  const [editValue, setEditValue] = useState("");
  const [showDiscardConfirm, setShowDiscardConfirm] = useState(false);

  // For user messages, highlight search terms in the plain text
  const userContent = useMemo(() => {
    if (!isUser || !searchQuery) return null;
    return <HighlightedText text={message.content} query={searchQuery} />;
  }, [isUser, message.content, searchQuery]);

  const userUrls = useMemo(() => {
    if (!isUser) return [];
    return extractUrls(message.content);
  }, [isUser, message.content]);

  return (
    <div
      data-message-id={message.id}
      role="article"
      aria-label={`${isUser ? "Your" : "JARVIS"} message`}
      className={`flex gap-3 px-4 animate-fade-in-up transition-colors duration-300 ${
        isGrouped ? "py-0.5" : "py-3"
      } ${
        isUser ? "flex-row-reverse" : ""
      } ${isActiveMatch ? "bg-primary/5 rounded-xl" : ""}`}
    >
      {/* Avatar */}
      {isGrouped ? (
        <div className="w-8 shrink-0" />
      ) : (
      <div
        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg transition-colors ${
          isUser
            ? "bg-primary/20"
            : isError
            ? "bg-red-500/20"
            : isStreaming
            ? "bg-primary/20 animate-glow-pulse"
            : "bg-secondary"
        }`}
      >
        {isUser ? (
          <User className="h-4 w-4 text-primary" />
        ) : isError ? (
          <AlertTriangle className="h-4 w-4 text-red-400" />
        ) : isStreaming ? (
          <Loader2 className="h-4 w-4 text-primary animate-spin" />
        ) : (
          <Bot className="h-4 w-4 text-primary" />
        )}
      </div>
      )}

      {/* Message content */}
      <div
        className={`flex flex-col gap-1 min-w-0 max-w-[85%] sm:max-w-[80%] ${
          isUser ? "items-end" : "items-start"
        }`}
      >
        {/* Tool calls shown before the response */}
        {!isUser && message.tool_calls && message.tool_calls.length > 0 && (
          <div className="w-full space-y-1.5 mb-1.5">
            {message.tool_calls.map((tc) => (
              <ToolCallCard key={tc.id} call={tc} />
            ))}
          </div>
        )}

        {/* Bubble */}
        <div
          className={`rounded-2xl px-4 py-2.5 transition-colors ${
            isUser
              ? "bg-primary text-primary-foreground rounded-br-md"
              : isError
              ? "bg-red-500/10 border border-red-500/20 text-foreground rounded-bl-md"
              : isStreaming
              ? "bg-secondary/80 backdrop-blur-sm border border-primary/20 text-secondary-foreground rounded-bl-md"
              : "bg-secondary/80 backdrop-blur-sm border border-border/50 text-secondary-foreground rounded-bl-md"
          }`}
        >
          {isUser ? (
            editing ? (
              <div className="space-y-2">
                <textarea
                  value={editValue}
                  onChange={(e) => setEditValue(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      if (editValue.trim() && onEdit) {
                        onEdit(editValue.trim());
                        setEditing(false);
                      }
                    }
                    if (e.key === "Escape") {
                      // If text unchanged, just close. Otherwise confirm discard.
                      if (editValue === message.content) {
                        setEditing(false);
                      } else {
                        setShowDiscardConfirm(true);
                      }
                    }
                  }}
                  className="w-full resize-none rounded-lg bg-primary-foreground/10 px-2 py-1.5 text-sm text-primary-foreground outline-none border border-primary-foreground/20 focus:border-primary-foreground/40"
                  rows={Math.min(editValue.split("\n").length + 1, 6)}
                  // eslint-disable-next-line jsx-a11y/no-autofocus
                  autoFocus
                />
                <div className="flex items-center gap-1.5 justify-end">
                  <button
                    onClick={() => setEditing(false)}
                    className="flex items-center gap-1 rounded-md px-2 py-1 text-[10px] text-primary-foreground/60 hover:text-primary-foreground transition-colors"
                  >
                    <X className="h-2.5 w-2.5" />
                    Cancel
                  </button>
                  <button
                    onClick={() => {
                      if (editValue.trim() && onEdit) {
                        onEdit(editValue.trim());
                        setEditing(false);
                      }
                    }}
                    className="flex items-center gap-1 rounded-md bg-primary-foreground/20 px-2 py-1 text-[10px] text-primary-foreground hover:bg-primary-foreground/30 transition-colors"
                  >
                    <Check className="h-2.5 w-2.5" />
                    Send
                  </button>
                </div>
                {showDiscardConfirm && (
                  <div className="flex items-center justify-between rounded-lg bg-red-500/10 border border-red-500/20 px-2 py-1.5">
                    <span className="text-[10px] text-red-400">Discard unsaved changes?</span>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => setShowDiscardConfirm(false)}
                        className="rounded px-1.5 py-0.5 text-[10px] text-primary-foreground/60 hover:text-primary-foreground transition-colors"
                      >
                        Keep editing
                      </button>
                      <button
                        onClick={() => { setShowDiscardConfirm(false); setEditing(false); }}
                        className="rounded bg-red-500/20 px-1.5 py-0.5 text-[10px] text-red-400 hover:bg-red-500/30 transition-colors"
                      >
                        Discard
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ) : (
            <div>
              <p className="text-sm whitespace-pre-wrap leading-relaxed">
                {userContent || message.content}
              </p>
              <LinkBadges urls={userUrls} />
            </div>
            )
          ) : isStreaming && !message.content ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground max-w-full" role="status" aria-live="polite">
              <span className="truncate max-w-xs">{message.streamStatus || "Thinking..."}</span>
              <span className="inline-block w-1.5 h-4 bg-primary/60 animate-pulse rounded-sm shrink-0" aria-hidden="true" />
            </div>
          ) : (
            <div className="prose prose-sm max-w-none dark:prose-invert prose-pre:relative prose-pre:bg-transparent prose-pre:p-0 prose-p:leading-relaxed prose-headings:text-foreground prose-a:text-primary prose-strong:text-foreground">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeHighlight]}
                components={{
                  pre: ({ children, ...props }) => {
                    let codeText = "";
                    let language = "";
                    try {
                      const child = children as React.ReactElement<{ children?: string; className?: string }>;
                      codeText = String(child?.props?.children || "");
                      const cls = child?.props?.className || "";
                      const langMatch = cls.match(/language-(\w+)/);
                      if (langMatch) language = langMatch[1];
                    } catch { /* ignore */ }
                    return (
                      <div className="relative group my-2">
                        {language && (
                          <div className="flex items-center justify-between rounded-t-xl border border-b-0 border-border/50 bg-slate-200 dark:bg-black/60 px-3 py-1.5">
                            <span className="text-[10px] font-mono text-muted-foreground uppercase">{language}</span>
                          </div>
                        )}
                        <pre
                          className={`!bg-slate-100 dark:!bg-black/40 !border !border-border/50 overflow-x-auto ${language ? "!rounded-t-none !rounded-b-xl" : "!rounded-xl"}`}
                          {...props}
                        >
                          {children}
                        </pre>
                        <CopyButton text={codeText} />
                      </div>
                    );
                  },
                  code: ({ className, children, ...props }) => {
                    const isInline = !className;
                    if (isInline) {
                      return (
                        <code
                          className="rounded-md bg-muted px-1.5 py-0.5 text-xs font-mono text-primary/90"
                          {...props}
                        >
                          {children}
                        </code>
                      );
                    }
                    return (
                      <code className={className} {...props}>
                        {children}
                      </code>
                    );
                  },
                  table: ({ children, ...props }) => (
                    <div className="overflow-x-auto my-2 rounded-xl border border-border/50">
                      <table className="!m-0 w-full text-xs" {...props}>{children}</table>
                    </div>
                  ),
                  th: ({ children, ...props }) => (
                    <th className="!border-b !border-border/50 !bg-muted/50 !px-3 !py-2 !text-left !text-[10px] !font-medium !uppercase !tracking-wider !text-muted-foreground/60" {...props}>{children}</th>
                  ),
                  td: ({ children, ...props }) => (
                    <td className="!border-b !border-border/30 !px-3 !py-2 !text-xs" {...props}>{children}</td>
                  ),
                  a: ({ href, children, ...props }) => (
                    <a href={href} target="_blank" rel="noopener noreferrer" className="text-primary hover:text-primary/80 underline underline-offset-2 decoration-primary/30 hover:decoration-primary/60 transition-colors" {...props}>{children}</a>
                  ),
                  img: ({ src, alt, ...props }) => (
                    <span className="block my-2">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={src}
                        alt={alt || "image"}
                        loading="lazy"
                        className="max-w-full rounded-xl border border-border/50 shadow-sm"
                        style={{ maxHeight: "400px", objectFit: "contain" }}
                        {...props}
                      />
                      {alt && alt !== "image" && (
                        <span className="block text-[10px] text-muted-foreground/50 mt-1 text-center">{alt}</span>
                      )}
                    </span>
                  ),
                }}
              >
                {message.content}
              </ReactMarkdown>
              {isStreaming && (
                <span className="inline-block w-1.5 h-4 bg-primary/60 animate-pulse rounded-sm ml-0.5 align-text-bottom" />
              )}
            </div>
          )}
        </div>

        {/* Footer: timestamp + actions */}
        <div className="flex items-center gap-2 px-1">
          {isStreaming ? (
            <>
              {message.streamStatus && (
                <span className="text-[10px] text-primary/60 animate-pulse">
                  {message.streamStatus}
                </span>
              )}
              {onStop && (
                <button
                  onClick={onStop}
                  className="flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground transition-colors"
                >
                  <Square className="h-2.5 w-2.5" />
                  Stop
                </button>
              )}
            </>
          ) : (
            <>
              <Tooltip
                content={new Date(message.timestamp).toLocaleString(undefined, {
                  weekday: "short",
                  year: "numeric",
                  month: "short",
                  day: "numeric",
                  hour: "2-digit",
                  minute: "2-digit",
                  second: "2-digit",
                })}
                side="top"
                delay={400}
              >
                <time
                  dateTime={message.timestamp}
                  aria-label={new Date(message.timestamp).toLocaleString()}
                  className="text-[10px] text-muted-foreground/60 cursor-default"
                >
                  {(() => {
                    const elapsed = Date.now() - new Date(message.timestamp).getTime();
                    if (elapsed < 60_000) return "just now";
                    return new Date(message.timestamp).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    });
                  })()}
                </time>
              </Tooltip>
              {message.content && (
                <MessageCopyButton text={message.content} />
              )}
              {isUser && onEdit && !editing && (
                <button
                  onClick={() => {
                    setEditValue(message.content);
                    setEditing(true);
                  }}
                  className="flex items-center gap-1 text-[10px] text-muted-foreground/60 hover:text-foreground transition-colors"
                  title="Edit message"
                >
                  <Pencil className="h-2.5 w-2.5" />
                  <span>Edit</span>
                </button>
              )}
              {!isUser && message.content && (() => {
                const wordCount = message.content.split(/\s+/).filter(Boolean).length;
                const readMin = Math.max(1, Math.ceil(wordCount / 200));
                return (
                  <>
                    <span className="text-[10px] text-muted-foreground/40">
                      {wordCount}w{wordCount >= 100 && ` · ${readMin} min read`}
                    </span>
                    <MessageReactions messageId={message.id} />
                  </>
                );
              })()}
              {onRegenerate && (
                <button
                  onClick={onRegenerate}
                  className="flex items-center gap-1 text-[10px] text-muted-foreground/60 hover:text-foreground transition-colors"
                  title="Regenerate response"
                >
                  <RefreshCw className="h-2.5 w-2.5" />
                  <span>Regenerate</span>
                </button>
              )}
              {isError && onRetry && (
                <button
                  onClick={onRetry}
                  className="flex items-center gap-1 text-[10px] text-red-400 hover:text-red-300 transition-colors"
                >
                  <RotateCcw className="h-3 w-3" />
                  Retry
                </button>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
});
