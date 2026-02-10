"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { ArrowRight, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";

const TERMINAL_LINES = [
  { type: "user", text: "Create a platformer game called SpaceRunner" },
  { type: "tool", text: "  [tool: create_game_project]" },
  { type: "tool", text: "  [tool: generate_game_asset] x4" },
  { type: "tool", text: "  [tool: write_file]" },
  { type: "tool", text: "  [tool: run_shell]" },
  {
    type: "bot",
    text: "Done. Complete platformer with enemies, coins, physics, and scoring. Ready to play at /games/SpaceRunner/",
  },
];

function AnimatedTerminal() {
  const [visibleLines, setVisibleLines] = useState(0);
  const [currentChar, setCurrentChar] = useState(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (visibleLines >= TERMINAL_LINES.length) {
      // Reset after a pause
      timerRef.current = setTimeout(() => {
        setVisibleLines(0);
        setCurrentChar(0);
      }, 4000);
      return () => { if (timerRef.current) clearTimeout(timerRef.current); };
    }

    const line = TERMINAL_LINES[visibleLines];
    if (currentChar < line.text.length) {
      const speed = line.type === "tool" ? 15 : 30;
      timerRef.current = setTimeout(() => setCurrentChar((c) => c + 1), speed);
    } else {
      const delay = line.type === "tool" ? 300 : 600;
      timerRef.current = setTimeout(() => {
        setVisibleLines((v) => v + 1);
        setCurrentChar(0);
      }, delay);
    }
    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, [visibleLines, currentChar]);

  return (
    <div aria-hidden="true" className="mx-auto mt-16 max-w-2xl rounded-xl border border-white/10 bg-black/40 backdrop-blur-xl overflow-hidden shadow-2xl shadow-primary/5">
      <div className="flex items-center gap-1.5 border-b border-white/5 px-4 py-2.5">
        <div className="h-2.5 w-2.5 rounded-full bg-red-500/60" />
        <div className="h-2.5 w-2.5 rounded-full bg-yellow-500/60" />
        <div className="h-2.5 w-2.5 rounded-full bg-green-500/60" />
        <span className="ml-3 text-[10px] text-muted-foreground">jarvis terminal</span>
      </div>
      <div className="p-4 font-mono text-sm space-y-2 min-h-[180px]">
        {TERMINAL_LINES.map((line, i) => {
          if (i > visibleLines) return null;
          const isCurrentLine = i === visibleLines;
          const displayText = isCurrentLine ? line.text.slice(0, currentChar) : line.text;
          const showCursor = isCurrentLine && visibleLines < TERMINAL_LINES.length;

          if (line.type === "user") {
            return (
              <p key={i}>
                <span className="text-green-400">You:</span>{" "}
                <span className="text-zinc-300">
                  {displayText}
                  {showCursor && <span className="inline-block w-1.5 h-4 bg-green-400/60 animate-pulse rounded-sm ml-0.5 align-text-bottom" />}
                </span>
              </p>
            );
          }
          if (line.type === "tool") {
            return (
              <p key={i} className="text-muted-foreground text-xs">
                {displayText}
                {showCursor && <span className="inline-block w-1.5 h-3 bg-muted-foreground/40 animate-pulse rounded-sm ml-0.5 align-text-bottom" />}
              </p>
            );
          }
          return (
            <p key={i}>
              <span className="text-primary">Jarvis:</span>{" "}
              <span className="text-zinc-300">
                {displayText}
                {showCursor && <span className="inline-block w-1.5 h-4 bg-primary/60 animate-pulse rounded-sm ml-0.5 align-text-bottom" />}
              </span>
            </p>
          );
        })}
      </div>
    </div>
  );
}

export function Hero() {
  return (
    <section className="relative overflow-hidden px-4 pt-32 pb-20">
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-to-b from-primary/5 via-transparent to-transparent" />
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 h-[500px] w-[500px] rounded-full bg-primary/10 blur-[120px]" />

      <div className="relative mx-auto max-w-4xl text-center">
        <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-4 py-1.5">
          <Zap className="h-3.5 w-3.5 text-primary" />
          <span className="text-xs font-medium text-primary">
            16+ Professional Tools Built In
          </span>
        </div>

        <h1 className="mb-6 text-5xl sm:text-6xl lg:text-7xl font-bold tracking-tight">
          The AI Agent That
          <span className="block bg-gradient-to-r from-primary via-purple-400 to-pink-400 bg-clip-text text-transparent">
            Actually Gets Things Done
          </span>
        </h1>

        <p className="mx-auto mb-10 max-w-2xl text-lg text-muted-foreground">
          Jarvis controls computers, builds software, creates games, scrapes the web,
          and gets smarter with every task. Not a chatbot. A digital workforce.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <Button asChild size="lg" className="gap-2 rounded-xl px-8 bg-gradient-to-r from-primary to-purple-500 hover:from-primary/90 hover:to-purple-500/90">
            <Link href="/register">
              Start Free Trial
              <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
          <Button asChild variant="outline" size="lg" className="gap-2 rounded-xl px-8">
            <Link href="#features">See What It Can Do</Link>
          </Button>
        </div>

        {/* Animated terminal */}
        <AnimatedTerminal />
      </div>
    </section>
  );
}
