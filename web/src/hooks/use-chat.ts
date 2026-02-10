"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { ApiError } from "@/lib/api";
import type { ChatMessage, ToolCallDetail } from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface SSESessionEvent {
  session_id: string;
}

interface SSEThinkingEvent {
  status: string;
}

interface SSEToolCallEvent {
  id: string;
  name: string;
  args: Record<string, unknown>;
}

interface SSEToolResultEvent {
  id: string;
  result: string;
}

interface SSETextEvent {
  content: string;
}

interface SSEErrorEvent {
  message: string;
}

type SSEEventData =
  | SSESessionEvent
  | SSEThinkingEvent
  | SSEToolCallEvent
  | SSEToolResultEvent
  | SSETextEvent
  | SSEErrorEvent;

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
  const loadAbortRef = useRef<AbortController | null>(null);
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const optionsRef = useRef(options);
  const messagesRef = useRef(messages);

  useEffect(() => {
    optionsRef.current = options;
  }, [options]);

  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  // Cleanup on unmount: abort any active requests and clear retry timer
  useEffect(() => {
    return () => {
      if (abortRef.current) abortRef.current.abort();
      if (loadAbortRef.current) loadAbortRef.current.abort();
      if (retryTimerRef.current) clearTimeout(retryTimerRef.current);
    };
  }, []);

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

            let data: SSEEventData;
            try {
              data = JSON.parse(eventData);
            } catch {
              console.warn("Skipping malformed SSE event:", eventData);
              continue;
            }

            switch (eventType) {
              case "session": {
                const d = data as SSESessionEvent;
                setSessionId(d.session_id);
                break;
              }

              case "thinking": {
                const d = data as SSEThinkingEvent;
                updateStreamingMessage(assistantMsgId, (m) => ({
                  ...m,
                  streamStatus: d.status,
                }));
                break;
              }

              case "tool_call": {
                const d = data as SSEToolCallEvent;
                updateStreamingMessage(assistantMsgId, (m) => ({
                  ...m,
                  streamStatus: `Running ${d.name}...`,
                  tool_calls: [
                    ...(m.tool_calls || []),
                    {
                      id: d.id,
                      name: d.name,
                      args: d.args,
                      result: "",
                    } as ToolCallDetail,
                  ],
                }));
                break;
              }

              case "tool_result": {
                const d = data as SSEToolResultEvent;
                updateStreamingMessage(assistantMsgId, (m) => ({
                  ...m,
                  tool_calls: (m.tool_calls || []).map((tc) =>
                    tc.id === d.id ? { ...tc, result: d.result } : tc,
                  ),
                }));
                break;
              }

              case "text": {
                const d = data as SSETextEvent;
                updateStreamingMessage(assistantMsgId, (m) => ({
                  ...m,
                  content: d.content,
                  streamStatus: undefined,
                }));
                break;
              }

              case "error": {
                const d = data as SSEErrorEvent;
                updateStreamingMessage(assistantMsgId, (m) => ({
                  ...m,
                  content: `Error: ${d.message}`,
                  isError: true,
                  isStreaming: false,
                  streamStatus: undefined,
                }));
                setError(d.message);
                break;
              }

              case "done":
                updateStreamingMessage(assistantMsgId, (m) => ({
                  ...m,
                  isStreaming: false,
                  streamStatus: undefined,
                  timestamp: new Date().toISOString(),
                }));
                optionsRef.current?.onAssistantMessage?.();
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
    const msgs = messagesRef.current;
    const lastUserMsg = [...msgs].reverse().find((m) => m.role === "user");
    if (lastUserMsg) {
      const lastUserIdx = msgs.lastIndexOf(lastUserMsg);
      const content = lastUserMsg.content;
      // Remove last user message and everything after it (error responses)
      // sendMessage will re-add the user message
      setMessages((prev) => prev.slice(0, lastUserIdx));
      if (retryTimerRef.current) clearTimeout(retryTimerRef.current);
      retryTimerRef.current = setTimeout(() => sendMessage(content), 50);
    }
  }, [sendMessage]);

  const stopStreaming = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
    }
  }, []);

  const loadSession = useCallback(async (sid: string) => {
    // Validate session ID format to prevent invalid API calls
    if (!sid || sid.length < 5) return;
    if (abortRef.current) {
      abortRef.current.abort();
    }
    if (loadAbortRef.current) {
      loadAbortRef.current.abort();
    }
    loadAbortRef.current = new AbortController();
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
          signal: loadAbortRef.current.signal,
        },
      );

      if (res.status === 404) {
        // Session was deleted or doesn't exist - notify sidebar
        setMessages([]);
        setSessionId(null);
        setError("This conversation no longer exists.");
        window.dispatchEvent(new CustomEvent("session-deleted", { detail: { sessionId: sid } }));
        return;
      }
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
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      setError("Failed to load conversation history");
    } finally {
      setIsLoading(false);
      loadAbortRef.current = null;
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
