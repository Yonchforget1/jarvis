"use client";

import { useState, useEffect, useCallback } from "react";
import { MessageSquare, Brain, Wrench, Zap, X, ArrowRight } from "lucide-react";
import { FocusTrap } from "@/components/ui/focus-trap";

const STEPS = [
  {
    icon: MessageSquare,
    title: "Chat with JARVIS",
    description: "Ask anything - write code, search the web, manage files, or build games.",
    color: "text-primary",
    bg: "bg-primary/10",
  },
  {
    icon: Wrench,
    title: "16+ Professional Tools",
    description: "Filesystem, shell, web scraping, game dev, and more - all built in.",
    color: "text-blue-400",
    bg: "bg-blue-400/10",
  },
  {
    icon: Brain,
    title: "Self-Improving AI",
    description: "JARVIS learns from every task and gets better over time.",
    color: "text-purple-400",
    bg: "bg-purple-400/10",
  },
  {
    icon: Zap,
    title: "Multiple AI Backends",
    description: "Switch between Claude, GPT-4, Gemini, or open-source models.",
    color: "text-yellow-400",
    bg: "bg-yellow-400/10",
  },
];

const STORAGE_KEY = "jarvis-onboarding-seen";

export function Onboarding() {
  const [visible, setVisible] = useState(false);
  const [step, setStep] = useState(0);

  useEffect(() => {
    const seen = localStorage.getItem(STORAGE_KEY);
    if (!seen) {
      // Small delay so the page renders first
      const timer = setTimeout(() => setVisible(true), 500);
      return () => clearTimeout(timer);
    }
  }, []);

  const dismiss = useCallback(() => {
    setVisible(false);
    localStorage.setItem(STORAGE_KEY, "true");
  }, []);

  const next = useCallback(() => {
    if (step < STEPS.length - 1) {
      setStep(step + 1);
    } else {
      dismiss();
    }
  }, [step, dismiss]);

  const prev = useCallback(() => {
    if (step > 0) setStep(step - 1);
  }, [step]);

  // Keyboard: Escape to dismiss, Arrow keys to navigate
  useEffect(() => {
    if (!visible) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") dismiss();
      if (e.key === "ArrowRight" || e.key === "ArrowDown") next();
      if (e.key === "ArrowLeft" || e.key === "ArrowUp") prev();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [visible, dismiss, next, prev]);

  if (!visible) return null;

  const current = STEPS[step];
  const Icon = current.icon;

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center animate-fade-in">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={dismiss} />
      <FocusTrap>
      <div role="dialog" aria-modal="true" aria-label="Welcome to JARVIS" className="relative w-full max-w-sm mx-4 rounded-2xl border border-border/50 bg-card/95 backdrop-blur-xl shadow-2xl overflow-hidden animate-fade-in-up">
        {/* Close button */}
        <button
          onClick={dismiss}
          className="absolute top-3 right-3 rounded-lg p-1.5 text-muted-foreground/50 hover:text-foreground hover:bg-muted transition-colors z-10"
        >
          <X className="h-4 w-4" />
        </button>

        {/* Content */}
        <div className="flex flex-col items-center text-center px-8 pt-8 pb-6">
          <div className={`flex h-16 w-16 items-center justify-center rounded-2xl ${current.bg} mb-5`}>
            <Icon className={`h-8 w-8 ${current.color}`} />
          </div>
          <h3 className="text-lg font-semibold mb-2">{current.title}</h3>
          <p className="text-sm text-muted-foreground/70 leading-relaxed max-w-xs">
            {current.description}
          </p>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-border/30 bg-muted/20">
          {/* Step dots */}
          <div className="flex gap-1.5" role="tablist" aria-label="Onboarding steps">
            {STEPS.map((s, i) => (
              <button
                key={i}
                role="tab"
                aria-selected={i === step}
                aria-label={`Step ${i + 1}: ${s.title}`}
                onClick={() => setStep(i)}
                className={`h-1.5 rounded-full transition-all duration-300 cursor-pointer ${
                  i === step ? "w-4 bg-primary" : "w-1.5 bg-muted-foreground/20 hover:bg-muted-foreground/40"
                }`}
              />
            ))}
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2">
            {step < STEPS.length - 1 && (
              <button
                onClick={dismiss}
                className="text-xs text-muted-foreground/50 hover:text-foreground transition-colors px-2 py-1"
              >
                Skip
              </button>
            )}
            <button
              onClick={next}
              className="flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-xs font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              {step < STEPS.length - 1 ? "Next" : "Get Started"}
              <ArrowRight className="h-3 w-3" />
            </button>
          </div>
        </div>
      </div>
      </FocusTrap>
    </div>
  );
}
