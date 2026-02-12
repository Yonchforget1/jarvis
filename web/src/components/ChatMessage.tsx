"use client";

interface ChatMessageProps {
  role: "user" | "assistant" | "system";
  content: string;
}

export function ChatMessage({ role, content }: ChatMessageProps) {
  const styles: Record<string, string> = {
    user: "bg-blue-900/50 self-end rounded-br-sm",
    assistant: "bg-zinc-800 border border-zinc-700 self-start rounded-bl-sm",
    system: "bg-zinc-900 border border-zinc-700 self-center text-xs text-zinc-500",
  };

  return (
    <div
      className={`max-w-2xl px-4 py-3 rounded-xl whitespace-pre-wrap break-words text-sm leading-relaxed ${styles[role]}`}
    >
      {content}
    </div>
  );
}
