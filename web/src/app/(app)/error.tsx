"use client";

import { useEffect } from "react";
import { AlertTriangle, RotateCcw, Home } from "lucide-react";
import Link from "next/link";

export default function AppError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("App error:", error);
  }, [error]);

  return (
    <div className="flex h-full items-center justify-center p-4">
      <div className="w-full max-w-md text-center space-y-6 animate-fade-in-up">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-red-500/10 border border-red-500/20 mx-auto">
          <AlertTriangle className="h-7 w-7 text-red-400" />
        </div>
        <div>
          <h2 className="text-lg font-semibold mb-1.5">Something went wrong</h2>
          <p className="text-sm text-muted-foreground/70 leading-relaxed">
            {error.message || "An unexpected error occurred in this page."}
          </p>
        </div>
        <div className="flex items-center justify-center gap-3">
          <button
            onClick={reset}
            className="inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            Try Again
          </button>
          <Link
            href="/chat"
            className="inline-flex items-center gap-2 rounded-xl border border-border/50 px-5 py-2.5 text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
          >
            <Home className="h-3.5 w-3.5" />
            Go Home
          </Link>
        </div>
      </div>
    </div>
  );
}
