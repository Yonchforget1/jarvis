"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { SessionProvider, useSessionContext } from "@/lib/session-context";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { MobileNav } from "@/components/layout/mobile-nav";
import { CommandPalette } from "@/components/command-palette";
import { KeyboardShortcuts } from "@/components/keyboard-shortcuts";
import { TopLoader } from "@/components/top-loader";
import { ErrorBoundary } from "@/components/error-boundary";
import { PageTransition } from "@/components/page-transition";
import { ConnectionMonitor } from "@/components/connection-monitor";
import { Onboarding } from "@/components/onboarding";
import { PWAInstall } from "@/components/pwa-install";

function AppLayoutInner({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [focusMode, setFocusMode] = useState(false);
  const { selectedSessionId, selectSession } = useSessionContext();

  // Load collapsed state from localStorage
  useEffect(() => {
    const stored = localStorage.getItem("jarvis-sidebar-collapsed");
    if (stored === "true") {
      setSidebarCollapsed(true);
    }
  }, []);

  const toggleSidebarCollapse = useCallback(() => {
    setSidebarCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem("jarvis-sidebar-collapsed", String(next));
      return next;
    });
  }, []);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isAuthenticated, isLoading, router]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setSidebarOpen(false);
      }
      // Ctrl+B toggles sidebar collapse on desktop
      if ((e.ctrlKey || e.metaKey) && e.key === "b") {
        e.preventDefault();
        toggleSidebarCollapse();
      }
      // Ctrl+N starts a new chat
      if ((e.ctrlKey || e.metaKey) && e.key === "n") {
        e.preventDefault();
        selectSession("");
        router.push("/chat");
      }
      // Ctrl+Shift+F toggles focus mode
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === "F") {
        e.preventDefault();
        setFocusMode((prev) => !prev);
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [toggleSidebarCollapse, selectSession, router]);

  // Touch swipe to open/close sidebar on mobile
  const touchStartRef = useRef<{ x: number; y: number } | null>(null);
  useEffect(() => {
    const handleTouchStart = (e: TouchEvent) => {
      touchStartRef.current = { x: e.touches[0].clientX, y: e.touches[0].clientY };
    };
    const handleTouchEnd = (e: TouchEvent) => {
      if (!touchStartRef.current) return;
      const dx = e.changedTouches[0].clientX - touchStartRef.current.x;
      const dy = e.changedTouches[0].clientY - touchStartRef.current.y;
      const absDx = Math.abs(dx);
      const absDy = Math.abs(dy);
      // Only trigger on horizontal swipes (at least 60px, and more horizontal than vertical)
      if (absDx > 60 && absDx > absDy * 1.5) {
        if (dx > 0 && touchStartRef.current.x < 40 && !sidebarOpen) {
          setSidebarOpen(true);
        } else if (dx < 0 && sidebarOpen) {
          setSidebarOpen(false);
        }
      }
      touchStartRef.current = null;
    };
    document.addEventListener("touchstart", handleTouchStart, { passive: true });
    document.addEventListener("touchend", handleTouchEnd, { passive: true });
    return () => {
      document.removeEventListener("touchstart", handleTouchStart);
      document.removeEventListener("touchend", handleTouchEnd);
    };
  }, [sidebarOpen]);

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4 animate-fade-in-up">
          <div className="relative">
            <div className="h-12 w-12 rounded-2xl bg-primary/20 border border-primary/10 flex items-center justify-center">
              <span className="text-lg font-bold text-primary">J</span>
            </div>
            <div className="absolute inset-0 rounded-2xl animate-glow-pulse" />
          </div>
          <div className="flex items-center gap-2">
            <div className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse-dot" />
            <div className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse-dot" style={{ animationDelay: "0.2s" }} />
            <div className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse-dot" style={{ animationDelay: "0.4s" }} />
          </div>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) return null;

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Skip to main content (a11y) */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-[200] focus:rounded-xl focus:bg-primary focus:text-primary-foreground focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:shadow-lg"
      >
        Skip to main content
      </a>
      <TopLoader />
      {/* Desktop sidebar */}
      <div
        className={`hidden lg:block shrink-0 transition-all duration-300 ease-in-out ${
          focusMode ? "lg:hidden" : ""
        }`}
      >
        <Sidebar
          onSessionSelect={selectSession}
          activeSessionId={selectedSessionId}
          collapsed={sidebarCollapsed}
          onToggleCollapse={toggleSidebarCollapse}
        />
      </div>

      {/* Mobile sidebar overlay */}
      {!focusMode && (
        <div
          className={`fixed inset-0 z-50 lg:hidden transition-opacity duration-300 ${
            sidebarOpen ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"
          }`}
        >
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => setSidebarOpen(false)}
          />
          <div
            className={`relative z-10 h-full transition-transform duration-300 ease-out ${
              sidebarOpen ? "translate-x-0" : "-translate-x-full"
            }`}
          >
            <Sidebar
              onClose={() => setSidebarOpen(false)}
              onSessionSelect={selectSession}
              activeSessionId={selectedSessionId}
            />
          </div>
        </div>
      )}

      {/* Main content */}
      <div className="flex flex-1 flex-col overflow-hidden min-w-0">
        {!focusMode && <Header onMenuClick={() => setSidebarOpen(true)} />}
        <main id="main-content" className={`flex-1 overflow-hidden ${focusMode ? "pb-0" : "pb-14 lg:pb-0"}`}>
          <ErrorBoundary>
            <PageTransition>{children}</PageTransition>
          </ErrorBoundary>
        </main>
        {!focusMode && <MobileNav />}
      </div>

      {/* Focus mode exit hint */}
      {focusMode && (
        <button
          onClick={() => setFocusMode(false)}
          className="fixed top-3 right-3 z-50 flex items-center gap-1.5 rounded-full bg-card/80 backdrop-blur-sm border border-border/50 px-3 py-1.5 text-[10px] text-muted-foreground/50 hover:text-foreground hover:bg-card transition-all duration-200 opacity-0 hover:opacity-100 focus:opacity-100"
        >
          <kbd className="rounded bg-muted px-1 py-0.5 font-mono text-[9px]">Ctrl+Shift+F</kbd>
          <span>Exit focus</span>
        </button>
      )}

      {/* Command palette */}
      <CommandPalette />
      {/* Keyboard shortcuts help */}
      <KeyboardShortcuts />
      {/* Connection status monitoring */}
      <ConnectionMonitor />
      {/* First-time user onboarding */}
      <Onboarding />
      {/* PWA install prompt */}
      <PWAInstall />
    </div>
  );
}

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <SessionProvider>
      <AppLayoutInner>{children}</AppLayoutInner>
    </SessionProvider>
  );
}
