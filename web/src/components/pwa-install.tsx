"use client";

import { useState, useEffect, useCallback } from "react";
import { Download, X, Smartphone } from "lucide-react";

interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

function detectIOS(): boolean {
  if (typeof navigator === "undefined") return false;
  const ua = navigator.userAgent;
  return /iPad|iPhone|iPod/.test(ua) && !(window as unknown as { MSStream?: unknown }).MSStream;
}

export function PWAInstall() {
  const [installPrompt, setInstallPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [showBanner, setShowBanner] = useState(false);
  const [bannerMode, setBannerMode] = useState<"native" | "ios">("native");
  const [showIOSGuide, setShowIOSGuide] = useState(false);

  useEffect(() => {
    // Check if already installed as PWA
    if (window.matchMedia("(display-mode: standalone)").matches) return;

    // Check if user dismissed recently
    const dismissed = localStorage.getItem("jarvis-pwa-dismissed");
    if (dismissed) {
      const dismissedAt = parseInt(dismissed, 10);
      if (Date.now() - dismissedAt < 7 * 24 * 60 * 60 * 1000) return; // 7 days
    }

    // Listen for install prompt (Chrome/Edge/Android)
    const handler = (e: Event) => {
      e.preventDefault();
      setInstallPrompt(e as BeforeInstallPromptEvent);
      setBannerMode("native");
      setShowBanner(true);
    };
    window.addEventListener("beforeinstallprompt", handler);

    // For iOS, show after a delay if not installed
    if (detectIOS()) {
      const timer = setTimeout(() => {
        setBannerMode("ios");
        setShowBanner(true);
      }, 5000);
      return () => {
        clearTimeout(timer);
        window.removeEventListener("beforeinstallprompt", handler);
      };
    }

    return () => window.removeEventListener("beforeinstallprompt", handler);
  }, []);

  const [updateAvailable, setUpdateAvailable] = useState(false);
  const [waitingWorker, setWaitingWorker] = useState<ServiceWorker | null>(null);

  // Register service worker and detect updates
  useEffect(() => {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/sw.js").then((registration) => {
        // Check for updates every 60 seconds
        const interval = setInterval(() => registration.update(), 60000);

        registration.addEventListener("updatefound", () => {
          const newWorker = registration.installing;
          if (newWorker) {
            newWorker.addEventListener("statechange", () => {
              if (newWorker.state === "installed" && navigator.serviceWorker.controller) {
                setUpdateAvailable(true);
                setWaitingWorker(newWorker);
              }
            });
          }
        });

        return () => clearInterval(interval);
      }).catch(() => {});
    }
  }, []);

  const handleUpdate = useCallback(() => {
    if (waitingWorker) {
      waitingWorker.postMessage("skipWaiting");
      setUpdateAvailable(false);
      window.location.reload();
    }
  }, [waitingWorker]);

  const handleInstall = useCallback(async () => {
    if (installPrompt) {
      await installPrompt.prompt();
      const { outcome } = await installPrompt.userChoice;
      if (outcome === "accepted") {
        setShowBanner(false);
      }
      setInstallPrompt(null);
    } else if (bannerMode === "ios") {
      setShowIOSGuide(true);
    }
  }, [installPrompt, bannerMode]);

  const handleDismiss = useCallback(() => {
    setShowBanner(false);
    localStorage.setItem("jarvis-pwa-dismissed", String(Date.now()));
  }, []);

  if (!showBanner && !updateAvailable) return null;

  // Show update banner if no install banner
  if (!showBanner && updateAvailable) {
    return (
      <div className="fixed bottom-16 left-4 right-4 z-50 lg:bottom-4 lg:left-auto lg:right-4 lg:w-80 animate-fade-in-up">
        <div className="rounded-2xl border border-primary/30 bg-card/95 backdrop-blur-xl shadow-2xl p-4">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10">
              <Download className="h-5 w-5 text-primary" />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="text-sm font-semibold text-foreground">Update Available</h3>
              <p className="text-xs text-muted-foreground mt-0.5">
                A new version of JARVIS is ready.
              </p>
            </div>
          </div>
          <div className="mt-3">
            <button
              onClick={handleUpdate}
              className="w-full flex items-center justify-center gap-1.5 rounded-xl bg-primary text-primary-foreground px-3 py-2 text-xs font-medium hover:bg-primary/90 transition-colors"
            >
              <Download className="h-3.5 w-3.5" />
              Update Now
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
      {/* Install banner */}
      <div className="fixed bottom-16 left-4 right-4 z-50 lg:bottom-4 lg:left-auto lg:right-4 lg:w-80 animate-fade-in-up">
        <div className="rounded-2xl border border-border/50 bg-card/95 backdrop-blur-xl shadow-2xl p-4">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10">
              <Smartphone className="h-5 w-5 text-primary" />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="text-sm font-semibold text-foreground">Install JARVIS</h3>
              <p className="text-xs text-muted-foreground mt-0.5">
                {bannerMode === "ios"
                  ? "Add to Home Screen for the best experience"
                  : "Install as an app for quick access"}
              </p>
            </div>
            <button
              onClick={handleDismiss}
              className="shrink-0 rounded-lg p-1 text-muted-foreground/50 hover:text-foreground hover:bg-muted/50 transition-colors"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
          <div className="mt-3 flex gap-2">
            <button
              onClick={handleInstall}
              className="flex-1 flex items-center justify-center gap-1.5 rounded-xl bg-primary text-primary-foreground px-3 py-2 text-xs font-medium hover:bg-primary/90 transition-colors"
            >
              <Download className="h-3.5 w-3.5" />
              {bannerMode === "ios" ? "Show Me How" : "Install"}
            </button>
            <button
              onClick={handleDismiss}
              className="rounded-xl bg-secondary text-secondary-foreground px-3 py-2 text-xs font-medium hover:bg-secondary/80 transition-colors"
            >
              Later
            </button>
          </div>
        </div>
      </div>

      {/* iOS install guide modal */}
      {showIOSGuide && (
        <div className="fixed inset-0 z-[60] flex items-end justify-center p-4 sm:items-center">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setShowIOSGuide(false)} />
          <div className="relative z-10 w-full max-w-sm rounded-2xl border border-border/50 bg-card p-6 shadow-2xl animate-fade-in-up">
            <h3 className="text-lg font-semibold text-foreground mb-4">Install JARVIS on iOS</h3>
            <ol className="space-y-3 text-sm text-muted-foreground">
              <li className="flex items-start gap-2">
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary text-xs font-bold">1</span>
                <span>Tap the <strong className="text-foreground">Share</strong> button in Safari&apos;s toolbar</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary text-xs font-bold">2</span>
                <span>Scroll down and tap <strong className="text-foreground">Add to Home Screen</strong></span>
              </li>
              <li className="flex items-start gap-2">
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary text-xs font-bold">3</span>
                <span>Tap <strong className="text-foreground">Add</strong> to confirm</span>
              </li>
            </ol>
            <button
              onClick={() => setShowIOSGuide(false)}
              className="mt-5 w-full rounded-xl bg-primary text-primary-foreground px-4 py-2.5 text-sm font-medium hover:bg-primary/90 transition-colors"
            >
              Got it
            </button>
          </div>
        </div>
      )}
    </>
  );
}
