"use client";

import Link from "next/link";
import { Home, MessageSquare, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <div className="flex flex-col items-center gap-6 text-center animate-fade-in-up">
        {/* Logo */}
        <div className="relative">
          <div className="flex h-20 w-20 items-center justify-center rounded-3xl bg-primary/10 border border-primary/20">
            <span className="text-4xl font-bold text-primary/30">?</span>
          </div>
        </div>

        {/* Error text */}
        <div>
          <h1 className="text-6xl font-bold tracking-tight text-foreground/20">404</h1>
          <p className="mt-2 text-lg font-medium text-foreground">Page not found</p>
          <p className="mt-1 text-sm text-muted-foreground max-w-md">
            The page you&apos;re looking for doesn&apos;t exist or has been moved.
          </p>
        </div>

        {/* Actions */}
        <div className="flex flex-col sm:flex-row gap-3">
          <Button asChild variant="default" className="gap-2 rounded-xl">
            <Link href="/chat">
              <MessageSquare className="h-4 w-4" />
              Go to Chat
            </Link>
          </Button>
          <Button asChild variant="outline" className="gap-2 rounded-xl border-border/50">
            <Link href="/dashboard">
              <Home className="h-4 w-4" />
              Dashboard
            </Link>
          </Button>
        </div>

        {/* Back link */}
        <button
          onClick={() => window.history.back()}
          className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Go back
        </button>
      </div>
    </div>
  );
}
