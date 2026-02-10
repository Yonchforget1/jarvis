"use client";

import { useEffect, useRef, useCallback, useMemo } from "react";
import { useSearchParams } from "next/navigation";
import { useChat } from "@/hooks/use-chat";
import { useSessionContext } from "@/lib/session-context";
import { ChatContainer } from "@/components/chat/chat-container";
import { ErrorBoundary } from "@/components/error-boundary";

export default function ChatPage() {
  const searchParams = useSearchParams();
  const { selectedSessionId, clearUnread, incrementUnread, selectSession, setProcessing } = useSessionContext();

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
      // Flash the title
      if (!titleFlashRef.current) {
        const original = document.title;
        let show = true;
        titleFlashRef.current = setInterval(() => {
          document.title = show ? "New message - JARVIS" : original;
          show = !show;
        }, 1000);
      }
      // Send browser notification if permitted
      if (typeof Notification !== "undefined" && Notification.permission === "granted") {
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
    sendMessage,
    retryLast,
    stopStreaming,
    clearChat,
    loadSession,
  } = useChat(selectedSessionId, chatOptions);

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
      <ChatContainer
        messages={messages}
        isLoading={isLoading}
        onSend={sendMessage}
        onRetry={retryLast}
        onStop={stopStreaming}
        onClear={clearChat}
      />
    </ErrorBoundary>
  );
}
