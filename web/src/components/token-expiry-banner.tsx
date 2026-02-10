"use client";

import { useState, useEffect } from "react";
import { AlertTriangle } from "lucide-react";

export function TokenExpiryBanner() {
  const [remainingMs, setRemainingMs] = useState<number | null>(null);

  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      if (detail?.remainingMs != null) {
        setRemainingMs(detail.remainingMs);
      }
    };
    window.addEventListener("token-expiry-warning", handler);
    return () => window.removeEventListener("token-expiry-warning", handler);
  }, []);

  if (remainingMs == null) return null;

  const mins = Math.max(1, Math.round(remainingMs / 60_000));

  return (
    <div className="fixed top-0 inset-x-0 z-[90] flex items-center justify-center gap-2 bg-yellow-500/90 text-yellow-950 px-4 py-1.5 text-xs font-medium animate-fade-in">
      <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
      <span>
        Your session expires in ~{mins} min.{" "}
        <a href="/login" className="underline underline-offset-2 font-semibold hover:text-yellow-900">
          Sign in again
        </a>{" "}
        to continue.
      </span>
    </div>
  );
}
