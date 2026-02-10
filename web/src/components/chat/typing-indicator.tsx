"use client";

import { useState, useEffect, useRef } from "react";
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
  const [elapsed, setElapsed] = useState(0);
  const startRef = useRef(Date.now());

  // Single interval handles both elapsed time and phrase cycling
  useEffect(() => {
    const timer = setInterval(() => {
      const secs = Math.floor((Date.now() - startRef.current) / 1000);
      setElapsed(secs);
      if (secs > 0 && secs % 3 === 0) {
        setPhraseIndex((prev) => (prev + 1) % THINKING_PHRASES.length);
      }
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const formatElapsed = (s: number) => {
    if (s < 5) return "";
    if (s < 60) return `${s}s`;
    return `${Math.floor(s / 60)}m ${s % 60}s`;
  };

  return (
    <div className="flex gap-3 px-4 py-3 animate-fade-in-up" role="status" aria-live="polite" aria-label="JARVIS is thinking">
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
        {elapsed >= 5 && (
          <span className="text-[10px] text-muted-foreground/40 font-mono tabular-nums ml-1">
            {formatElapsed(elapsed)}
          </span>
        )}
      </div>
    </div>
  );
}
