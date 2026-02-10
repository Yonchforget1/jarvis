"use client";

import { useEffect, useRef, useCallback, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Cpu } from "lucide-react";
import { useChat } from "@/hooks/use-chat";
import { useSessionContext } from "@/lib/session-context";
import { ChatContainer } from "@/components/chat/chat-container";
import { ErrorBoundary } from "@/components/error-boundary";
import { api } from "@/lib/api";

export default function ChatPage() {
  const searchParams = useSearchParams();
  const { selectedSessionId, selectedSessionName, clearUnread, incrementUnread, selectSession, setProcessing } = useSessionContext();

  // Fetch model info once for header badge (cached in sessionStorage)
  const [modelLabel, setModelLabel] = useState<string | null>(() => {
    try { return sessionStorage.getItem("jarvis_model_label"); } catch { return null; }
  });
  useEffect(() => {
    if (modelLabel) return; // Already have it
    api.get<{ backend: string; model: string }>("/api/stats")
      .then((res) => {
        const short = res.model?.split("-").slice(0, 3).join("-") || res.backend;
        setModelLabel(short);
        try { sessionStorage.setItem("jarvis_model_label", short); } catch { /* ignore */ }
      })
      .catch(() => {});
  }, [modelLabel]);

  // Deep-link: load session from ?session=<id> query parameter
  const deepLinkHandled = useRef(false);
  useEffect(() => {
    if (deepLinkHandled.current) return;
    const sessionParam = searchParams.get("session");
    if (sessionParam && sessionParam !== selectedSessionId) {
      deepLinkHandled.current = true;
      selectSession(sessionParam);
    }
  }, [searchParams, selectedSessionId, selectSession]);

  // Clear unread count when visiting chat page
  useEffect(() => {
    clearUnread();
  }, [clearUnread]);

  // Request notification permission on first visit
  useEffect(() => {
    if (typeof Notification !== "undefined" && Notification.permission === "default") {
      // Delay to not interrupt the user immediately
      const timer = setTimeout(() => {
        Notification.requestPermission();
      }, 10000);
      return () => clearTimeout(timer);
    }
  }, []);

  // Increment unread when assistant responds and tab is hidden
  const titleFlashRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Flash title when tab is hidden to notify user
  useEffect(() => {
    const handleVisibility = () => {
      if (!document.hidden && titleFlashRef.current) {
        clearInterval(titleFlashRef.current);
        titleFlashRef.current = null;
      }
    };
    document.addEventListener("visibilitychange", handleVisibility);
    return () => {
      document.removeEventListener("visibilitychange", handleVisibility);
      if (titleFlashRef.current) {
        clearInterval(titleFlashRef.current);
        titleFlashRef.current = null;
      }
    };
  }, []);

  const onAssistantMessage = useCallback(() => {
    if (document.hidden) {
      incrementUnread();

      // Check notification preferences
      let notifEnabled = true;
      try {
        const prefs = JSON.parse(localStorage.getItem("jarvis_notifications") || "{}");
        if (prefs.enabled === false) notifEnabled = false;
      } catch { /* ignore */ }

      // Flash the title
      if (!titleFlashRef.current) {
        const original = document.title;
        let show = true;
        titleFlashRef.current = setInterval(() => {
          document.title = show ? "New message - JARVIS" : original;
          show = !show;
        }, 1000);
      }
      // Send browser notification if permitted and enabled
      if (notifEnabled && typeof Notification !== "undefined" && Notification.permission === "granted") {
        new Notification("JARVIS", {
          body: "New response ready",
          icon: "/icon-192x192.png",
        });
      }
    }
  }, [incrementUnread]);

  const chatOptions = useMemo(() => ({ onAssistantMessage }), [onAssistantMessage]);

  const {
    messages,
    isLoading,
    sessionId,
    error: chatError,
    sendMessage,
    editMessage,
    retryLast,
    regenerate,
    stopStreaming,
    clearChat,
    loadSession,
  } = useChat(selectedSessionId, chatOptions);

  // Auto-send prompt from ?prompt= query parameter (e.g., dashboard "Try These")
  const promptHandled = useRef(false);
  useEffect(() => {
    if (promptHandled.current) return;
    const promptParam = searchParams.get("prompt");
    if (promptParam) {
      promptHandled.current = true;
      const timer = setTimeout(() => {
        sendMessage(promptParam);
        const url = new URL(window.location.href);
        url.searchParams.delete("prompt");
        window.history.replaceState(null, "", url.toString());
      }, 200);
      return () => clearTimeout(timer);
    }
  }, [searchParams, sendMessage]);

  // Update URL when session changes (without full navigation)
  useEffect(() => {
    if (sessionId) {
      const url = new URL(window.location.href);
      if (url.searchParams.get("session") !== sessionId) {
        url.searchParams.set("session", sessionId);
        window.history.replaceState(null, "", url.toString());
      }
    }
  }, [sessionId]);

  const lastLoadedRef = useRef<string | null>(null);

  // Load session when sidebar selection changes
  useEffect(() => {
    if (selectedSessionId && selectedSessionId !== lastLoadedRef.current) {
      lastLoadedRef.current = selectedSessionId;
      loadSession(selectedSessionId);
    } else if (!selectedSessionId && lastLoadedRef.current) {
      lastLoadedRef.current = null;
      clearChat();
    }
  }, [selectedSessionId, loadSession, clearChat]);

  // Keep the session context updated with the current session
  const prevSessionIdRef = useRef<string | null>(null);
  useEffect(() => {
    if (sessionId && sessionId !== selectedSessionId) {
      selectSession(sessionId);
    }
    // Notify sidebar to refresh when a new session is created
    if (sessionId && sessionId !== prevSessionIdRef.current) {
      if (prevSessionIdRef.current !== null) {
        window.dispatchEvent(new CustomEvent("session-created"));
      }
      prevSessionIdRef.current = sessionId;
    }
  }, [sessionId, selectedSessionId, selectSession]);

  // Sync processing state to session context for sidebar indicator
  useEffect(() => {
    setProcessing(isLoading);
  }, [isLoading, setProcessing]);

  // Warn before closing tab when streaming is active
  useEffect(() => {
    if (!isLoading) return;
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      e.preventDefault();
    };
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [isLoading]);

  // Dynamic page title based on first user message
  useEffect(() => {
    const firstUserMsg = messages.find((m) => m.role === "user");
    if (firstUserMsg) {
      const preview = firstUserMsg.content.slice(0, 50).trim();
      document.title = `${preview}${firstUserMsg.content.length > 50 ? "..." : ""} - JARVIS`;
    } else {
      document.title = "Chat - JARVIS";
    }
    return () => { document.title = "JARVIS"; };
  }, [messages]);

  return (
    <ErrorBoundary>
      <div className="flex h-full flex-col">
        {/* Session header bar */}
        {(selectedSessionName || modelLabel || isLoading) && (
          <div className="flex items-center gap-2 border-b border-border/30 bg-background/60 backdrop-blur-sm px-4 py-1.5 text-xs shrink-0">
            {isLoading && (
              <span className="flex items-center gap-1.5 text-primary">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-primary" />
                </span>
                <span className="font-medium">Streaming</span>
              </span>
            )}
            {selectedSessionName && (
              <span className="text-muted-foreground/70 truncate max-w-[200px] sm:max-w-md" title={selectedSessionName}>
                {selectedSessionName}
              </span>
            )}
            <span className="ml-auto flex items-center gap-2">
              {messages.length > 0 && (
                <span className="text-[10px] text-muted-foreground/30 tabular-nums hidden sm:inline">
                  {messages.length} msg{messages.length !== 1 ? "s" : ""}
                </span>
              )}
              {modelLabel && (
                <span className="flex items-center gap-1 rounded-full bg-muted/50 border border-border/30 px-2 py-0.5 text-[10px] font-mono text-muted-foreground/50">
                  <Cpu className="h-2.5 w-2.5" />
                  {modelLabel}
                </span>
              )}
            </span>
          </div>
        )}
        <div className="flex-1 min-h-0">
          <ChatContainer
            messages={messages}
            isLoading={isLoading}
            onSend={sendMessage}
            onEditMessage={editMessage}
            onRetry={retryLast}
            onRegenerate={regenerate}
            onStop={stopStreaming}
            onClear={clearChat}
            error={chatError}
            onRetryLoad={selectedSessionId ? () => loadSession(selectedSessionId) : undefined}
          />
        </div>
      </div>
    </ErrorBoundary>
  );
}
