"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import {
  Shield,
  Server,
  Cpu,
  HardDrive,
  MemoryStick,
  Users,
  Activity,
  RefreshCw,
  Clock,
  AlertTriangle,
  Wrench,
  ScrollText,
  Trash2,
  ChevronDown,
  ChevronRight,
  RotateCw,
  X,
  Lock,
  Loader2,
  Timer,
  Download,
} from "lucide-react";
import { api } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorBoundary } from "@/components/error-boundary";

interface SystemInfo {
  platform: string;
  python_version: string;
  architecture: string;
  processor: string;
  uptime_seconds: number;
  active_sessions: number;
  config: {
    backend: string;
    model: string;
    max_tokens: number;
    tool_timeout: number;
  };
  memory?: { total_mb: number; available_mb: number; percent_used: number };
  cpu?: { count: number; percent: number };
  disk?: { total_gb: number; free_gb: number };
}

interface AdminSession {
  session_id: string;
  user_id: string;
  created_at: string;
  last_active: string;
  message_count: number;
  archived: boolean;
}

interface ToolStat {
  name: string;
  calls: number;
  errors: number;
  avg_ms: number;
}

interface AuditEntry {
  timestamp: string;
  user_id: string;
  username: string;
  action: string;
  detail?: string;
  ip?: string;
}

function formatUptime(seconds: number): string {
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (d > 0) return `${d}d ${h}h ${m}m`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const secs = Math.floor(diff / 1000);
  if (secs < 60) return "just now";
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function ProgressBar({ percent, color = "bg-primary" }: { percent: number; color?: string }) {
  return (
    <div className="h-2 rounded-full bg-muted/50 overflow-hidden">
      <div className={`h-full rounded-full transition-all duration-500 ${color}`} style={{ width: `${Math.min(percent, 100)}%` }} />
    </div>
  );
}

export default function AdminPage() {
  const [authorized, setAuthorized] = useState<boolean | null>(null);
  const [system, setSystem] = useState<SystemInfo | null>(null);
  const [sessions, setSessions] = useState<AdminSession[]>([]);
  const [sessionsTotal, setSessionsTotal] = useState(0);
  const [tools, setTools] = useState<ToolStat[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "sessions" | "tools" | "audit">("overview");
  const [refreshing, setRefreshing] = useState(false);
  const [auditExpanded, setAuditExpanded] = useState<Set<number>>(new Set());
  const [terminatingId, setTerminatingId] = useState<string | null>(null);
  const [showReloadDialog, setShowReloadDialog] = useState(false);
  const [reloadPassword, setReloadPassword] = useState("");
  const [reloading, setReloading] = useState(false);
  const [reloadError, setReloadError] = useState<string | null>(null);
  const [reloadSuccess, setReloadSuccess] = useState(false);
  const [autoRefreshInterval, setAutoRefreshInterval] = useState<number>(0); // 0 = off
  const autoRefreshRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);

  const fetchAll = useCallback(async () => {
    try {
      const [sysRes, sessRes, toolRes, auditRes] = await Promise.allSettled([
        api.get<SystemInfo>("/api/admin/system"),
        api.get<{ sessions: AdminSession[]; total: number }>("/api/admin/sessions?limit=50"),
        api.get<{ tools: ToolStat[] }>("/api/admin/tools/stats"),
        api.get<{ entries: AuditEntry[] }>("/api/admin/audit-logs?limit=100"),
      ]);

      if (sysRes.status === "fulfilled") setSystem(sysRes.value);
      if (sessRes.status === "fulfilled") {
        setSessions(sessRes.value.sessions);
        setSessionsTotal(sessRes.value.total);
      }
      if (toolRes.status === "fulfilled") setTools(toolRes.value.tools);
      if (auditRes.status === "fulfilled") setAuditLogs(auditRes.value.entries);

      setAuthorized(true);
      setError(null);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to load admin data";
      if (msg.includes("403") || msg.includes("Admin")) {
        setAuthorized(false);
      } else {
        setError(msg);
      }
    } finally {
      setLoading(false);
      setLastRefreshed(new Date());
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  // Auto-refresh interval
  useEffect(() => {
    if (autoRefreshRef.current) clearInterval(autoRefreshRef.current);
    if (autoRefreshInterval > 0) {
      autoRefreshRef.current = setInterval(() => {
        fetchAll();
      }, autoRefreshInterval * 1000);
    }
    return () => {
      if (autoRefreshRef.current) clearInterval(autoRefreshRef.current);
    };
  }, [autoRefreshInterval, fetchAll]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchAll();
    setRefreshing(false);
  };

  const terminateSession = async (sessionId: string) => {
    setTerminatingId(sessionId);
    try {
      await api.delete(`/api/admin/sessions/${sessionId}`);
      setSessions((prev) => prev.filter((s) => s.session_id !== sessionId));
      setSessionsTotal((prev) => Math.max(0, prev - 1));
    } catch (err) {
      // Silently fail — could show toast in future
    } finally {
      setTerminatingId(null);
    }
  };

  const handleReloadConfig = async () => {
    setReloading(true);
    setReloadError(null);
    try {
      const res = await api.post<{ status: string; config: SystemInfo["config"] }>("/api/admin/config/reload", { password: reloadPassword });
      if (system && res.config) {
        setSystem({ ...system, config: res.config });
      }
      setReloadSuccess(true);
      setReloadPassword("");
      setTimeout(() => {
        setShowReloadDialog(false);
        setReloadSuccess(false);
      }, 1500);
    } catch (err) {
      setReloadError(err instanceof Error ? err.message : "Reload failed");
    } finally {
      setReloading(false);
    }
  };

  const exportSessionsCSV = useCallback(() => {
    if (sessions.length === 0) return;
    const headers = "Session ID,User ID,Messages,Created,Last Active,Status";
    const rows = sessions.map((s) =>
      `${s.session_id},${s.user_id},${s.message_count},${s.created_at},${s.last_active},${s.archived ? "Archived" : "Active"}`
    );
    const csv = [headers, ...rows].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `jarvis-sessions-${new Date().toISOString().split("T")[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [sessions]);

  const exportAuditCSV = useCallback(() => {
    if (auditLogs.length === 0) return;
    const headers = "Timestamp,Username,User ID,Action,Detail,IP";
    const rows = auditLogs.map((e) =>
      `"${e.timestamp}","${e.username}","${e.user_id}","${e.action}","${(e.detail || "").replace(/"/g, '""')}","${e.ip || ""}"`
    );
    const csv = [headers, ...rows].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `jarvis-audit-log-${new Date().toISOString().split("T")[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [auditLogs]);

  if (loading) {
    return (
      <div className="h-full overflow-y-auto p-4 sm:p-6 space-y-4">
        <Skeleton className="h-10 w-48 rounded-xl" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-24 rounded-xl" />)}
        </div>
        <Skeleton className="h-64 rounded-xl" />
      </div>
    );
  }

  if (authorized === false) {
    return (
      <div className="h-full flex items-center justify-center p-6">
        <div className="text-center space-y-4 max-w-sm">
          <div className="flex justify-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-red-500/10 border border-red-500/20">
              <Shield className="h-8 w-8 text-red-400" />
            </div>
          </div>
          <h2 className="text-xl font-bold">Access Denied</h2>
          <p className="text-sm text-muted-foreground/60 leading-relaxed">
            You don&apos;t have admin access. Contact your administrator to request access.
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full overflow-y-auto p-4 sm:p-6">
        <div className="flex flex-col items-center justify-center py-20 space-y-4">
          <AlertTriangle className="h-10 w-10 text-red-400/50" />
          <p className="text-sm text-red-400">{error}</p>
          <button onClick={handleRefresh} className="text-xs text-primary hover:underline">Retry</button>
        </div>
      </div>
    );
  }

  const tabs = [
    { id: "overview" as const, label: "Overview", icon: Server },
    { id: "sessions" as const, label: "Sessions", icon: Users },
    { id: "tools" as const, label: "Tools", icon: Wrench },
    { id: "audit" as const, label: "Audit Log", icon: ScrollText },
  ];

  return (
    <ErrorBoundary>
      <div className="h-full overflow-y-auto p-4 sm:p-6 pb-20">
        <div className="mx-auto max-w-6xl space-y-5">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2">
                <Shield className="h-5 w-5 text-primary" />
                <h1 className="text-2xl font-bold tracking-tight">Admin</h1>
                {autoRefreshInterval > 0 && (
                  <span className="flex items-center gap-1 rounded-full bg-green-400/10 border border-green-400/20 px-2 py-0.5 text-[9px] text-green-400">
                    <span className="relative flex h-1.5 w-1.5">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
                      <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-green-400" />
                    </span>
                    Live
                  </span>
                )}
              </div>
              <p className="text-sm text-muted-foreground/60 mt-0.5">
                System management and monitoring
                {lastRefreshed && (
                  <span className="ml-2 text-[10px] text-muted-foreground/30">
                    Updated {lastRefreshed.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                  </span>
                )}
              </p>
            </div>
            <div className="flex items-center gap-2">
              {/* Auto-refresh selector */}
              <div className="flex items-center gap-1 rounded-lg border border-border/50 bg-muted/30 px-1 py-0.5">
                <Timer className="h-3 w-3 text-muted-foreground/50 ml-1.5" />
                {[0, 10, 30, 60].map((s) => (
                  <button
                    key={s}
                    onClick={() => setAutoRefreshInterval(s)}
                    className={`px-1.5 py-0.5 text-[10px] rounded-md transition-colors ${
                      autoRefreshInterval === s
                        ? "bg-primary/20 text-primary font-medium"
                        : "text-muted-foreground/50 hover:text-muted-foreground hover:bg-muted"
                    }`}
                  >
                    {s === 0 ? "Off" : `${s}s`}
                  </button>
                ))}
              </div>
              <button
                onClick={handleRefresh}
                disabled={refreshing}
                className="flex items-center gap-1.5 rounded-lg border border-border/50 bg-muted/30 px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground hover:bg-muted transition-colors disabled:opacity-50"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`} />
                Refresh
              </button>
            </div>
          </div>

          {/* Tabs */}
          <div className="flex gap-1 border-b border-border/30">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-1.5 px-4 py-2 text-xs font-medium border-b-2 transition-colors ${
                  activeTab === tab.id
                    ? "border-primary text-primary"
                    : "border-transparent text-muted-foreground/60 hover:text-foreground"
                }`}
              >
                <tab.icon className="h-3.5 w-3.5" />
                {tab.label}
              </button>
            ))}
          </div>

          {/* Overview Tab */}
          {activeTab === "overview" && system && (
            <div className="space-y-4">
              {/* Quick stats */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="rounded-xl border border-border/50 bg-card/50 p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Activity className="h-4 w-4 text-green-400" />
                    <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground/50">Uptime</span>
                  </div>
                  <p className="text-lg font-bold tabular-nums">{formatUptime(system.uptime_seconds)}</p>
                </div>
                <div className="rounded-xl border border-border/50 bg-card/50 p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Users className="h-4 w-4 text-blue-400" />
                    <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground/50">Sessions</span>
                  </div>
                  <p className="text-lg font-bold tabular-nums">{system.active_sessions}</p>
                </div>
                <div className="rounded-xl border border-border/50 bg-card/50 p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Cpu className="h-4 w-4 text-orange-400" />
                    <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground/50">Backend</span>
                  </div>
                  <p className="text-sm font-bold truncate">{system.config.backend}</p>
                  <p className="text-[10px] text-muted-foreground/50 truncate">{system.config.model}</p>
                </div>
                <div className="rounded-xl border border-border/50 bg-card/50 p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Wrench className="h-4 w-4 text-purple-400" />
                    <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground/50">Tools Used</span>
                  </div>
                  <p className="text-lg font-bold tabular-nums">{tools.length}</p>
                </div>
              </div>

              {/* System resources */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {system.cpu && (
                  <div className="rounded-xl border border-border/50 bg-card/50 p-4 space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Cpu className="h-4 w-4 text-cyan-400" />
                        <span className="text-xs font-medium">CPU</span>
                      </div>
                      <span className="text-xs text-muted-foreground/60 tabular-nums">{system.cpu.percent}%</span>
                    </div>
                    <ProgressBar percent={system.cpu.percent} color={system.cpu.percent > 80 ? "bg-red-500" : system.cpu.percent > 50 ? "bg-yellow-500" : "bg-cyan-400"} />
                    <p className="text-[10px] text-muted-foreground/40">{system.cpu.count} cores &middot; {system.architecture}</p>
                  </div>
                )}
                {system.memory && (
                  <div className="rounded-xl border border-border/50 bg-card/50 p-4 space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <MemoryStick className="h-4 w-4 text-green-400" />
                        <span className="text-xs font-medium">Memory</span>
                      </div>
                      <span className="text-xs text-muted-foreground/60 tabular-nums">{system.memory.percent_used}%</span>
                    </div>
                    <ProgressBar percent={system.memory.percent_used} color={system.memory.percent_used > 85 ? "bg-red-500" : system.memory.percent_used > 60 ? "bg-yellow-500" : "bg-green-400"} />
                    <p className="text-[10px] text-muted-foreground/40">
                      {(system.memory.available_mb / 1024).toFixed(1)}GB free of {(system.memory.total_mb / 1024).toFixed(1)}GB
                    </p>
                  </div>
                )}
                {system.disk && (
                  <div className="rounded-xl border border-border/50 bg-card/50 p-4 space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <HardDrive className="h-4 w-4 text-orange-400" />
                        <span className="text-xs font-medium">Disk</span>
                      </div>
                      <span className="text-xs text-muted-foreground/60 tabular-nums">
                        {((1 - system.disk.free_gb / system.disk.total_gb) * 100).toFixed(0)}%
                      </span>
                    </div>
                    <ProgressBar
                      percent={(1 - system.disk.free_gb / system.disk.total_gb) * 100}
                      color={(1 - system.disk.free_gb / system.disk.total_gb) > 0.85 ? "bg-red-500" : "bg-orange-400"}
                    />
                    <p className="text-[10px] text-muted-foreground/40">{system.disk.free_gb}GB free of {system.disk.total_gb}GB</p>
                  </div>
                )}
              </div>

              {/* System info */}
              <div className="rounded-xl border border-border/50 bg-card/50 p-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-xs font-medium">System Information</h3>
                  <button
                    onClick={() => { setShowReloadDialog(true); setReloadError(null); setReloadSuccess(false); }}
                    className="flex items-center gap-1.5 rounded-lg border border-border/50 bg-muted/30 px-2.5 py-1 text-[10px] text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                  >
                    <RotateCw className="h-3 w-3" />
                    Reload Config
                  </button>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                  <div>
                    <p className="text-[10px] text-muted-foreground/40 uppercase tracking-wider">Platform</p>
                    <p className="font-mono text-muted-foreground truncate">{system.platform}</p>
                  </div>
                  <div>
                    <p className="text-[10px] text-muted-foreground/40 uppercase tracking-wider">Python</p>
                    <p className="font-mono text-muted-foreground">{system.python_version}</p>
                  </div>
                  <div>
                    <p className="text-[10px] text-muted-foreground/40 uppercase tracking-wider">Max Tokens</p>
                    <p className="font-mono text-muted-foreground">{system.config.max_tokens.toLocaleString()}</p>
                  </div>
                  <div>
                    <p className="text-[10px] text-muted-foreground/40 uppercase tracking-wider">Tool Timeout</p>
                    <p className="font-mono text-muted-foreground">{system.config.tool_timeout}s</p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Sessions Tab */}
          {activeTab === "sessions" && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <p className="text-xs text-muted-foreground/60">{sessionsTotal} total sessions across all users</p>
                {sessions.length > 0 && (
                  <button
                    onClick={exportSessionsCSV}
                    className="flex items-center gap-1.5 rounded-lg border border-border/50 bg-muted/30 px-2.5 py-1 text-[10px] text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                  >
                    <Download className="h-3 w-3" />
                    Export CSV
                  </button>
                )}
              </div>
              <div className="rounded-xl border border-border/50 overflow-hidden">
                <div className="grid grid-cols-[1fr_1fr_auto_auto_auto_auto] gap-2 px-4 py-2 bg-muted/30 border-b border-border/30 text-[10px] font-medium uppercase tracking-wider text-muted-foreground/50">
                  <span>Session</span>
                  <span>User</span>
                  <span>Messages</span>
                  <span>Last Active</span>
                  <span>Status</span>
                  <span className="w-10"></span>
                </div>
                {sessions.length === 0 ? (
                  <div className="px-4 py-8 text-center text-xs text-muted-foreground/40">No sessions found</div>
                ) : (
                  sessions.map((s) => (
                    <div key={s.session_id} className="grid grid-cols-[1fr_1fr_auto_auto_auto_auto] gap-2 items-center px-4 py-2.5 border-b border-border/20 hover:bg-muted/20 transition-colors text-xs group">
                      <span className="font-mono text-[10px] text-muted-foreground truncate" title={s.session_id}>
                        {s.session_id.slice(0, 8)}...
                      </span>
                      <span className="text-muted-foreground/70 truncate" title={s.user_id}>{s.user_id.slice(0, 12)}...</span>
                      <span className="tabular-nums text-center w-16">{s.message_count}</span>
                      <span className="text-muted-foreground/50 w-20 text-right">{timeAgo(s.last_active)}</span>
                      <span className={`w-16 text-center rounded-full px-2 py-0.5 text-[9px] font-medium ${
                        s.archived ? "bg-muted text-muted-foreground/50" : "bg-green-400/10 text-green-400"
                      }`}>
                        {s.archived ? "Archived" : "Active"}
                      </span>
                      <span className="w-10 flex justify-center">
                        {!s.archived && (
                          <button
                            onClick={() => terminateSession(s.session_id)}
                            disabled={terminatingId === s.session_id}
                            title="Terminate session"
                            className="p-1 rounded-md text-muted-foreground/30 hover:text-red-400 hover:bg-red-400/10 transition-colors opacity-0 group-hover:opacity-100 disabled:opacity-50"
                          >
                            {terminatingId === s.session_id ? (
                              <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            ) : (
                              <Trash2 className="h-3.5 w-3.5" />
                            )}
                          </button>
                        )}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {/* Tools Tab */}
          {activeTab === "tools" && (
            <div className="space-y-3">
              <p className="text-xs text-muted-foreground/60">{tools.reduce((sum, t) => sum + t.calls, 0).toLocaleString()} total tool calls across all sessions</p>
              <div className="rounded-xl border border-border/50 overflow-hidden">
                <div className="grid grid-cols-[1fr_auto_auto_auto] gap-2 px-4 py-2 bg-muted/30 border-b border-border/30 text-[10px] font-medium uppercase tracking-wider text-muted-foreground/50">
                  <span>Tool</span>
                  <span>Calls</span>
                  <span>Errors</span>
                  <span>Avg Time</span>
                </div>
                {tools.length === 0 ? (
                  <div className="px-4 py-8 text-center text-xs text-muted-foreground/40">No tool usage data</div>
                ) : (
                  tools.map((t) => (
                    <div key={t.name} className="grid grid-cols-[1fr_auto_auto_auto] gap-2 items-center px-4 py-2.5 border-b border-border/20 hover:bg-muted/20 transition-colors text-xs">
                      <span className="font-mono font-medium">{t.name}</span>
                      <span className="tabular-nums text-right w-16">{t.calls.toLocaleString()}</span>
                      <span className={`tabular-nums text-right w-16 ${t.errors > 0 ? "text-red-400" : "text-muted-foreground/40"}`}>
                        {t.errors}
                      </span>
                      <span className="tabular-nums text-right w-20 text-muted-foreground/60">{t.avg_ms}ms</span>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {/* Audit Log Tab */}
          {activeTab === "audit" && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <p className="text-xs text-muted-foreground/60">{auditLogs.length} recent audit entries</p>
                {auditLogs.length > 0 && (
                  <button
                    onClick={exportAuditCSV}
                    className="flex items-center gap-1.5 rounded-lg border border-border/50 bg-muted/30 px-2.5 py-1 text-[10px] text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                  >
                    <Download className="h-3 w-3" />
                    Export CSV
                  </button>
                )}
              </div>
              <div className="space-y-1">
                {auditLogs.length === 0 ? (
                  <div className="rounded-xl border border-border/50 px-4 py-8 text-center text-xs text-muted-foreground/40">No audit logs</div>
                ) : (
                  auditLogs.map((entry, idx) => {
                    const isExpanded = auditExpanded.has(idx);
                    const isWarning = entry.action.includes("denied") || entry.action.includes("failed") || entry.action.includes("delete");
                    return (
                      <div key={idx} className={`rounded-lg border ${isWarning ? "border-red-500/20" : "border-border/30"} overflow-hidden`}>
                        <button
                          onClick={() => {
                            setAuditExpanded((prev) => {
                              const next = new Set(prev);
                              if (next.has(idx)) next.delete(idx); else next.add(idx);
                              return next;
                            });
                          }}
                          className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs hover:bg-muted/30 transition-colors"
                        >
                          {isExpanded ? <ChevronDown className="h-3 w-3 shrink-0 text-muted-foreground/40" /> : <ChevronRight className="h-3 w-3 shrink-0 text-muted-foreground/40" />}
                          <span className={`font-mono text-[10px] px-1.5 py-0.5 rounded ${
                            isWarning ? "bg-red-500/10 text-red-400" : "bg-muted text-muted-foreground/70"
                          }`}>
                            {entry.action}
                          </span>
                          <span className="text-muted-foreground/60 truncate">{entry.username}</span>
                          <span className="ml-auto text-[10px] text-muted-foreground/30 shrink-0 tabular-nums">
                            {new Date(entry.timestamp).toLocaleString()}
                          </span>
                        </button>
                        {isExpanded && (
                          <div className="px-3 pb-2 pt-0 text-[11px] text-muted-foreground/50 space-y-1 border-t border-border/20 bg-muted/10">
                            {entry.detail && <p><span className="text-muted-foreground/30">Detail:</span> {entry.detail}</p>}
                            <p><span className="text-muted-foreground/30">User ID:</span> {entry.user_id}</p>
                            {entry.ip && <p><span className="text-muted-foreground/30">IP:</span> {entry.ip}</p>}
                          </div>
                        )}
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          )}
        </div>

        {/* Config Reload Dialog */}
        {showReloadDialog && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={() => setShowReloadDialog(false)}>
            <div className="relative w-full max-w-sm mx-4 rounded-xl border border-border/50 bg-background p-5 shadow-2xl" onClick={(e) => e.stopPropagation()}>
              <button
                onClick={() => setShowReloadDialog(false)}
                className="absolute top-3 right-3 p-1 text-muted-foreground/40 hover:text-foreground transition-colors"
              >
                <X className="h-4 w-4" />
              </button>

              {reloadSuccess ? (
                <div className="text-center py-4 space-y-2">
                  <div className="flex justify-center">
                    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-green-400/10">
                      <RotateCw className="h-5 w-5 text-green-400" />
                    </div>
                  </div>
                  <p className="text-sm font-medium text-green-400">Config Reloaded</p>
                </div>
              ) : (
                <>
                  <div className="flex items-center gap-2 mb-4">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
                      <Lock className="h-4 w-4 text-primary" />
                    </div>
                    <div>
                      <h3 className="text-sm font-medium">Reload Configuration</h3>
                      <p className="text-[10px] text-muted-foreground/50">Confirm your password to reload config.yaml</p>
                    </div>
                  </div>

                  {reloadError && (
                    <div className="mb-3 rounded-lg bg-red-500/10 border border-red-500/20 px-3 py-2 text-xs text-red-400">
                      {reloadError}
                    </div>
                  )}

                  <form
                    onSubmit={(e) => { e.preventDefault(); handleReloadConfig(); }}
                    className="space-y-3"
                  >
                    <input
                      type="password"
                      value={reloadPassword}
                      onChange={(e) => setReloadPassword(e.target.value)}
                      placeholder="Admin password"
                      autoFocus
                      className="w-full rounded-lg border border-border/50 bg-muted/30 px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/30 focus:outline-none focus:ring-1 focus:ring-primary/50"
                    />
                    <div className="flex gap-2 justify-end">
                      <button
                        type="button"
                        onClick={() => setShowReloadDialog(false)}
                        className="rounded-lg px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
                      >
                        Cancel
                      </button>
                      <button
                        type="submit"
                        disabled={!reloadPassword || reloading}
                        className="flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
                      >
                        {reloading ? <Loader2 className="h-3 w-3 animate-spin" /> : <RotateCw className="h-3 w-3" />}
                        Reload
                      </button>
                    </div>
                  </form>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </ErrorBoundary>
  );
}
