"use client";

import { useState, useEffect } from "react";
import { Bot } from "lucide-react";

const THINKING_PHRASES = [
  "Thinking",
  "Analyzing",
  "Processing",
  "Reasoning",
  "Working on it",
];

export function TypingIndicator() {
  const [phraseIndex, setPhraseIndex] = useState(0);

  // Cycle through phrases
  useEffect(() => {
    const timer = setInterval(() => {
      setPhraseIndex((prev) => (prev + 1) % THINKING_PHRASES.length);
    }, 3000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="flex gap-3 px-4 py-3 animate-fade-in-up">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/20 animate-glow-pulse">
        <Bot className="h-4 w-4 text-primary" />
      </div>
      <div className="flex items-center gap-2.5 rounded-2xl rounded-bl-md bg-secondary/80 backdrop-blur-sm border border-primary/20 px-4 py-3">
        <span className="text-sm text-muted-foreground/80 transition-all duration-300">
          {THINKING_PHRASES[phraseIndex]}
        </span>
        <div className="flex gap-1 ml-0.5">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="h-1.5 w-1.5 rounded-full bg-primary animate-typing-wave"
              style={{ animationDelay: `${i * 0.15}s` }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
