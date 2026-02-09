"use client";

import { useEffect, useRef } from "react";
import { MessageSquare, Zap, Code, Globe, Gamepad2 } from "lucide-react";
import type { ChatMessage } from "@/lib/types";
import { MessageBubble } from "./message-bubble";
import { TypingIndicator } from "./typing-indicator";
import { ChatInput } from "./chat-input";

interface ChatContainerProps {
  messages: ChatMessage[];
  isLoading: boolean;
  onSend: (message: string) => void;
}

const SUGGESTIONS = [
  { icon: Code, text: "Write a Python script that generates a fractal image" },
  { icon: Globe, text: "Search the web for the latest AI news" },
  { icon: Gamepad2, text: "Create a platformer game called SpaceRunner" },
  { icon: Zap, text: "List all files in the current directory" },
];

export function ChatContainer({ messages, isLoading, onSend }: ChatContainerProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  return (
    <div className="flex h-full flex-col">
      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        {messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center px-4">
            <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 border border-primary/20">
              <MessageSquare className="h-8 w-8 text-primary" />
            </div>
            <h2 className="mb-2 text-2xl font-bold tracking-tight">
              What can I help you build?
            </h2>
            <p className="mb-8 text-sm text-muted-foreground max-w-md text-center">
              I have 16 tools at my disposal including file operations, code execution,
              web search, and game development. Try one of these:
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-lg w-full">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s.text}
                  onClick={() => onSend(s.text)}
                  className="flex items-center gap-3 rounded-xl border border-white/5 bg-white/[0.02] p-3 text-left text-sm hover:bg-white/5 transition-colors"
                >
                  <s.icon className="h-4 w-4 text-primary shrink-0" />
                  <span className="text-muted-foreground">{s.text}</span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="mx-auto max-w-3xl py-4">
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}
            {isLoading && <TypingIndicator />}
          </div>
        )}
      </div>
      <ChatInput onSend={onSend} disabled={isLoading} />
    </div>
  );
}
