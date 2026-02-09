"use client";

import { useState, useCallback } from "react";
import { api } from "@/lib/api";
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
        const errorMsg: ChatMessage = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: `Error: ${err instanceof Error ? err.message : "Failed to get response"}`,
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, errorMsg]);
      } finally {
        setIsLoading(false);
      }
    },
    [sessionId],
  );

  const clearChat = useCallback(() => {
    setMessages([]);
    setSessionId(null);
  }, []);

  return { messages, isLoading, sessionId, sendMessage, clearChat };
}
