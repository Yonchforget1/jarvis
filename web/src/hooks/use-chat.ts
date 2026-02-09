"use client";

import { useState, useCallback, useRef } from "react";
import { api, ApiError } from "@/lib/api";
import type { ChatMessage, ToolCallDetail } from "@/lib/types";

interface ChatApiResponse {
  session_id: string;
  response: string;
  tool_calls: ToolCallDetail[];
  timestamp: string;
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(
    async (content: string) => {
      const userMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setIsLoading(true);
      setError(null);

      abortRef.current = new AbortController();

      try {
        const res = await api.post<ChatApiResponse>("/api/chat", {
          message: content,
          session_id: sessionId,
        });

        setSessionId(res.session_id);

        const assistantMsg: ChatMessage = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: res.response,
          tool_calls: res.tool_calls,
          timestamp: res.timestamp,
        };
        setMessages((prev) => [...prev, assistantMsg]);
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          // Auth error handled by api.ts redirect
          return;
        }
        const errorMessage = err instanceof Error ? err.message : "Failed to get response";
        setError(errorMessage);
        const errorMsg: ChatMessage = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: `I encountered an error: ${errorMessage}\n\nPlease try again or start a new chat.`,
          timestamp: new Date().toISOString(),
          isError: true,
        };
        setMessages((prev) => [...prev, errorMsg]);
      } finally {
        setIsLoading(false);
        abortRef.current = null;
      }
    },
    [sessionId],
  );

  const clearChat = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
    }
    setMessages([]);
    setSessionId(null);
    setError(null);
  }, []);

  const retryLast = useCallback(() => {
    const lastUserMsg = [...messages].reverse().find((m) => m.role === "user");
    if (lastUserMsg) {
      // Remove error message and retry
      setMessages((prev) => prev.filter((m) => !m.isError));
      // Re-send the message content (remove the user msg too since sendMessage adds it)
      setMessages((prev) => prev.filter((m) => m.id !== lastUserMsg.id));
      sendMessage(lastUserMsg.content);
    }
  }, [messages, sendMessage]);

  return { messages, isLoading, sessionId, error, sendMessage, clearChat, retryLast };
}
