"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { CodeBlock } from "@/components/CodeBlock";

interface ChatMessageProps {
  role: "user" | "assistant" | "system";
  content: string;
  timestamp?: number;
  onFork?: () => void;
  onEdit?: (newContent: string) => void;
  onRegenerate?: () => void;
  onCopy?: () => void;
}

function formatTime(ts?: number): string {
  if (!ts) return "";
  const d = new Date(ts);
  return d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}

function wordCount(text: string): number {
  return text.trim().split(/\s+/).filter(Boolean).length;
}

export function ChatMessage({ role, content, timestamp, onFork, onEdit, onRegenerate, onCopy }: ChatMessageProps) {
  const [editing, setEditing] = useState(false);
  const [editText, setEditText] = useState(content);
  const [copied, setCopied] = useState(false);

  const baseStyles: Record<string, string> = {
    user: "bg-blue-100 dark:bg-blue-900/50 self-end rounded-br-sm",
    assistant: "bg-zinc-100 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 self-start rounded-bl-sm",
    system: "bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-700 self-center text-xs text-zinc-500",
  };

  function handleCopy() {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
    onCopy?.();
  }

  function handleEditSubmit() {
    if (editText.trim() && editText !== content) {
      onEdit?.(editText.trim());
    }
    setEditing(false);
  }

  if (role === "system") {
    return (
      <div className={`max-w-2xl px-4 py-3 rounded-xl whitespace-pre-wrap break-words text-sm leading-relaxed ${baseStyles[role]}`}>
        {content}
      </div>
    );
  }

  // Action buttons
  const actions = (
    <div className="opacity-0 group-hover/msg:opacity-100 absolute -right-1 -top-6 flex items-center gap-1 bg-zinc-200 dark:bg-zinc-800 rounded-lg px-1.5 py-0.5 shadow-sm border border-zinc-300 dark:border-zinc-700 transition-opacity">
      <button onClick={handleCopy} className="text-xs text-zinc-500 hover:text-zinc-300 px-1" title="Copy">
        {copied ? "\u2713" : "\u2398"}
      </button>
      {role === "user" && onEdit && (
        <button onClick={() => { setEditText(content); setEditing(true); }} className="text-xs text-zinc-500 hover:text-blue-400 px-1" title="Edit">
          {"\u270E"}
        </button>
      )}
      {role === "assistant" && onRegenerate && (
        <button onClick={onRegenerate} className="text-xs text-zinc-500 hover:text-green-400 px-1" title="Regenerate">
          {"\u21BB"}
        </button>
      )}
      {onFork && (
        <button onClick={onFork} className="text-xs text-zinc-500 hover:text-purple-400 px-1" title="Fork from here">
          {"\u2442"}
        </button>
      )}
    </div>
  );

  // Editing mode for user messages
  if (editing && role === "user") {
    return (
      <div className="self-end max-w-2xl w-full">
        <textarea
          value={editText}
          onChange={(e) => setEditText(e.target.value)}
          className="w-full bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 rounded-xl px-4 py-3 text-sm border border-blue-500 focus:outline-none resize-none"
          rows={3}
          autoFocus
        />
        <div className="flex gap-2 mt-1 justify-end">
          <button onClick={() => setEditing(false)} className="text-xs text-zinc-500 hover:text-zinc-300 px-2 py-1">Cancel</button>
          <button onClick={handleEditSubmit} className="text-xs bg-blue-600 hover:bg-blue-500 text-white px-3 py-1 rounded">Save & Resend</button>
        </div>
      </div>
    );
  }

  const meta = (
    <div className="flex items-center gap-2 mt-1 opacity-0 group-hover/msg:opacity-100 transition-opacity">
      {timestamp && (
        <span className="text-[10px] text-zinc-400">{formatTime(timestamp)}</span>
      )}
      {role === "assistant" && content && (
        <span className="text-[10px] text-zinc-400">{wordCount(content)} words</span>
      )}
    </div>
  );

  if (role === "assistant") {
    return (
      <div className="group/msg relative">
        {actions}
        <div
          className={`max-w-2xl px-4 py-3 rounded-xl text-sm leading-relaxed prose dark:prose-invert prose-sm max-w-none
            prose-pre:bg-zinc-200 dark:prose-pre:bg-zinc-900 prose-pre:border prose-pre:border-zinc-300 dark:prose-pre:border-zinc-700 prose-pre:rounded-lg
            prose-code:text-blue-600 dark:prose-code:text-blue-300 prose-code:bg-zinc-200 dark:prose-code:bg-zinc-900 prose-code:px-1 prose-code:py-0.5 prose-code:rounded
            prose-a:text-blue-500 dark:prose-a:text-blue-400 prose-headings:text-zinc-900 dark:prose-headings:text-zinc-100
            ${baseStyles[role]}`}
        >
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              pre({ children }) {
                return <>{children}</>;
              },
              code({ className, children, ...props }) {
                const match = /language-(\w+)/.exec(className || "");
                const codeString = String(children).replace(/\n$/, "");
                if (match || codeString.includes("\n")) {
                  return (
                    <CodeBlock language={match?.[1]}>
                      {codeString}
                    </CodeBlock>
                  );
                }
                return <code className={className} {...props}>{children}</code>;
              },
            }}
          >{content}</ReactMarkdown>
        </div>
        {meta}
      </div>
    );
  }

  return (
    <div className="group/msg relative self-end">
      {actions}
      <div
        className={`max-w-2xl px-4 py-3 rounded-xl whitespace-pre-wrap break-words text-sm leading-relaxed ${baseStyles[role]}`}
      >
        {content}
      </div>
      {meta}
    </div>
  );
}
