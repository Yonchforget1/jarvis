"use client";

import { useEffect, useRef, useState } from "react";
import { Folder, Terminal, Globe, Gamepad2, Brain, Cpu } from "lucide-react";

const FEATURES = [
  {
    icon: Folder,
    title: "Filesystem Control",
    description:
      "Read, write, move, copy, and manage files and directories. Full filesystem access with safety checks.",
  },
  {
    icon: Terminal,
    title: "Code Execution",
    description:
      "Run Python scripts and shell commands with real-time output. Build, test, and deploy from natural language.",
  },
  {
    icon: Globe,
    title: "Web Intelligence",
    description:
      "Search the web, scrape pages, extract data with CSS selectors. Stay informed with real-time information.",
  },
  {
    icon: Gamepad2,
    title: "Game Development",
    description:
      "Scaffold complete game projects with Pygame or Ursina. Generate assets and build playable games in minutes.",
  },
  {
    icon: Brain,
    title: "Self-Improving Memory",
    description:
      "Learns from every task and never makes the same mistake twice. Persistent memory across sessions.",
  },
  {
    icon: Cpu,
    title: "Multi-Backend AI",
    description:
      "Switch between Claude, GPT-4, and Gemini with one config change. Always use the best model for the job.",
  },
];

function FeatureCard({ feature, delay }: { feature: typeof FEATURES[number]; delay: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    let timer: ReturnType<typeof setTimeout> | null = null;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          timer = setTimeout(() => setVisible(true), delay);
          observer.disconnect();
        }
      },
      { threshold: 0.15 },
    );
    observer.observe(el);
    return () => {
      observer.disconnect();
      if (timer) clearTimeout(timer);
    };
  }, [delay]);

  return (
    <div
      ref={ref}
      className={`group rounded-2xl border border-white/5 bg-white/[0.02] p-6 backdrop-blur-sm hover:border-primary/20 hover:bg-white/[0.04] transition-all duration-500 ${
        visible
          ? "opacity-100 translate-y-0"
          : "opacity-0 translate-y-6"
      }`}
    >
      <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 group-hover:bg-primary/20 group-hover:scale-110 transition-all duration-300">
        <feature.icon className="h-5 w-5 text-primary" />
      </div>
      <h3 className="mb-2 text-lg font-semibold">{feature.title}</h3>
      <p className="text-sm text-muted-foreground leading-relaxed">
        {feature.description}
      </p>
    </div>
  );
}

export function Features() {
  return (
    <section id="features" className="px-4 py-24">
      <div className="mx-auto max-w-6xl">
        <div className="text-center mb-16">
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight mb-4">
            Built for Professionals
          </h2>
          <p className="text-muted-foreground max-w-xl mx-auto">
            16+ production-ready tools that execute real tasks on real computers.
            Not prompts. Not suggestions. Execution.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {FEATURES.map((feature, i) => (
            <FeatureCard key={feature.title} feature={feature} delay={i * 100} />
          ))}
        </div>
      </div>
    </section>
  );
}
