"use client";

import { useEffect, useRef, useCallback, useState } from "react";

const WS_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:3000")
  .replace(/^http/, "ws");

interface WSEvent {
  event: string;
  data: unknown;
}

type EventHandler = (data: unknown) => void;

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const handlersRef = useRef<Map<string, Set<EventHandler>>>(new Map());
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [connected, setConnected] = useState(false);

  const connect = useCallback(() => {
    if (typeof window === "undefined") return;
    const token = localStorage.getItem("jarvis_token");
    if (!token) return;

    // Don't reconnect if already connected
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    try {
      const ws = new WebSocket(`${WS_BASE}/ws`);
      wsRef.current = ws;

      ws.onopen = () => {
        // Send auth message
        ws.send(JSON.stringify({ type: "auth", token: `Bearer ${token}` }));
      };

      ws.onmessage = (event) => {
        try {
          const msg: WSEvent = JSON.parse(event.data);

          if (msg.event === "connected") {
            setConnected(true);
            return;
          }

          if (msg.event === "error") {
            console.warn("WebSocket error:", msg.data);
            return;
          }

          // Dispatch to registered handlers
          const handlers = handlersRef.current.get(msg.event);
          if (handlers) {
            for (const handler of handlers) {
              handler(msg.data);
            }
          }

          // Also dispatch to wildcard handlers
          const wildcardHandlers = handlersRef.current.get("*");
          if (wildcardHandlers) {
            for (const handler of wildcardHandlers) {
              handler(msg);
            }
          }
        } catch {
          // ignore parse errors
        }
      };

      ws.onclose = () => {
        setConnected(false);
        wsRef.current = null;
        // Auto-reconnect after 5s
        if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
        reconnectTimer.current = setTimeout(connect, 5000);
      };

      ws.onerror = () => {
        // onclose will fire after this
      };
    } catch {
      // WebSocket creation failed
    }
  }, []);

  const disconnect = useCallback(() => {
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current);
      reconnectTimer.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setConnected(false);
  }, []);

  const on = useCallback((event: string, handler: EventHandler) => {
    if (!handlersRef.current.has(event)) {
      handlersRef.current.set(event, new Set());
    }
    handlersRef.current.get(event)!.add(handler);

    // Return cleanup function
    return () => {
      handlersRef.current.get(event)?.delete(handler);
    };
  }, []);

  // Connect on mount, disconnect on unmount
  useEffect(() => {
    connect();
    return disconnect;
  }, [connect, disconnect]);

  return { connected, on, connect, disconnect };
}
