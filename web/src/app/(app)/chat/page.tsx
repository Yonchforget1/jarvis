"use client";

import { useEffect, useRef, useCallback, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Cpu, BarChart3, Zap, Hash, DollarSign, Clock, X, Link2, Check, Pencil } from "lucide-react";
import { useChat } from "@/hooks/use-chat";
import { useSessionContext } from "@/lib/session-context";
import { ChatContainer } from "@/components/chat/chat-container";
import { ErrorBoundary } from "@/components/error-boundary";
import { api } from "@/lib/api";

interface SessionAnalytics {
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  cost_estimate_usd: number;
  message_count: number;
  tool_calls: number;
  unique_tools_used: number;
  tool_breakdown: Record<string, { calls: number; errors: number; duration_ms: number }>;
  duration_seconds: number;
}

function formatTokens(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(1) + "K";
  return String(n);
}

function formatDuration(secs: number): string {
  if (secs < 60) return `${Math.floor(secs)}s`;
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins}m`;
  const hours = Math.floor(mins / 60);
  return `${hours}h ${mins % 60}m`;
}

export default function ChatPage() {
  const searchParams = useSearchParams();
  const { selectedSessionId, selectedSessionName, clearUnread, incrementUnread, selectSession, setProcessing, setSessionName } = useSessionContext();

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

  // Session analytics popover
  const [analytics, setAnalytics] = useState<SessionAnalytics | null>(null);
  const [analyticsOpen, setAnalyticsOpen] = useState(false);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);

  const fetchAnalytics = useCallback(async (sid: string) => {
    setAnalyticsLoading(true);
    try {
      const res = await api.get<SessionAnalytics>(`/api/conversation/sessions/${sid}/analytics`);
      setAnalytics(res);
    } catch {
      setAnalytics(null);
    } finally {
      setAnalyticsLoading(false);
    }
  }, []);

  // Reset analytics when session changes
  useEffect(() => {
    setAnalytics(null);
    setAnalyticsOpen(false);
  }, [selectedSessionId]);

  // Deep-link: load session from ?session=<id> query parameter
  const deepLinkHandled = useRef(false);
  const isValidSessionId = (id: string) => /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id);
  useEffect(() => {
    if (deepLinkHandled.current) return;
    const sessionParam = searchParams.get("session");
    if (sessionParam && sessionParam !== selectedSessionId && isValidSessionId(sessionParam)) {
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
      let soundEnabled = false;
      try {
        const prefs = JSON.parse(localStorage.getItem("jarvis_notifications") || "{}");
        if (prefs.enabled === false) notifEnabled = false;
        if (prefs.sound === true) soundEnabled = true;
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
      // Play notification sound via Web Audio API
      if (soundEnabled) {
        try {
          const ctx = new AudioContext();
          const osc = ctx.createOscillator();
          const gain = ctx.createGain();
          osc.connect(gain);
          gain.connect(ctx.destination);
          osc.type = "sine";
          osc.frequency.setValueAtTime(880, ctx.currentTime);
          osc.frequency.setValueAtTime(1047, ctx.currentTime + 0.08);
          gain.gain.setValueAtTime(0.15, ctx.currentTime);
          gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.25);
          osc.start(ctx.currentTime);
          osc.stop(ctx.currentTime + 0.25);
          osc.onended = () => ctx.close();
        } catch { /* audio not available */ }
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
    tokenUsage,
    sendMessage,
    editMessage,
    retryLast,
    regenerate,
    stopStreaming,
    clearChat,
    loadSession,
  } = useChat(selectedSessionId, chatOptions);

  // Copy session link
  const [linkCopied, setLinkCopied] = useState(false);
  const copyTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const copySessionLink = useCallback(() => {
    if (!sessionId) return;
    const url = new URL(window.location.href);
    url.searchParams.set("session", sessionId);
    navigator.clipboard.writeText(url.toString()).then(() => {
      setLinkCopied(true);
      if (copyTimerRef.current) clearTimeout(copyTimerRef.current);
      copyTimerRef.current = setTimeout(() => setLinkCopied(false), 2000);
    }).catch(() => {});
  }, [sessionId]);

  // Inline session rename
  const [renaming, setRenaming] = useState(false);
  const [renameValue, setRenameValue] = useState("");
  const renameInputRef = useRef<HTMLInputElement>(null);

  const startRename = useCallback(() => {
    setRenameValue(selectedSessionName || "");
    setRenaming(true);
    setTimeout(() => renameInputRef.current?.select(), 50);
  }, [selectedSessionName]);

  const commitRename = useCallback(() => {
    const trimmed = renameValue.trim();
    if (trimmed && sessionId) {
      setSessionName(trimmed);
      api.patch(`/api/conversation/sessions/${sessionId}`, { name: trimmed }).catch(() => {});
      window.dispatchEvent(new CustomEvent("session-renamed", { detail: { sessionId, name: trimmed } }));
    }
    setRenaming(false);
  }, [renameValue, sessionId, setSessionName]);

  const cancelRename = useCallback(() => {
    setRenaming(false);
  }, []);

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
              renaming ? (
                <input
                  ref={renameInputRef}
                  value={renameValue}
                  onChange={(e) => setRenameValue(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") commitRename();
                    if (e.key === "Escape") cancelRename();
                  }}
                  onBlur={commitRename}
                  className="text-xs text-foreground bg-muted/50 border border-border/50 rounded-md px-2 py-0.5 max-w-[200px] sm:max-w-md outline-none focus:border-primary/50"
                  maxLength={100}
                />
              ) : (
                <button
                  onClick={startRename}
                  className="group/name flex items-center gap-1 text-muted-foreground/70 hover:text-foreground truncate max-w-[200px] sm:max-w-md transition-colors"
                  title="Click to rename session"
                >
                  <span className="truncate">{selectedSessionName}</span>
                  <Pencil className="h-2.5 w-2.5 opacity-0 group-hover/name:opacity-60 transition-opacity shrink-0" />
                </button>
              )
            )}
            <span className="ml-auto flex items-center gap-2">
              {messages.length > 0 && (
                <span className="text-[10px] text-muted-foreground/30 tabular-nums hidden sm:inline">
                  {messages.length} msg{messages.length !== 1 ? "s" : ""}
                </span>
              )}
              {tokenUsage && tokenUsage.total_tokens > 0 && (
                <span
                  className="text-[10px] text-muted-foreground/30 tabular-nums hidden sm:inline"
                  title={`In: ${tokenUsage.input_tokens.toLocaleString()} · Out: ${tokenUsage.output_tokens.toLocaleString()}`}
                >
                  {formatTokens(tokenUsage.total_tokens)} tokens
                </span>
              )}
              {sessionId && messages.length > 0 && (
                <button
                  onClick={copySessionLink}
                  className={`flex items-center gap-1 rounded-full border border-border/30 px-2 py-0.5 text-[10px] transition-colors ${
                    linkCopied
                      ? "bg-green-500/10 text-green-400 border-green-500/30"
                      : "bg-muted/50 text-muted-foreground/50 hover:text-foreground hover:bg-muted"
                  }`}
                  title="Copy session link"
                >
                  {linkCopied ? <Check className="h-2.5 w-2.5" /> : <Link2 className="h-2.5 w-2.5" />}
                  <span className="hidden sm:inline">{linkCopied ? "Copied" : "Link"}</span>
                </button>
              )}
              {sessionId && messages.length > 0 && (
                <button
                  onClick={() => {
                    if (!analyticsOpen) fetchAnalytics(sessionId);
                    setAnalyticsOpen(!analyticsOpen);
                  }}
                  className="flex items-center gap-1 rounded-full bg-muted/50 border border-border/30 px-2 py-0.5 text-[10px] text-muted-foreground/50 hover:text-foreground hover:bg-muted transition-colors"
                  title="Session analytics"
                >
                  <BarChart3 className="h-2.5 w-2.5" />
                  <span className="hidden sm:inline">Stats</span>
                </button>
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
        {/* Session analytics panel */}
        {analyticsOpen && (
          <div className="border-b border-border/30 bg-card/60 backdrop-blur-sm px-4 py-3 animate-fade-in">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
                <BarChart3 className="h-3 w-3 text-primary" />
                Session Analytics
              </span>
              <button onClick={() => setAnalyticsOpen(false)} className="p-0.5 rounded hover:bg-muted transition-colors">
                <X className="h-3 w-3 text-muted-foreground" />
              </button>
            </div>
            {analyticsLoading ? (
              <div className="flex items-center gap-2 text-[10px] text-muted-foreground/50">
                <span className="h-3 w-3 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
                Loading...
              </div>
            ) : analytics ? (
              <div className="space-y-2">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  <div className="flex items-center gap-2 rounded-lg bg-muted/30 px-2.5 py-1.5">
                    <Zap className="h-3 w-3 text-yellow-400 shrink-0" />
                    <div>
                      <p className="text-[10px] text-muted-foreground/50">Tokens</p>
                      <p className="text-xs font-medium tabular-nums">{formatTokens(analytics.total_tokens)}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 rounded-lg bg-muted/30 px-2.5 py-1.5">
                    <DollarSign className="h-3 w-3 text-green-400 shrink-0" />
                    <div>
                      <p className="text-[10px] text-muted-foreground/50">Cost</p>
                      <p className="text-xs font-medium tabular-nums">${analytics.cost_estimate_usd.toFixed(4)}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 rounded-lg bg-muted/30 px-2.5 py-1.5">
                    <Hash className="h-3 w-3 text-cyan-400 shrink-0" />
                    <div>
                      <p className="text-[10px] text-muted-foreground/50">Tool Calls</p>
                      <p className="text-xs font-medium tabular-nums">{analytics.tool_calls} ({analytics.unique_tools_used} tools)</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 rounded-lg bg-muted/30 px-2.5 py-1.5">
                    <Clock className="h-3 w-3 text-orange-400 shrink-0" />
                    <div>
                      <p className="text-[10px] text-muted-foreground/50">Duration</p>
                      <p className="text-xs font-medium tabular-nums">{formatDuration(analytics.duration_seconds)}</p>
                    </div>
                  </div>
                </div>
                {/* Token breakdown */}
                <div className="flex items-center gap-3 text-[10px] text-muted-foreground/40">
                  <span>In: {formatTokens(analytics.input_tokens)}</span>
                  <span>Out: {formatTokens(analytics.output_tokens)}</span>
                  {analytics.tool_calls > 0 && Object.keys(analytics.tool_breakdown).length > 0 && (
                    <span className="ml-auto">
                      Top tools: {Object.entries(analytics.tool_breakdown).sort(([, a], [, b]) => b.calls - a.calls).slice(0, 3).map(([name, s]) => `${name}(${s.calls})`).join(", ")}
                    </span>
                  )}
                </div>
              </div>
            ) : (
              <p className="text-[10px] text-muted-foreground/40">No analytics available</p>
            )}
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
