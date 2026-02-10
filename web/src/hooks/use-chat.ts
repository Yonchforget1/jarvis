"use client";

import { useState, useCallback, useRef } from "react";
import { ApiError } from "@/lib/api";
import type { ChatMessage, ToolCallDetail } from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface UseChatOptions {
  onAssistantMessage?: () => void;
}

export function useChat(initialSessionId?: string | null, options?: UseChatOptions) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(
    initialSessionId || null,
  );
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const updateStreamingMessage = useCallback(
    (msgId: string, updater: (msg: ChatMessage) => ChatMessage) => {
      setMessages((prev) =>
        prev.map((m) => (m.id === msgId ? updater(m) : m)),
      );
    },
    [],
  );

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

      const assistantMsgId = crypto.randomUUID();
      const streamingMsg: ChatMessage = {
        id: assistantMsgId,
        role: "assistant",
        content: "",
        tool_calls: [],
        timestamp: new Date().toISOString(),
        isStreaming: true,
        streamStatus: "Connecting...",
      };
      setMessages((prev) => [...prev, streamingMsg]);

      abortRef.current = new AbortController();

      try {
        const token =
          typeof window !== "undefined"
            ? localStorage.getItem("jarvis_token")
            : null;

        const response = await fetch(`${API_URL}/api/chat/stream`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({ message: content, session_id: sessionId }),
          signal: abortRef.current.signal,
        });

        if (response.status === 401) {
          if (typeof window !== "undefined") {
            localStorage.removeItem("jarvis_token");
            localStorage.removeItem("jarvis_user");
            window.location.href = "/login";
          }
          return;
        }

        if (!response.ok) {
          const body = await response
            .json()
            .catch(() => ({ detail: response.statusText }));
          throw new ApiError(
            body.detail || response.statusText,
            response.status,
          );
        }

        const reader = response.body!.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          // Parse SSE events from the buffer
          const parts = buffer.split("\n\n");
          buffer = parts.pop() || "";

          for (const part of parts) {
            if (!part.trim() || part.startsWith(":")) continue;

            let eventType = "";
            let eventData = "";

            for (const line of part.split("\n")) {
              if (line.startsWith("event: ")) {
                eventType = line.slice(7);
              } else if (line.startsWith("data: ")) {
                eventData = line.slice(6);
              }
            }

            if (!eventType || !eventData) continue;

            const data = JSON.parse(eventData);

            switch (eventType) {
              case "session":
                setSessionId(data.session_id);
                break;

              case "thinking":
                updateStreamingMessage(assistantMsgId, (m) => ({
                  ...m,
                  streamStatus: data.status,
                }));
                break;

              case "tool_call":
                updateStreamingMessage(assistantMsgId, (m) => ({
                  ...m,
                  streamStatus: `Running ${data.name}...`,
                  tool_calls: [
                    ...(m.tool_calls || []),
                    {
                      id: data.id,
                      name: data.name,
                      args: data.args,
                      result: "",
                    } as ToolCallDetail,
                  ],
                }));
                break;

              case "tool_result":
                updateStreamingMessage(assistantMsgId, (m) => ({
                  ...m,
                  tool_calls: (m.tool_calls || []).map((tc) =>
                    tc.id === data.id ? { ...tc, result: data.result } : tc,
                  ),
                }));
                break;

              case "text":
                updateStreamingMessage(assistantMsgId, (m) => ({
                  ...m,
                  content: data.content,
                  streamStatus: undefined,
                }));
                break;

              case "error":
                updateStreamingMessage(assistantMsgId, (m) => ({
                  ...m,
                  content: `Error: ${data.message}`,
                  isError: true,
                  isStreaming: false,
                  streamStatus: undefined,
                }));
                setError(data.message);
                break;

              case "done":
                updateStreamingMessage(assistantMsgId, (m) => ({
                  ...m,
                  isStreaming: false,
                  streamStatus: undefined,
                  timestamp: new Date().toISOString(),
                }));
                options?.onAssistantMessage?.();
                break;
            }
          }
        }

        // Ensure streaming flag is cleared when reader finishes
        updateStreamingMessage(assistantMsgId, (m) => ({
          ...m,
          isStreaming: false,
          streamStatus: undefined,
        }));
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") {
          // User cancelled - just clean up
          updateStreamingMessage(assistantMsgId, (m) => ({
            ...m,
            content: m.content || "Request cancelled.",
            isStreaming: false,
            streamStatus: undefined,
          }));
        } else {
          const errorMessage =
            err instanceof Error ? err.message : "Failed to get response";
          setError(errorMessage);
          updateStreamingMessage(assistantMsgId, (m) => ({
            ...m,
            content: `I encountered an error: ${errorMessage}\n\nPlease try again or start a new chat.`,
            isError: true,
            isStreaming: false,
            streamStatus: undefined,
          }));
        }
      } finally {
        setIsLoading(false);
        abortRef.current = null;
      }
    },
    [sessionId, updateStreamingMessage],
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
      // Remove only error messages, keep the user message for context
      setMessages((prev) => prev.filter((m) => !m.isError));
      sendMessage(lastUserMsg.content);
    }
  }, [messages, sendMessage]);

  const stopStreaming = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
    }
  }, []);

  const loadSession = useCallback(async (sid: string) => {
    if (abortRef.current) {
      abortRef.current.abort();
    }
    setIsLoading(true);
    setError(null);

    try {
      const token =
        typeof window !== "undefined"
          ? localStorage.getItem("jarvis_token")
          : null;

      const res = await fetch(
        `${API_URL}/api/sessions/${sid}/messages`,
        {
          headers: {
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
        },
      );

      if (!res.ok) throw new Error("Failed to load session");

      const data = await res.json();
      const loaded: ChatMessage[] = data.messages.map(
        (m: { role: string; content: string; tool_calls?: ChatMessage["tool_calls"]; timestamp?: string }, i: number) => ({
          id: `loaded-${i}`,
          role: m.role as "user" | "assistant",
          content: m.content,
          tool_calls: m.tool_calls || undefined,
          timestamp: m.timestamp || new Date().toISOString(),
        }),
      );

      setMessages(loaded);
      setSessionId(sid);
    } catch {
      setError("Failed to load conversation history");
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    messages,
    isLoading,
    sessionId,
    error,
    sendMessage,
    clearChat,
    retryLast,
    stopStreaming,
    loadSession,
  };
}
