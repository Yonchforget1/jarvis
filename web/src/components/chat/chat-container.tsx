"use client";

import { useEffect, useRef } from "react";
import {
  MessageSquare,
  Zap,
  Code,
  Globe,
  Gamepad2,
  Sparkles,
  Keyboard,
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
  onStop?: () => void;
}

const SUGGESTIONS = [
  {
    icon: Code,
    text: "Write a Python script that generates a fractal image",
    color: "text-green-400",
    bg: "bg-green-400/10 border-green-400/20 hover:bg-green-400/15",
  },
  {
    icon: Globe,
    text: "Search the web for the latest AI news",
    color: "text-orange-400",
    bg: "bg-orange-400/10 border-orange-400/20 hover:bg-orange-400/15",
  },
  {
    icon: Gamepad2,
    text: "Create a platformer game called SpaceRunner",
    color: "text-purple-400",
    bg: "bg-purple-400/10 border-purple-400/20 hover:bg-purple-400/15",
  },
  {
    icon: Zap,
    text: "List all files in the current directory",
    color: "text-blue-400",
    bg: "bg-blue-400/10 border-blue-400/20 hover:bg-blue-400/15",
  },
];

export function ChatContainer({
  messages,
  isLoading,
  onSend,
  onRetry,
  onStop,
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
            {/* Logo with animated gradient ring */}
            <div className="relative mb-8">
              <div className="absolute -inset-1 rounded-3xl bg-gradient-to-r from-primary/20 via-purple-500/20 to-cyan-500/20 blur-lg animate-glow-pulse" />
              <div className="relative flex h-20 w-20 items-center justify-center rounded-3xl bg-card border border-border/50">
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

            {/* Keyboard shortcut hint */}
            <div className="mt-8 flex items-center gap-1.5 text-[10px] text-muted-foreground/40">
              <Keyboard className="h-3 w-3" />
              <span>
                Press{" "}
                <kbd className="rounded bg-muted px-1 py-0.5 font-mono text-[9px]">Ctrl+K</kbd>{" "}
                for new chat
              </span>
            </div>
          </div>
        ) : (
          <div className="mx-auto max-w-3xl py-4">
            {messages.map((msg) => (
              <MessageBubble
                key={msg.id}
                message={msg}
                onRetry={msg.isError ? onRetry : undefined}
                onStop={msg.isStreaming ? onStop : undefined}
              />
            ))}
            {isLoading && !messages.some((m) => m.isStreaming) && (
              <TypingIndicator />
            )}
          </div>
        )}
      </div>

      {/* Input */}
      <ChatInput onSend={onSend} disabled={isLoading} />
    </div>
  );
}
