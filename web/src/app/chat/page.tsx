"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { ChatMessage } from "@/components/ChatMessage";
import { ChatInput } from "@/components/ChatInput";
import { Sidebar } from "@/components/Sidebar";
import { TemplateGrid } from "@/components/TemplateGrid";
import { ThemeToggle } from "@/components/ThemeToggle";
import { WelcomeModal } from "@/components/WelcomeModal";

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
  const [selectedModel, setSelectedModel] = useState<string | null>(null);
  const [shareUrl, setShareUrl] = useState<string | null>(null);
  const [lastFailedMessage, setLastFailedMessage] = useState<string | null>(null);
  const [showWelcome, setShowWelcome] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!api.isLoggedIn()) {
      router.push("/");
      return;
    }
    // Show welcome modal for first-time users
    if (!localStorage.getItem("jarvis_onboarded")) {
      setShowWelcome(true);
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

  // Keyboard shortcuts
  useEffect(() => {
    function handleKeyboard(e: KeyboardEvent) {
      // Ctrl+N / Cmd+N: New chat
      if ((e.ctrlKey || e.metaKey) && e.key === "n") {
        e.preventDefault();
        handleNewChat();
      }
      // Ctrl+K / Cmd+K: Focus search (in sidebar)
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        const searchInput = document.querySelector<HTMLInputElement>('input[placeholder*="Search"]');
        searchInput?.focus();
      }
      // Escape: Clear search, focus chat input
      if (e.key === "Escape") {
        const textarea = document.querySelector<HTMLTextAreaElement>('textarea[placeholder*="Message"]');
        textarea?.focus();
      }
    }
    window.addEventListener("keydown", handleKeyboard);
    return () => window.removeEventListener("keydown", handleKeyboard);
  }, []);

  async function handleSend(text: string) {
    setLastFailedMessage(null);
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
          setLastFailedMessage(text);
          const friendly = error.includes("timed out")
            ? "Response timed out. The AI took too long to respond."
            : error.includes("429") || error.includes("rate")
            ? "Rate limit reached. Please wait a moment before sending another message."
            : `Something went wrong: ${error}`;
          setMessages((prev) => {
            const updated = prev.filter(
              (m, i) => !(i === prev.length - 1 && m.role === "assistant" && !m.content)
            );
            return [...updated, { role: "system", content: friendly }];
          });
        },
        selectedModel
      );
    } catch (err: unknown) {
      setLastFailedMessage(text);
      const msg = err instanceof Error ? err.message : "Unknown error";
      const friendly = msg.includes("timed out")
        ? "Response timed out. The AI took too long to respond."
        : msg.includes("Failed to fetch")
        ? "Cannot reach the server. Check your connection."
        : `Something went wrong: ${msg}`;
      setMessages((prev) => [
        ...prev,
        { role: "system", content: friendly },
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
    <div className="flex h-screen bg-white dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100">
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
        <header className="flex items-center justify-between px-5 py-3 bg-zinc-100 dark:bg-zinc-900 border-b border-zinc-200 dark:border-zinc-800">
          <div className="flex items-center gap-3 pl-10 md:pl-0">
            <div className="w-2 h-2 rounded-full bg-green-500" />
            <h1 className="text-lg font-semibold">Jarvis</h1>
          </div>
          <div className="flex items-center gap-2">
            {sessionId && (
              <button
                onClick={async () => {
                  try {
                    const result = await api.shareSession(sessionId);
                    const url = `${window.location.origin}${result.url}`;
                    navigator.clipboard.writeText(url);
                    setShareUrl(url);
                    setTimeout(() => setShareUrl(null), 3000);
                  } catch { /* ignore */ }
                }}
                className="text-xs text-zinc-500 hover:text-blue-400 transition-colors px-2 py-1"
              >
                {shareUrl ? "Link copied!" : "Share"}
              </button>
            )}
            {sessionId && (
              <button
                onClick={async () => {
                  const url = `${window.location.origin.replace(':3001', ':3000')}/api/sessions/${sessionId}/export?format=markdown`;
                  window.open(url, "_blank");
                }}
                className="text-xs text-zinc-500 hover:text-green-400 transition-colors px-2 py-1"
              >
                Export
              </button>
            )}
          <select
            value={selectedModel || ""}
            onChange={(e) => setSelectedModel(e.target.value || null)}
            className="bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 text-xs px-2 py-1.5 rounded border border-zinc-300 dark:border-zinc-700 focus:border-blue-500 focus:outline-none"
          >
            <option value="">Default Model</option>
            <optgroup label="Anthropic">
              <option value="claude-sonnet-4-5-20250929">Claude Sonnet 4.5</option>
              <option value="claude-haiku-4-5-20251001">Claude Haiku 4.5</option>
            </optgroup>
            <optgroup label="OpenAI">
              <option value="gpt-4o">GPT-4o</option>
              <option value="gpt-4o-mini">GPT-4o Mini</option>
            </optgroup>
            <optgroup label="Google">
              <option value="gemini-2.0-flash">Gemini 2.0 Flash</option>
            </optgroup>
          </select>
            <ThemeToggle />
          </div>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-5 py-4 flex flex-col gap-3">
          {messages.map((msg, i) => (
            <ChatMessage
              key={i}
              role={msg.role}
              content={msg.content}
              onFork={sessionId ? async () => {
                try {
                  const result = await api.forkSession(sessionId, i);
                  handleSelectSession(result.session_id);
                  setSidebarRefresh((n) => n + 1);
                } catch { /* ignore */ }
              } : undefined}
              onEdit={msg.role === "user" && sessionId ? (newContent: string) => {
                // Fork to the message before this one, then send new content
                const forkIndex = i - 1;
                if (forkIndex >= 0) {
                  api.forkSession(sessionId, forkIndex).then((result) => {
                    handleSelectSession(result.session_id);
                    setSidebarRefresh((n) => n + 1);
                    // Send the edited message in the forked session
                    setTimeout(() => handleSend(newContent), 500);
                  }).catch(() => {});
                } else {
                  // First message - just resend
                  handleSend(newContent);
                }
              } : undefined}
              onRegenerate={msg.role === "assistant" && sessionId ? async () => {
                try {
                  const result = await api.regenerateSession(sessionId);
                  if (result.status === "ready") {
                    // Remove the last assistant message from UI and resend
                    setMessages((prev) => prev.filter((_, idx) => idx !== i));
                    handleSend(result.message);
                  }
                } catch { /* ignore */ }
              } : undefined}
            />
          ))}
          {sending && (
            <div className="self-start flex items-center gap-2 px-4 py-3 rounded-xl bg-zinc-100 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700">
              <div className="flex gap-1">
                <span className="w-2 h-2 rounded-full bg-zinc-400 animate-bounce" style={{ animationDelay: "0ms" }} />
                <span className="w-2 h-2 rounded-full bg-zinc-400 animate-bounce" style={{ animationDelay: "150ms" }} />
                <span className="w-2 h-2 rounded-full bg-zinc-400 animate-bounce" style={{ animationDelay: "300ms" }} />
              </div>
              <span className="text-xs text-zinc-500">Jarvis is thinking</span>
            </div>
          )}
          {/* Retry button on error */}
          {lastFailedMessage && !sending && (
            <div className="self-center">
              <button
                onClick={() => handleSend(lastFailedMessage)}
                className="text-xs bg-blue-600 hover:bg-blue-500 text-white px-4 py-1.5 rounded-lg transition-colors"
              >
                Retry
              </button>
            </div>
          )}
          {/* Show templates when no active conversation */}
          {!sessionId && messages.length <= 1 && !sending && (
            <div className="mt-4">
              <TemplateGrid onSelect={(prompt) => handleSend(prompt)} />
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <ChatInput onSend={handleSend} disabled={sending} />
      </div>

      {/* Welcome Modal */}
      {showWelcome && (
        <WelcomeModal
          onClose={() => setShowWelcome(false)}
          onStartChat={(prompt) => { setShowWelcome(false); handleSend(prompt); }}
        />
      )}
    </div>
  );
}
