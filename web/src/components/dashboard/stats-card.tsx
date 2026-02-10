"use client";

import { useEffect, useState, useRef } from "react";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import type { LucideIcon } from "lucide-react";

interface TrendInfo {
  direction: "up" | "down" | "stable";
  label: string;
}

interface StatsCardProps {
  title: string;
  value: string | number;
  description: string;
  icon: LucideIcon;
  iconColor?: string;
  bgColor?: string;
  trend?: TrendInfo;
}

function AnimatedNumber({ value }: { value: number }) {
  const [display, setDisplay] = useState(0);
  const frameRef = useRef<number>(0);
  const startRef = useRef<number>(0);
  const duration = 800; // ms

  useEffect(() => {
    const startValue = display;
    const diff = value - startValue;
    if (diff === 0) return;

    startRef.current = performance.now();

    const animate = (now: number) => {
      const elapsed = now - startRef.current;
      const progress = Math.min(elapsed / duration, 1);
      // Ease out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplay(Math.round(startValue + diff * eased));

      if (progress < 1) {
        frameRef.current = requestAnimationFrame(animate);
      }
    };

    frameRef.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(frameRef.current);
    // Only re-animate when the target value changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  return <>{display.toLocaleString()}</>;
}

function AnimatedValue({ value }: { value: string | number }) {
  if (typeof value === "number") {
    return <AnimatedNumber value={value} />;
  }
  // Try to parse a number from strings like "1.2K", "3.5M"
  const match = value.match(/^([\d.]+)(.*)$/);
  if (match) {
    const num = parseFloat(match[1]);
    const suffix = match[2];
    if (!isNaN(num) && suffix) {
      return (
        <>
          <AnimatedNumber value={Math.round(num * 10) / 10} />
          {suffix}
        </>
      );
    }
  }
  return <>{value}</>;
}

function TrendBadge({ trend }: { trend: TrendInfo }) {
  const config = {
    up: { icon: TrendingUp, color: "text-green-400 bg-green-400/10" },
    down: { icon: TrendingDown, color: "text-red-400 bg-red-400/10" },
    stable: { icon: Minus, color: "text-muted-foreground/60 bg-muted" },
  }[trend.direction];
  const TIcon = config.icon;
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 text-[10px] font-medium ${config.color}`}>
      <TIcon className="h-2.5 w-2.5" />
      {trend.label}
    </span>
  );
}

export function StatsCard({
  title,
  value,
  description,
  icon: Icon,
  iconColor = "text-primary",
  bgColor = "bg-muted",
  trend,
}: StatsCardProps) {
  const prevValueRef = useRef(value);
  const [flash, setFlash] = useState(false);

  useEffect(() => {
    if (prevValueRef.current !== value) {
      prevValueRef.current = value;
      setFlash(true);
      const timer = setTimeout(() => setFlash(false), 600);
      return () => clearTimeout(timer);
    }
  }, [value]);

  return (
    <div
      role="region"
      aria-label={`${title} statistics`}
      className={`group rounded-2xl border border-border/50 bg-card/50 p-5 transition-all duration-300 hover:border-border hover:bg-card/80 animate-fade-in-up ${
        flash ? "ring-1 ring-primary/30 bg-primary/5" : ""
      }`}
    >
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-xs font-medium uppercase tracking-wider text-muted-foreground/60">
          {title}
        </h4>
        <div className={`rounded-xl ${bgColor} p-2.5 ${iconColor} transition-transform duration-300 group-hover:scale-110`}>
          <Icon className="h-4 w-4" />
        </div>
      </div>
      <div className="flex items-baseline gap-2">
        <p className="text-3xl font-bold tracking-tight tabular-nums">
          <AnimatedValue value={value} />
        </p>
        {trend && <TrendBadge trend={trend} />}
      </div>
      <p className="mt-1 text-xs text-muted-foreground/60">{description}</p>
    </div>
  );
}
