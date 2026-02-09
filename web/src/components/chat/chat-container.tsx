"use client";

import { useEffect, useRef } from "react";
import {
  MessageSquare,
  Zap,
  Code,
  Globe,
  Gamepad2,
  Sparkles,
} from "lucide-react";
import type { ChatMessage } from "@/lib/types";
import { MessageBubble } from "./message-bubble";
import { TypingIndicator } from "./typing-indicator";
import { ChatInput } from "./chat-input";

interface ChatContainerProps {
  messages: ChatMessage[];
  isLoading: boolean;
  onSend: (message: string) => void;
  onRetry?: () => void;
}

const SUGGESTIONS = [
  {
    icon: Code,
    text: "Write a Python script that generates a fractal image",
    color: "text-green-400",
    bg: "bg-green-400/10 border-green-400/20",
  },
  {
    icon: Globe,
    text: "Search the web for the latest AI news",
    color: "text-orange-400",
    bg: "bg-orange-400/10 border-orange-400/20",
  },
  {
    icon: Gamepad2,
    text: "Create a platformer game called SpaceRunner",
    color: "text-purple-400",
    bg: "bg-purple-400/10 border-purple-400/20",
  },
  {
    icon: Zap,
    text: "List all files in the current directory",
    color: "text-blue-400",
    bg: "bg-blue-400/10 border-blue-400/20",
  },
];

export function ChatContainer({
  messages,
  isLoading,
  onSend,
  onRetry,
}: ChatContainerProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: "smooth",
      });
    }
  }, [messages, isLoading]);

  return (
    <div className="flex h-full flex-col">
      {/* Message area */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto scroll-smooth">
        {messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center px-4 animate-fade-in-up">
            {/* Logo */}
            <div className="relative mb-8">
              <div className="flex h-20 w-20 items-center justify-center rounded-3xl bg-primary/10 border border-primary/20">
                <MessageSquare className="h-10 w-10 text-primary" />
              </div>
              <div className="absolute -bottom-1 -right-1 flex h-7 w-7 items-center justify-center rounded-full bg-green-500/20 border border-green-500/30">
                <Sparkles className="h-3.5 w-3.5 text-green-400" />
              </div>
            </div>

            {/* Welcome text */}
            <h2 className="mb-2 text-2xl sm:text-3xl font-bold tracking-tight text-center">
              What can I help you build?
            </h2>
            <p className="mb-10 text-sm text-muted-foreground/70 max-w-md text-center leading-relaxed">
              I&apos;m JARVIS, your AI agent with 16+ professional tools. I can
              write code, search the web, manage files, and build games.
            </p>

            {/* Suggestion cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-lg w-full px-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s.text}
                  onClick={() => onSend(s.text)}
                  className={`flex items-start gap-3 rounded-2xl border p-4 text-left text-sm transition-all duration-200 hover:scale-[1.02] hover:shadow-lg active:scale-[0.98] ${s.bg}`}
                >
                  <s.icon className={`h-4 w-4 mt-0.5 shrink-0 ${s.color}`} />
                  <span className="text-muted-foreground leading-relaxed">
                    {s.text}
                  </span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="mx-auto max-w-3xl py-4">
            {messages.map((msg) => (
              <MessageBubble
                key={msg.id}
                message={msg}
                onRetry={msg.isError ? onRetry : undefined}
              />
            ))}
            {isLoading && <TypingIndicator />}
          </div>
        )}
      </div>

      {/* Input */}
      <ChatInput onSend={onSend} disabled={isLoading} />
    </div>
  );
}
