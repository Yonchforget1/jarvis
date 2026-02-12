"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface ChatMessageProps {
  role: "user" | "assistant" | "system";
  content: string;
  onFork?: () => void;
}

export function ChatMessage({ role, content, onFork }: ChatMessageProps) {
  const baseStyles: Record<string, string> = {
    user: "bg-blue-900/50 dark:bg-blue-900/50 bg-blue-100 self-end rounded-br-sm",
    assistant: "bg-zinc-100 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 self-start rounded-bl-sm",
    system: "bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-700 self-center text-xs text-zinc-500",
  };

  const forkBtn = onFork && role !== "system" ? (
    <button
      onClick={onFork}
      className="opacity-0 group-hover/msg:opacity-100 absolute -right-8 top-2 text-xs text-zinc-500 hover:text-blue-400 transition-all"
      title="Fork from here"
    >
      {"\u2442"}
    </button>
  ) : null;

  if (role === "assistant") {
    return (
      <div className="group/msg relative">
        <div
          className={`max-w-2xl px-4 py-3 rounded-xl text-sm leading-relaxed prose prose-invert prose-sm max-w-none
            prose-pre:bg-zinc-900 prose-pre:border prose-pre:border-zinc-700 prose-pre:rounded-lg
            prose-code:text-blue-300 prose-code:bg-zinc-900 prose-code:px-1 prose-code:py-0.5 prose-code:rounded
            prose-a:text-blue-400 prose-headings:text-zinc-100
            ${baseStyles[role]}`}
        >
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
        </div>
        {forkBtn}
      </div>
    );
  }

  return (
    <div className="group/msg relative">
      <div
        className={`max-w-2xl px-4 py-3 rounded-xl whitespace-pre-wrap break-words text-sm leading-relaxed ${baseStyles[role]}`}
      >
        {content}
      </div>
      {forkBtn}
    </div>
  );
}
