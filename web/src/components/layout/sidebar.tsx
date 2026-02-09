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
  Settings,
  Sparkles,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";

const NAV_ITEMS = [
  { href: "/chat", label: "Chat", icon: MessageSquare },
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/tools", label: "Tools", icon: Wrench },
  { href: "/learnings", label: "Learnings", icon: Brain },
  { href: "/settings", label: "Settings", icon: Settings },
];

const TOOL_GROUPS = [
  { label: "Filesystem", icon: Folder, count: 7, color: "text-blue-400" },
  { label: "Execution", icon: Terminal, count: 2, color: "text-green-400" },
  { label: "Web", icon: Globe, count: 2, color: "text-orange-400" },
  { label: "Game Dev", icon: Gamepad2, count: 2, color: "text-purple-400" },
  { label: "Memory", icon: Lightbulb, count: 3, color: "text-yellow-400" },
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
        <div className="flex items-center gap-2.5">
          <div className="relative">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/20 border border-primary/10">
              <span className="text-sm font-bold text-primary">J</span>
            </div>
            <div className="absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full bg-green-500 border-2 border-sidebar" />
          </div>
          <div>
            <h1 className="text-sm font-semibold tracking-wide">JARVIS</h1>
            <p className="text-[10px] text-muted-foreground/60">AI Agent Platform</p>
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
      <nav className="flex-1 space-y-0.5 p-3 overflow-y-auto">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onClose}
              className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-all duration-200 ${
                isActive
                  ? "bg-primary/10 text-primary shadow-sm shadow-primary/5"
                  : "text-muted-foreground hover:bg-white/5 hover:text-foreground"
              }`}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
              {item.label === "Chat" && (
                <Sparkles className="ml-auto h-3 w-3 text-primary/50" />
              )}
            </Link>
          );
        })}

        <Separator className="!my-3 bg-white/5" />

        {/* Tool groups */}
        <p className="px-3 py-1.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground/50">
          Tool Groups
        </p>
        {TOOL_GROUPS.map((group) => (
          <div
            key={group.label}
            className="flex items-center justify-between rounded-xl px-3 py-2 text-xs text-muted-foreground/70"
          >
            <div className="flex items-center gap-2.5">
              <group.icon className={`h-3.5 w-3.5 ${group.color}`} />
              <span>{group.label}</span>
            </div>
            <span className="rounded-full bg-white/5 px-2 py-0.5 text-[10px] font-mono">
              {group.count}
            </span>
          </div>
        ))}
      </nav>

      {/* User */}
      <div className="border-t border-white/5 p-3">
        <div className="flex items-center justify-between rounded-xl px-2 py-1.5">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-primary/30 to-primary/10 text-xs font-semibold text-primary border border-primary/20">
              {user?.username?.[0]?.toUpperCase() || "U"}
            </div>
            <div>
              <span className="text-sm font-medium">{user?.username || "User"}</span>
              <p className="text-[10px] text-muted-foreground/50">Free Plan</p>
            </div>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={logout}
            className="h-8 w-8 text-muted-foreground/50 hover:text-red-400 hover:bg-red-400/10 transition-all"
          >
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
