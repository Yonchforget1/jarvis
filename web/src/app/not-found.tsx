"use client";

import Link from "next/link";
import { Home, MessageSquare, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="relative flex min-h-screen items-center justify-center bg-background p-4 overflow-hidden">
      {/* Animated gradient orbs */}
      <div className="absolute top-1/4 -left-32 h-64 w-64 rounded-full bg-primary/10 blur-3xl animate-glow-pulse" />
      <div className="absolute bottom-1/4 -right-32 h-48 w-48 rounded-full bg-purple-500/10 blur-3xl animate-glow-pulse" style={{ animationDelay: "1s" }} />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 h-96 w-96 rounded-full bg-cyan-500/5 blur-3xl" />

      <div className="relative flex flex-col items-center gap-8 text-center animate-fade-in-up">
        {/* Logo */}
        <div className="relative">
          <div className="absolute -inset-4 rounded-3xl bg-gradient-to-r from-primary/10 via-purple-500/10 to-cyan-500/10 blur-xl animate-glow-pulse" />
          <div className="relative flex h-24 w-24 items-center justify-center rounded-3xl bg-card border border-border/50 shadow-2xl">
            <span className="text-5xl font-bold bg-gradient-to-b from-primary/40 to-primary/10 bg-clip-text text-transparent">?</span>
          </div>
        </div>

        {/* Error text */}
        <div className="space-y-2">
          <h1 className="text-7xl sm:text-8xl font-bold tracking-tighter bg-gradient-to-b from-foreground/30 to-foreground/5 bg-clip-text text-transparent">
            404
          </h1>
          <p className="text-xl font-semibold text-foreground">Page not found</p>
          <p className="text-sm text-muted-foreground/70 max-w-md leading-relaxed">
            The page you&apos;re looking for doesn&apos;t exist or has been moved.
            Let&apos;s get you back on track.
          </p>
        </div>

        {/* Actions */}
        <div className="flex flex-col sm:flex-row gap-3">
          <Button asChild variant="default" className="gap-2 rounded-xl h-11 px-6">
            <Link href="/chat">
              <MessageSquare className="h-4 w-4" />
              Go to Chat
            </Link>
          </Button>
          <Button asChild variant="outline" className="gap-2 rounded-xl h-11 px-6 border-border/50">
            <Link href="/dashboard">
              <Home className="h-4 w-4" />
              Dashboard
            </Link>
          </Button>
        </div>

        {/* Back link */}
        <button
          onClick={() => window.history.back()}
          className="flex items-center gap-1.5 text-sm text-muted-foreground/60 hover:text-foreground transition-colors group"
        >
          <ArrowLeft className="h-3.5 w-3.5 transition-transform group-hover:-translate-x-0.5" />
          Go back
        </button>
      </div>
    </div>
  );
}
