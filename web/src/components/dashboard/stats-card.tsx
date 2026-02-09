import type { LucideIcon } from "lucide-react";

interface StatsCardProps {
  title: string;
  value: string | number;
  description: string;
  icon: LucideIcon;
  iconColor?: string;
  bgColor?: string;
}

export function StatsCard({
  title,
  value,
  description,
  icon: Icon,
  iconColor = "text-primary",
  bgColor = "bg-muted",
}: StatsCardProps) {
  return (
    <div className="group rounded-2xl border border-border/50 bg-card/50 p-5 transition-all duration-300 hover:border-border hover:bg-card/80 animate-fade-in-up">
      <div className="flex items-center justify-between mb-3">
        <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground/60">
          {title}
        </p>
        <div className={`rounded-xl ${bgColor} p-2.5 ${iconColor} transition-transform duration-300 group-hover:scale-110`}>
          <Icon className="h-4 w-4" />
        </div>
      </div>
      <p className="text-3xl font-bold tracking-tight">{value}</p>
      <p className="mt-1 text-xs text-muted-foreground/60">{description}</p>
    </div>
  );
}
