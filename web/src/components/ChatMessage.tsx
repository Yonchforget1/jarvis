"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface ChatMessageProps {
  role: "user" | "assistant" | "system";
  content: string;
}

export function ChatMessage({ role, content }: ChatMessageProps) {
  const baseStyles: Record<string, string> = {
    user: "bg-blue-900/50 self-end rounded-br-sm",
    assistant: "bg-zinc-800 border border-zinc-700 self-start rounded-bl-sm",
    system: "bg-zinc-900 border border-zinc-700 self-center text-xs text-zinc-500",
  };

  if (role === "assistant") {
    return (
      <div
        className={`max-w-2xl px-4 py-3 rounded-xl text-sm leading-relaxed prose prose-invert prose-sm max-w-none
          prose-pre:bg-zinc-900 prose-pre:border prose-pre:border-zinc-700 prose-pre:rounded-lg
          prose-code:text-blue-300 prose-code:bg-zinc-900 prose-code:px-1 prose-code:py-0.5 prose-code:rounded
          prose-a:text-blue-400 prose-headings:text-zinc-100
          ${baseStyles[role]}`}
      >
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
      </div>
    );
  }

  return (
    <div
      className={`max-w-2xl px-4 py-3 rounded-xl whitespace-pre-wrap break-words text-sm leading-relaxed ${baseStyles[role]}`}
    >
      {content}
    </div>
  );
}
