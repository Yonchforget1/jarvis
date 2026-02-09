"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { SessionProvider, useSessionContext } from "@/lib/session-context";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { ErrorBoundary } from "@/components/error-boundary";

function AppLayoutInner({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { selectedSessionId, selectSession } = useSessionContext();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isAuthenticated, isLoading, router]);

  // Close sidebar on Escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") setSidebarOpen(false);
    };
    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, []);

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
      {/* Desktop sidebar */}
      <div className="hidden lg:block shrink-0">
        <Sidebar
          onSessionSelect={selectSession}
          activeSessionId={selectedSessionId}
        />
      </div>

      {/* Mobile sidebar overlay */}
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

      {/* Main content */}
      <div className="flex flex-1 flex-col overflow-hidden min-w-0">
        <Header onMenuClick={() => setSidebarOpen(true)} />
        <main className="flex-1 overflow-hidden">
          <ErrorBoundary>{children}</ErrorBoundary>
        </main>
      </div>
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
