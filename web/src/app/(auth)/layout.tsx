"use client";

import { Code, Globe, Brain, Wrench, Zap } from "lucide-react";

const FEATURES = [
  { icon: Code, label: "Write & execute code in real-time" },
  { icon: Globe, label: "Search and scrape the web" },
  { icon: Brain, label: "Self-improving AI that learns" },
  { icon: Wrench, label: "16+ professional tools built-in" },
  { icon: Zap, label: "Runs on Claude, GPT-4, and Gemini" },
];

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative flex min-h-screen bg-background overflow-hidden">
      {/* Left: Feature panel (desktop only) */}
      <div className="hidden lg:flex lg:w-[45%] items-center justify-center relative">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/10 via-purple-500/5 to-transparent" />
        <div className="absolute top-1/4 -left-32 h-64 w-64 rounded-full bg-primary/10 blur-3xl" />
        <div className="absolute bottom-1/3 right-0 h-48 w-48 rounded-full bg-purple-500/10 blur-3xl" />

        <div className="relative z-10 max-w-md px-12 py-16">
          {/* Logo */}
          <div className="flex items-center gap-3 mb-12">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/20 border border-primary/10">
              <span className="text-xl font-bold text-primary">J</span>
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-wide">JARVIS</h1>
              <p className="text-xs text-muted-foreground/60">AI Agent Platform</p>
            </div>
          </div>

          {/* Tagline */}
          <h2 className="text-3xl font-bold tracking-tight mb-3">
            Your AI workforce,
            <br />
            <span className="text-primary">ready to deploy.</span>
          </h2>
          <p className="text-sm text-muted-foreground/70 mb-10 leading-relaxed">
            The most advanced AI agent platform that executes real tasks on real
            computers using professional software.
          </p>

          {/* Features */}
          <div className="space-y-4">
            {FEATURES.map((f) => (
              <div key={f.label} className="flex items-center gap-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-primary/10">
                  <f.icon className="h-4 w-4 text-primary" />
                </div>
                <span className="text-sm text-muted-foreground">{f.label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right: Auth form */}
      <div className="flex flex-1 items-center justify-center p-4 relative">
        <div className="absolute inset-0 bg-gradient-to-br from-transparent via-transparent to-primary/5 lg:hidden" />
        <div className="absolute top-1/4 -right-32 h-64 w-64 rounded-full bg-primary/5 blur-3xl lg:hidden" />

        <div className="relative z-10 w-full animate-fade-in-up">{children}</div>
      </div>
    </div>
  );
}
