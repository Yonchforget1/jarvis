"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import "highlight.js/styles/github-dark.css";
import { User, Bot, Copy, Check, AlertTriangle, RotateCcw, Loader2, Square } from "lucide-react";
import { useState } from "react";
import type { ChatMessage } from "@/lib/types";
import { ToolCallCard } from "./tool-call-card";

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button
      onClick={handleCopy}
      className="absolute top-2 right-2 rounded-lg bg-white/10 p-1.5 text-zinc-400 hover:text-white hover:bg-white/20 transition-all duration-200 opacity-0 group-hover:opacity-100"
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

export function MessageBubble({
  message,
  onRetry,
  onStop,
}: {
  message: ChatMessage;
  onRetry?: () => void;
  onStop?: () => void;
}) {
  const isUser = message.role === "user";
  const isError = message.isError;
  const isStreaming = message.isStreaming;

  return (
    <div
      className={`flex gap-3 px-4 py-3 animate-fade-in-up ${
        isUser ? "flex-row-reverse" : ""
      }`}
    >
      {/* Avatar */}
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
              ? "bg-red-500/10 border border-red-500/20 text-red-200 rounded-bl-md"
              : isStreaming
              ? "bg-secondary/80 backdrop-blur-sm border border-primary/20 text-secondary-foreground rounded-bl-md"
              : "bg-secondary/80 backdrop-blur-sm border border-white/5 text-secondary-foreground rounded-bl-md"
          }`}
        >
          {isUser ? (
            <p className="text-sm whitespace-pre-wrap leading-relaxed">
              {message.content}
            </p>
          ) : isStreaming && !message.content ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <span>{message.streamStatus || "Thinking..."}</span>
              <span className="inline-block w-1.5 h-4 bg-primary/60 animate-pulse rounded-sm" />
            </div>
          ) : (
            <div className="prose prose-invert prose-sm max-w-none prose-pre:relative prose-pre:bg-transparent prose-pre:p-0 prose-p:leading-relaxed prose-headings:text-foreground prose-a:text-primary prose-strong:text-foreground">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeHighlight]}
                components={{
                  pre: ({ children, ...props }) => {
                    // Extract text content from children for copy button
                    let codeText = "";
                    try {
                      const child = children as React.ReactElement<{ children?: string }>;
                      codeText = String(child?.props?.children || "");
                    } catch { /* ignore */ }
                    return (
                      <div className="relative group my-2">
                        <pre
                          className="!bg-black/40 !rounded-xl !border !border-white/5 overflow-x-auto"
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
                          className="rounded-md bg-white/10 px-1.5 py-0.5 text-xs font-mono text-primary/90"
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

        {/* Footer: timestamp + retry/stop */}
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
              <span className="text-[10px] text-muted-foreground/60">
                {new Date(message.timestamp).toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </span>
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
}
