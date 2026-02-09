"use client";

import { useEffect, useRef, useState } from "react";

const STATS = [
  { value: 16, suffix: "+", label: "Professional Tools" },
  { value: 4, suffix: "", label: "AI Backends" },
  { value: 24, suffix: "/7", label: "Automation" },
  { value: 100, suffix: "%", label: "Self-Improving" },
];

function useCountUp(end: number, duration: number, start: boolean) {
  const [count, setCount] = useState(0);

  useEffect(() => {
    if (!start) return;
    let startTime: number | null = null;
    let frame: number;

    const animate = (timestamp: number) => {
      if (!startTime) startTime = timestamp;
      const progress = Math.min((timestamp - startTime) / duration, 1);
      // Ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setCount(Math.round(eased * end));
      if (progress < 1) {
        frame = requestAnimationFrame(animate);
      }
    };

    frame = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(frame);
  }, [end, duration, start]);

  return count;
}

function StatItem({ value, suffix, label, delay }: { value: number; suffix: string; label: string; delay: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);
  const count = useCountUp(value, 1500 + delay, visible);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setTimeout(() => setVisible(true), delay);
          observer.disconnect();
        }
      },
      { threshold: 0.3 },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [delay]);

  return (
    <div ref={ref} className="text-center">
      <p className="text-4xl sm:text-5xl font-bold tracking-tight">
        <span className="bg-gradient-to-b from-foreground to-foreground/60 bg-clip-text text-transparent">
          {count}
        </span>
        <span className="text-primary">{suffix}</span>
      </p>
      <p className="mt-1.5 text-sm text-muted-foreground">{label}</p>
    </div>
  );
}

export function StatsCounter() {
  return (
    <section className="px-4 py-16 border-y border-border/10">
      <div className="mx-auto max-w-4xl grid grid-cols-2 sm:grid-cols-4 gap-8">
        {STATS.map((stat, i) => (
          <StatItem key={stat.label} {...stat} delay={i * 150} />
        ))}
      </div>
    </section>
  );
}
