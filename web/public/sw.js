/**
 * JARVIS PWA Service Worker
 *
 * Provides offline caching, background sync readiness, and install support.
 * Strategy: Network-first for API calls, Cache-first for static assets.
 */

// Cache version — update on each deploy or use build hash
// The activate handler automatically cleans caches that don't match
const CACHE_VERSION = "2";
const CACHE_NAME = `jarvis-v${CACHE_VERSION}`;
const STATIC_ASSETS = [
  "/offline.html",
  "/icon.svg",
  "/manifest.json",
];

// Install: pre-cache essential assets
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

// Activate: clean old caches
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))
      )
    )
  );
  self.clients.claim();
});

// Fetch: network-first for navigation/API, cache-first for static assets
self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== "GET") return;

  // Skip API requests and SSE streams - always go to network
  if (url.pathname.startsWith("/api/")) return;

  // For navigation requests: network-first with offline fallback
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request).catch(() => caches.match("/offline.html"))
    );
    return;
  }

  // For static assets: stale-while-revalidate
  if (
    url.pathname.match(/\.(js|css|svg|png|jpg|jpeg|gif|woff2?|ttf|ico)$/) ||
    url.pathname.startsWith("/_next/static/")
  ) {
    event.respondWith(
      caches.match(request).then((cached) => {
        const fetchPromise = fetch(request).then((response) => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          }
          return response;
        });
        return cached || fetchPromise;
      })
    );
    return;
  }
});

// Handle messages from the app
self.addEventListener("message", (event) => {
  if (event.data === "skipWaiting") {
    self.skipWaiting();
  }
  if (event.data === "clearCache") {
    caches.keys().then((keys) =>
      Promise.all(keys.map((k) => caches.delete(k)))
    ).then(() => {
      event.source?.postMessage("cacheCleared");
    });
  }
});
