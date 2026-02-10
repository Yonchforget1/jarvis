"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { Menu, X } from "lucide-react";
import { Button } from "@/components/ui/button";

export function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  // Throttled scroll handler via requestAnimationFrame
  useEffect(() => {
    let rafId: number | null = null;
    const handleScroll = () => {
      if (rafId !== null) return;
      rafId = requestAnimationFrame(() => {
        rafId = null;
        setScrolled(window.scrollY > 20);
      });
    };
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => {
      window.removeEventListener("scroll", handleScroll);
      if (rafId !== null) cancelAnimationFrame(rafId);
    };
  }, []);

  // Close mobile menu on navigation
  const closeMobile = useCallback(() => setMobileOpen(false), []);

  // Close mobile menu on Escape
  useEffect(() => {
    if (!mobileOpen) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMobileOpen(false);
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [mobileOpen]);

  return (
    <nav
      aria-label="Main navigation"
      className={`fixed top-0 left-0 right-0 z-50 border-b backdrop-blur-xl transition-all duration-300 ${
        scrolled
          ? "border-border/20 bg-background/90 shadow-lg shadow-black/5"
          : "border-white/5 bg-background/80"
      }`}
    >
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4">
        <Link href="/" aria-label="Jarvis home" className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/20">
            <span className="text-sm font-bold text-primary">J</span>
          </div>
          <span className="text-lg font-bold">JARVIS</span>
        </Link>

        <div className="hidden sm:flex items-center gap-6">
          <Link
            href="#features"
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            Features
          </Link>
          <Link
            href="#pricing"
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            Pricing
          </Link>
        </div>

        <div className="flex items-center gap-3">
          {/* Mobile menu toggle */}
          <button
            onClick={() => setMobileOpen(!mobileOpen)}
            aria-label={mobileOpen ? "Close menu" : "Open menu"}
            aria-expanded={mobileOpen}
            className="sm:hidden flex h-10 w-10 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
          >
            {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>

          <div className="hidden sm:flex items-center gap-3">
            <Button asChild variant="ghost" size="sm">
              <Link href="/login">Sign In</Link>
            </Button>
            <Button asChild size="sm" className="rounded-lg bg-gradient-to-r from-primary to-purple-500">
              <Link href="/register">Get Started</Link>
            </Button>
          </div>
        </div>
      </div>

      {/* Mobile menu */}
      {mobileOpen && (
        <div className="sm:hidden border-t border-border/20 bg-background/95 backdrop-blur-xl animate-fade-in">
          <div className="flex flex-col gap-1 p-4">
            <Link
              href="#features"
              onClick={closeMobile}
              className="rounded-xl px-4 py-3 text-sm text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
            >
              Features
            </Link>
            <Link
              href="#pricing"
              onClick={closeMobile}
              className="rounded-xl px-4 py-3 text-sm text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
            >
              Pricing
            </Link>
            <div className="border-t border-border/20 mt-2 pt-2 flex flex-col gap-2">
              <Button asChild variant="outline" className="w-full rounded-xl h-11">
                <Link href="/login" onClick={closeMobile}>Sign In</Link>
              </Button>
              <Button asChild className="w-full rounded-xl h-11 bg-gradient-to-r from-primary to-purple-500">
                <Link href="/register" onClick={closeMobile}>Get Started</Link>
              </Button>
            </div>
          </div>
        </div>
      )}
    </nav>
  );
}
