"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { ChatMessage } from "@/components/ChatMessage";
import { ChatInput } from "@/components/ChatInput";
import { Sidebar } from "@/components/Sidebar";

interface Message {
  role: "user" | "assistant" | "system";
  content: string;
}

export default function ChatPage() {
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [sidebarRefresh, setSidebarRefresh] = useState(0);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!api.isLoggedIn()) {
      router.push("/");
      return;
    }
    // Resume last active session if available
    const savedSession = localStorage.getItem("jarvis_active_session");
    if (savedSession) {
      handleSelectSession(savedSession);
    } else {
      const name = api.getUsername() || "there";
      setMessages([{ role: "system", content: `Welcome back, ${name}. How can I help?` }]);
    }
  }, [router]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend(text: string) {
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setSending(true);

    // Add an empty assistant message that we'll stream into
    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

    try {
      await api.chatStream(
        text,
        sessionId,
        // onChunk: append text to the last message
        (chunk) => {
          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last && last.role === "assistant") {
              updated[updated.length - 1] = {
                ...last,
                content: last.content + chunk,
              };
            }
            return updated;
          });
        },
        // onMeta: set session ID
        (meta) => {
          setSessionId(meta.session_id);
          localStorage.setItem("jarvis_active_session", meta.session_id);
        },
        // onDone: finalize
        () => {
          setSidebarRefresh((n) => n + 1);
        },
        // onError
        (error) => {
          setMessages((prev) => {
            // Remove the empty assistant message and add error
            const updated = prev.filter(
              (m, i) => !(i === prev.length - 1 && m.role === "assistant" && !m.content)
            );
            return [...updated, { role: "system", content: `Error: ${error}` }];
          });
        }
      );
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      setMessages((prev) => [
        ...prev,
        { role: "system", content: `Error: ${msg}` },
      ]);
    } finally {
      setSending(false);
    }
  }

  function handleNewChat() {
    setMessages([{ role: "system", content: "New session started." }]);
    setSessionId(null);
    localStorage.removeItem("jarvis_active_session");
  }

  async function handleSelectSession(sid: string) {
    setSessionId(sid);
    localStorage.setItem("jarvis_active_session", sid);
    setMessages([{ role: "system", content: "Loading conversation..." }]);
    try {
      const data = await api.getSessionMessages(sid);
      const history: Message[] = data.messages.map((m) => ({
        role: m.role as "user" | "assistant",
        content: m.content,
      }));
      if (history.length > 0) {
        setMessages(history);
      } else {
        setMessages([{ role: "system", content: "Resumed session. Continue the conversation." }]);
      }
    } catch {
      setMessages([{ role: "system", content: "Resumed session. Continue the conversation." }]);
    }
  }

  function handleLogout() {
    api.logout();
    router.push("/");
  }

  return (
    <div className="flex h-screen bg-zinc-950 text-zinc-100">
      {/* Sidebar */}
      <Sidebar
        currentSessionId={sessionId}
        onSelectSession={handleSelectSession}
        onNewChat={handleNewChat}
        onLogout={handleLogout}
        refreshTrigger={sidebarRefresh}
      />

      {/* Main chat area */}
      <div className="flex flex-col flex-1">
        {/* Header */}
        <header className="flex items-center px-5 py-3 bg-zinc-900 border-b border-zinc-800">
          <div className="flex items-center gap-3">
            <div className="w-2 h-2 rounded-full bg-green-500" />
            <h1 className="text-lg font-semibold">Jarvis</h1>
          </div>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-5 py-4 flex flex-col gap-3">
          {messages.map((msg, i) => (
            <ChatMessage key={i} role={msg.role} content={msg.content} />
          ))}
          {sending && (
            <div className="self-start text-xs text-zinc-500 animate-pulse">
              Jarvis is thinking...
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <ChatInput onSend={handleSend} disabled={sending} />
      </div>
    </div>
  );
}
