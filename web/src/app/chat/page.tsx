"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { ChatMessage } from "@/components/ChatMessage";
import { ChatInput } from "@/components/ChatInput";

interface Message {
  role: "user" | "assistant" | "system";
  content: string;
}

export default function ChatPage() {
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!api.isLoggedIn()) {
      router.push("/");
      return;
    }
    const name = api.getUsername() || "there";
    setMessages([{ role: "system", content: `Welcome back, ${name}. How can I help?` }]);
  }, [router]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend(text: string) {
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setSending(true);

    try {
      const res = await api.chat(text, sessionId);
      setSessionId(res.session_id);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: res.response },
      ]);
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

  function handleLogout() {
    api.logout();
    router.push("/");
  }

  return (
    <div className="flex flex-col h-screen bg-zinc-950 text-zinc-100">
      {/* Header */}
      <header className="flex items-center justify-between px-5 py-3 bg-zinc-900 border-b border-zinc-800">
        <div className="flex items-center gap-3">
          <div className="w-2 h-2 rounded-full bg-green-500" />
          <h1 className="text-lg font-semibold">Jarvis</h1>
        </div>
        <div className="flex items-center gap-4">
          <button
            onClick={() => {
              setMessages([]);
              setSessionId(null);
              setMessages([{ role: "system", content: "New session started." }]);
            }}
            className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
          >
            New Chat
          </button>
          <button
            onClick={handleLogout}
            className="text-xs text-zinc-500 hover:text-red-400 transition-colors"
          >
            Logout
          </button>
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
  );
}
