"use client";

import { useEffect, useRef } from "react";
import { useChat } from "@/hooks/use-chat";
import { useSessionContext } from "@/lib/session-context";
import { ChatContainer } from "@/components/chat/chat-container";

export default function ChatPage() {
  const { selectedSessionId } = useSessionContext();
  const {
    messages,
    isLoading,
    sessionId,
    sendMessage,
    retryLast,
    stopStreaming,
    clearChat,
    loadSession,
  } = useChat(selectedSessionId);

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
  const { selectSession } = useSessionContext();
  useEffect(() => {
    if (sessionId && sessionId !== selectedSessionId) {
      selectSession(sessionId);
    }
  }, [sessionId, selectedSessionId, selectSession]);

  return (
    <ChatContainer
      messages={messages}
      isLoading={isLoading}
      onSend={sendMessage}
      onRetry={retryLast}
      onStop={stopStreaming}
    />
  );
}
