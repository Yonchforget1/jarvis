"use client";

import { Bot, Sparkles } from "lucide-react";

export function TypingIndicator() {
  return (
    <div className="flex gap-3 px-4 py-3 animate-fade-in-up">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-secondary animate-glow-pulse">
        <Bot className="h-4 w-4 text-primary" />
      </div>
      <div className="flex items-center gap-2.5 rounded-2xl rounded-bl-md bg-secondary/80 backdrop-blur-sm border border-white/5 px-4 py-3">
        <Sparkles className="h-3.5 w-3.5 text-primary animate-pulse" />
        <span className="text-sm text-muted-foreground">Jarvis is thinking</span>
        <div className="flex gap-1 ml-1">
          <div className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse-dot" />
          <div
            className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse-dot"
            style={{ animationDelay: "0.2s" }}
          />
          <div
            className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse-dot"
            style={{ animationDelay: "0.4s" }}
          />
        </div>
      </div>
    </div>
  );
}
