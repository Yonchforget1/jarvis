"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  MessageSquare,
  LayoutDashboard,
  Wrench,
  Brain,
  Settings,
} from "lucide-react";
import { useSessionContext } from "@/lib/session-context";

const NAV_ITEMS = [
  { href: "/chat", label: "Chat", icon: MessageSquare },
  { href: "/dashboard", label: "Board", icon: LayoutDashboard },
  { href: "/tools", label: "Tools", icon: Wrench },
  { href: "/learnings", label: "Learn", icon: Brain },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function MobileNav() {
  const pathname = usePathname();
  const { unreadCount, isProcessing } = useSessionContext();

  return (
    <nav aria-label="Mobile navigation" className="fixed bottom-0 left-0 right-0 z-40 lg:hidden border-t border-border/50 bg-background/80 backdrop-blur-xl">
      <div className="flex items-center justify-around py-1.5 px-2" role="list">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-label={item.label}
              aria-current={isActive ? "page" : undefined}
              className={`relative flex flex-col items-center gap-0.5 px-3 py-1.5 rounded-xl transition-all duration-200 active:scale-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 ${
                isActive
                  ? "text-primary"
                  : "text-muted-foreground/60 active:text-foreground"
              }`}
            >
              <div className="relative">
                <item.icon className={`h-5 w-5 transition-transform duration-200 ${isActive ? "text-primary scale-110" : ""}`} />
                {item.label === "Chat" && unreadCount > 0 && !isActive && (
                  <span className="absolute -top-1 -right-1.5 flex h-3.5 min-w-3.5 items-center justify-center rounded-full bg-primary px-0.5 text-[8px] font-bold text-primary-foreground">
                    {unreadCount > 9 ? "9+" : unreadCount}
                  </span>
                )}
                {item.label === "Chat" && isActive && isProcessing && (
                  <span className="absolute -top-1 -right-1.5 h-2.5 w-2.5 rounded-full bg-primary animate-pulse" />
                )}
              </div>
              <span className={`text-[10px] font-medium ${isActive ? "text-primary" : ""}`}>
                {item.label}
              </span>
              {isActive && (
                <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 h-1 w-1 rounded-full bg-primary" />
              )}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
