"use client";

import { useEffect, useState, useRef } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useTheme } from "next-themes";
import { Menu, Search, Wifi, WifiOff, Loader2, Sun, Moon, ChevronRight, Bell, Settings, Shield, LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useConnection } from "@/hooks/use-connection";
import { useSessionContext } from "@/lib/session-context";
import { useAuth } from "@/lib/auth";
import { useToast } from "@/components/ui/toast";

const PAGE_TITLES: Record<string, string> = {
  "/chat": "Chat",
  "/dashboard": "Dashboard",
  "/tools": "Tools",
  "/learnings": "Learnings",
  "/settings": "Settings",
};

interface HeaderProps {
  onMenuClick: () => void;
}

export function Header({ onMenuClick }: HeaderProps) {
  const pathname = usePathname();
  const router = useRouter();
  const title = PAGE_TITLES[pathname] || "Jarvis";
  const { status, latency } = useConnection();
  const { theme, setTheme } = useTheme();
  const { selectedSessionName, isProcessing, unreadCount, clearUnread } = useSessionContext();
  const { user, logout } = useAuth();
  const toast = useToast();
  const [profileOpen, setProfileOpen] = useState(false);
  const profileRef = useRef<HTMLDivElement>(null);

  // Close profile dropdown on click outside
  useEffect(() => {
    if (!profileOpen) return;
    const handleClick = (e: MouseEvent) => {
      if (profileRef.current && !profileRef.current.contains(e.target as Node)) {
        setProfileOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [profileOpen]);

  // Listen for token expiry warnings
  useEffect(() => {
    const handler = (e: Event) => {
      const { remainingMs } = (e as CustomEvent<{ remainingMs: number }>).detail;
      const mins = Math.round(remainingMs / 60000);
      toast.warning(`Session expires in ${mins} minute${mins !== 1 ? "s" : ""}. Please save your work and log in again.`);
    };
    window.addEventListener("token-expiry-warning", handler);
    return () => window.removeEventListener("token-expiry-warning", handler);
  }, [toast]);

  return (
    <header role="banner" className="flex h-14 items-center justify-between border-b border-border/50 bg-background/80 backdrop-blur-xl px-4">
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="icon"
          onClick={onMenuClick}
          aria-label="Open menu"
          className="h-8 w-8 lg:hidden"
        >
          <Menu className="h-4 w-4" />
        </Button>
        <div className="flex items-center gap-1.5 min-w-0">
          <span className="text-sm text-muted-foreground/50 hidden sm:inline shrink-0">JARVIS</span>
          <ChevronRight className="h-3 w-3 text-muted-foreground/30 hidden sm:block shrink-0" />
          <h2 className="text-sm font-semibold shrink-0">{title}</h2>
          {pathname === "/chat" && selectedSessionName && (
            <>
              <ChevronRight className="h-3 w-3 text-muted-foreground/30 shrink-0" />
              <span
                className="text-sm text-muted-foreground/60 truncate max-w-[200px]"
                title={selectedSessionName}
              >
                {selectedSessionName}
              </span>
            </>
          )}
          {pathname === "/chat" && isProcessing && (
            <div className="flex items-center gap-1 ml-1">
              {[0, 1, 2].map((i) => (
                <div
                  key={i}
                  className="h-1 w-1 rounded-full bg-primary animate-typing-wave"
                  style={{ animationDelay: `${i * 0.15}s` }}
                />
              ))}
            </div>
          )}
        </div>
      </div>
      <div className="flex items-center gap-2">
        {/* Connection status */}
        {status === "connected" ? (
          <div className="hidden sm:flex items-center gap-1.5 rounded-full bg-green-500/10 border border-green-500/20 px-2.5 py-1 transition-all">
            <Wifi className="h-3 w-3 text-green-500" />
            <span className="text-[10px] font-medium text-green-500">
              Connected{latency !== null && ` (${latency}ms)`}
            </span>
          </div>
        ) : status === "disconnected" ? (
          <div className="hidden sm:flex items-center gap-1.5 rounded-full bg-red-500/10 border border-red-500/20 px-2.5 py-1 animate-pulse">
            <WifiOff className="h-3 w-3 text-red-400" />
            <span className="text-[10px] font-medium text-red-400">Disconnected</span>
          </div>
        ) : status === "degraded" ? (
          <div className="hidden sm:flex items-center gap-1.5 rounded-full bg-yellow-500/10 border border-yellow-500/20 px-2.5 py-1">
            <Wifi className="h-3 w-3 text-yellow-500" />
            <span className="text-[10px] font-medium text-yellow-500">
              Slow{latency !== null && ` (${latency}ms)`}
            </span>
          </div>
        ) : (
          <div className="hidden sm:flex items-center gap-1.5 rounded-full bg-yellow-500/10 border border-yellow-500/20 px-2.5 py-1">
            <Loader2 className="h-3 w-3 text-yellow-500 animate-spin" />
            <span className="text-[10px] font-medium text-yellow-500">Connecting</span>
          </div>
        )}

        {/* Mobile connection dot */}
        <div className="flex sm:hidden items-center">
          <div
            className={`h-2 w-2 rounded-full ${
              status === "connected"
                ? "bg-green-500"
                : status === "disconnected"
                ? "bg-red-500 animate-pulse"
                : status === "degraded"
                ? "bg-yellow-500"
                : "bg-yellow-500 animate-pulse"
            }`}
          />
        </div>

        {/* Mobile search / command palette trigger */}
        <Button
          variant="ghost"
          size="icon"
          onClick={() => {
            document.dispatchEvent(new KeyboardEvent("keydown", { key: "k", ctrlKey: true }));
          }}
          className="h-8 w-8 sm:hidden text-muted-foreground hover:text-foreground"
        >
          <Search className="h-4 w-4" />
          <span className="sr-only">Search</span>
        </Button>

        {/* Notification bell */}
        {unreadCount > 0 && (
          <Button
            variant="ghost"
            size="icon"
            onClick={clearUnread}
            className="relative h-8 w-8 text-muted-foreground hover:text-foreground"
            aria-label={`${unreadCount} unread notification${unreadCount > 1 ? "s" : ""}`}
          >
            <Bell className="h-4 w-4" />
            <span className="absolute -top-0.5 -right-0.5 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-primary px-1 text-[9px] font-bold text-primary-foreground">
              {unreadCount > 99 ? "99+" : unreadCount}
            </span>
          </Button>
        )}

        {/* Theme toggle */}
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          className="h-8 w-8 text-muted-foreground hover:text-foreground"
        >
          <Sun className="h-4 w-4 rotate-0 scale-100 transition-transform dark:-rotate-90 dark:scale-0" />
          <Moon className="absolute h-4 w-4 rotate-90 scale-0 transition-transform dark:rotate-0 dark:scale-100" />
          <span className="sr-only">Toggle theme</span>
        </Button>

        {/* Command palette trigger */}
        <button
          onClick={() => {
            document.dispatchEvent(new KeyboardEvent("keydown", { key: "k", ctrlKey: true }));
          }}
          className="hidden sm:flex items-center gap-2 h-8 rounded-lg border border-border/50 bg-muted/50 px-3 text-xs text-muted-foreground hover:bg-muted transition-colors"
        >
          <Search className="h-3 w-3" />
          <span>Search</span>
          <kbd className="rounded bg-background px-1 py-0.5 text-[10px] font-mono border border-border/50">
            Ctrl+K
          </kbd>
        </button>

        {/* User avatar / profile dropdown */}
        {user && (
          <div ref={profileRef} className="relative">
            <button
              onClick={() => setProfileOpen(!profileOpen)}
              className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/20 border border-primary/20 text-xs font-bold text-primary hover:bg-primary/30 transition-colors"
              title={user.username}
              aria-label="User menu"
              aria-expanded={profileOpen}
            >
              {user.username.charAt(0).toUpperCase()}
            </button>
            {profileOpen && (
              <div className="absolute right-0 top-full mt-2 w-56 rounded-xl border border-border/50 bg-background shadow-xl overflow-hidden z-50 animate-fade-in-up" style={{ animationDuration: "0.12s" }}>
                <div className="px-4 py-3 border-b border-border/30">
                  <p className="text-sm font-medium truncate">{user.username}</p>
                  <p className="text-[10px] text-muted-foreground/50 truncate">{user.email}</p>
                </div>
                <div className="py-1">
                  <button
                    onClick={() => { router.push("/settings"); setProfileOpen(false); }}
                    className="flex w-full items-center gap-2.5 px-4 py-2 text-xs text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors"
                  >
                    <Settings className="h-3.5 w-3.5" />
                    Settings
                  </button>
                  <button
                    onClick={() => { router.push("/admin"); setProfileOpen(false); }}
                    className="flex w-full items-center gap-2.5 px-4 py-2 text-xs text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors"
                  >
                    <Shield className="h-3.5 w-3.5" />
                    Admin
                  </button>
                </div>
                <div className="border-t border-border/30 py-1">
                  <button
                    onClick={() => { logout(); setProfileOpen(false); }}
                    className="flex w-full items-center gap-2.5 px-4 py-2 text-xs text-red-400/80 hover:text-red-400 hover:bg-red-500/5 transition-colors"
                  >
                    <LogOut className="h-3.5 w-3.5" />
                    Log out
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </header>
  );
}
