"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  MessageSquare,
  LayoutDashboard,
  Wrench,
  Brain,
  LogOut,
  X,
  Folder,
  Terminal,
  Globe,
  Gamepad2,
  Lightbulb,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";

const NAV_ITEMS = [
  { href: "/chat", label: "Chat", icon: MessageSquare },
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/tools", label: "Tools", icon: Wrench },
  { href: "/learnings", label: "Learnings", icon: Brain },
];

const TOOL_GROUPS = [
  { label: "Filesystem", icon: Folder, count: 7 },
  { label: "Execution", icon: Terminal, count: 2 },
  { label: "Web", icon: Globe, count: 2 },
  { label: "Game Dev", icon: Gamepad2, count: 2 },
  { label: "Memory", icon: Lightbulb, count: 3 },
];

interface SidebarProps {
  onClose?: () => void;
}

export function Sidebar({ onClose }: SidebarProps) {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <div className="flex h-full w-[280px] flex-col border-r border-white/5 bg-sidebar">
      {/* Header */}
      <div className="flex items-center justify-between p-4">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/20">
            <span className="text-sm font-bold text-primary">J</span>
          </div>
          <div>
            <h1 className="text-sm font-semibold">JARVIS</h1>
            <p className="text-[10px] text-muted-foreground">AI Agent Platform</p>
          </div>
        </div>
        {onClose && (
          <Button variant="ghost" size="icon" onClick={onClose} className="h-8 w-8 lg:hidden">
            <X className="h-4 w-4" />
          </Button>
        )}
      </div>

      <Separator className="bg-white/5" />

      {/* Navigation */}
      <nav className="flex-1 space-y-1 p-3">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onClose}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
                isActive
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-white/5 hover:text-foreground"
              }`}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}

        <Separator className="my-3 bg-white/5" />

        {/* Tool groups */}
        <p className="px-3 py-1 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
          Tools
        </p>
        {TOOL_GROUPS.map((group) => (
          <div
            key={group.label}
            className="flex items-center justify-between rounded-lg px-3 py-1.5 text-xs text-muted-foreground"
          >
            <div className="flex items-center gap-2">
              <group.icon className="h-3.5 w-3.5" />
              {group.label}
            </div>
            <span className="rounded-full bg-white/5 px-1.5 py-0.5 text-[10px]">
              {group.count}
            </span>
          </div>
        ))}
      </nav>

      {/* User */}
      <div className="border-t border-white/5 p-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/20 text-xs font-medium text-primary">
              {user?.username?.[0]?.toUpperCase() || "U"}
            </div>
            <span className="text-sm">{user?.username || "User"}</span>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={logout}
            className="h-8 w-8 text-muted-foreground hover:text-destructive"
          >
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
