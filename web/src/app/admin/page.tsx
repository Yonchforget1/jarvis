"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

interface AdminStats {
  total_users: number;
  admin_users: number;
  active_sessions: number;
  uptime_seconds: number;
  total_tasks: number;
  running_tasks: number;
  completed_tasks: number;
  failed_tasks: number;
}

interface UserInfo {
  id: string;
  username: string;
  email: string;
  role: string;
  created_at: string;
}

interface AuditEntry {
  timestamp: string;
  username: string;
  action: string;
  ip: string;
}

export default function AdminPage() {
  const router = useRouter();
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [users, setUsers] = useState<UserInfo[]>([]);
  const [audit, setAudit] = useState<AuditEntry[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"overview" | "users" | "audit">("overview");

  useEffect(() => {
    if (!api.isLoggedIn()) {
      router.push("/");
      return;
    }
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    try {
      const [s, u, a] = await Promise.all([
        api.getAdminStats(),
        api.getAdminUsers(),
        api.getAuditLog(50),
      ]);
      setStats(s);
      setUsers(u);
      setAudit(a.entries);
      setError("");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load admin data");
    } finally {
      setLoading(false);
    }
  }

  async function toggleRole(user: UserInfo) {
    const newRole = user.role === "admin" ? "user" : "admin";
    try {
      await api.updateUserRole(user.id, newRole);
      loadData();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to update role");
    }
  }

  async function handleDeleteUser(user: UserInfo) {
    if (!confirm(`Delete user "${user.username}"? This cannot be undone.`)) return;
    try {
      await api.deleteUser(user.id);
      loadData();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to delete user");
    }
  }

  function formatUptime(seconds: number): string {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    if (days > 0) return `${days}d ${hours}h ${mins}m`;
    if (hours > 0) return `${hours}h ${mins}m`;
    return `${mins}m`;
  }

  if (error && !stats) {
    return (
      <div className="min-h-screen bg-white dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold mb-4">Admin Dashboard</h1>
          <p className="text-red-500 dark:text-red-400">{error}</p>
          <button
            onClick={() => router.push("/chat")}
            className="mt-4 px-4 py-2 bg-zinc-200 dark:bg-zinc-700 rounded hover:bg-zinc-300 dark:hover:bg-zinc-600"
          >
            Back to Chat
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100">
      <div className="max-w-6xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold">Admin Dashboard</h1>
            <p className="text-sm text-zinc-500 mt-1">
              {users.length} users, {stats?.active_sessions || 0} active sessions
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={loadData}
              disabled={loading}
              className="px-4 py-2 bg-zinc-200 dark:bg-zinc-800 rounded-lg hover:bg-zinc-300 dark:hover:bg-zinc-700 text-sm disabled:opacity-50"
            >
              {loading ? "Loading..." : "Refresh"}
            </button>
            <button
              onClick={() => router.push("/chat")}
              className="px-4 py-2 bg-zinc-200 dark:bg-zinc-800 rounded-lg hover:bg-zinc-300 dark:hover:bg-zinc-700 text-sm"
            >
              Back to Chat
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-4 px-4 py-2 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded-lg text-sm">
            {error}
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-1 mb-6 bg-zinc-100 dark:bg-zinc-900 rounded-lg p-1 w-fit">
          {(["overview", "users", "audit"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-2 rounded-md text-sm font-medium transition ${
                tab === t
                  ? "bg-blue-600 text-white"
                  : "text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white hover:bg-zinc-200 dark:hover:bg-zinc-800"
              }`}
            >
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>

        {/* Overview Tab */}
        {tab === "overview" && stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard label="Total Users" value={stats.total_users} />
            <StatCard label="Admin Users" value={stats.admin_users} />
            <StatCard label="Active Sessions" value={stats.active_sessions} />
            <StatCard label="Uptime" value={formatUptime(stats.uptime_seconds)} />
            <StatCard label="Total Tasks" value={stats.total_tasks} />
            <StatCard label="Running" value={stats.running_tasks} color="blue" />
            <StatCard label="Completed" value={stats.completed_tasks} color="green" />
            <StatCard label="Failed" value={stats.failed_tasks} color="red" />
          </div>
        )}

        {tab === "overview" && loading && !stats && (
          <div className="text-center py-16 text-zinc-500">Loading stats...</div>
        )}

        {/* Users Tab */}
        {tab === "users" && (
          <div className="bg-zinc-50 dark:bg-zinc-900 rounded-xl overflow-hidden border border-zinc-200 dark:border-zinc-800">
            <table className="w-full">
              <thead>
                <tr className="border-b border-zinc-200 dark:border-zinc-800">
                  <th className="text-left px-4 py-3 text-sm text-zinc-500 dark:text-zinc-400">Username</th>
                  <th className="text-left px-4 py-3 text-sm text-zinc-500 dark:text-zinc-400">Email</th>
                  <th className="text-left px-4 py-3 text-sm text-zinc-500 dark:text-zinc-400">Role</th>
                  <th className="text-left px-4 py-3 text-sm text-zinc-500 dark:text-zinc-400">Created</th>
                  <th className="text-right px-4 py-3 text-sm text-zinc-500 dark:text-zinc-400">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-zinc-500">
                      {loading ? "Loading users..." : "No users found"}
                    </td>
                  </tr>
                ) : (
                  users.map((u) => (
                    <tr key={u.id} className="border-b border-zinc-100 dark:border-zinc-800/50 hover:bg-zinc-100 dark:hover:bg-zinc-800/30">
                      <td className="px-4 py-3 font-medium">{u.username}</td>
                      <td className="px-4 py-3 text-zinc-500 dark:text-zinc-400">{u.email || "-"}</td>
                      <td className="px-4 py-3">
                        <span
                          className={`px-2 py-1 rounded text-xs font-medium ${
                            u.role === "admin"
                              ? "bg-purple-100 dark:bg-purple-900/50 text-purple-700 dark:text-purple-300"
                              : "bg-zinc-200 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-300"
                          }`}
                        >
                          {u.role}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-zinc-500 dark:text-zinc-400 text-sm">
                        {new Date(u.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-4 py-3 text-right space-x-2">
                        <button
                          onClick={() => toggleRole(u)}
                          className="px-3 py-1 bg-zinc-200 dark:bg-zinc-700 rounded text-xs hover:bg-zinc-300 dark:hover:bg-zinc-600"
                        >
                          {u.role === "admin" ? "Demote" : "Promote"}
                        </button>
                        <button
                          onClick={() => handleDeleteUser(u)}
                          className="px-3 py-1 bg-red-100 dark:bg-red-900/50 text-red-600 dark:text-red-300 rounded text-xs hover:bg-red-200 dark:hover:bg-red-900"
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}

        {/* Audit Tab */}
        {tab === "audit" && (
          <div className="bg-zinc-50 dark:bg-zinc-900 rounded-xl overflow-hidden border border-zinc-200 dark:border-zinc-800">
            <table className="w-full">
              <thead>
                <tr className="border-b border-zinc-200 dark:border-zinc-800">
                  <th className="text-left px-4 py-3 text-sm text-zinc-500 dark:text-zinc-400">Time</th>
                  <th className="text-left px-4 py-3 text-sm text-zinc-500 dark:text-zinc-400">User</th>
                  <th className="text-left px-4 py-3 text-sm text-zinc-500 dark:text-zinc-400">Action</th>
                  <th className="text-left px-4 py-3 text-sm text-zinc-500 dark:text-zinc-400">IP</th>
                </tr>
              </thead>
              <tbody>
                {audit.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="px-4 py-8 text-center text-zinc-500">
                      {loading ? "Loading audit log..." : "No audit entries yet"}
                    </td>
                  </tr>
                ) : (
                  audit.map((entry, i) => (
                    <tr key={i} className="border-b border-zinc-100 dark:border-zinc-800/50 hover:bg-zinc-100 dark:hover:bg-zinc-800/30">
                      <td className="px-4 py-3 text-sm text-zinc-500 dark:text-zinc-400">
                        {new Date(entry.timestamp).toLocaleString()}
                      </td>
                      <td className="px-4 py-3">{entry.username || "-"}</td>
                      <td className="px-4 py-3">
                        <span
                          className={`px-2 py-1 rounded text-xs ${
                            entry.action === "login_failed"
                              ? "bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-300"
                              : entry.action === "register"
                              ? "bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-300"
                              : "bg-zinc-200 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-300"
                          }`}
                        >
                          {entry.action}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-zinc-500 dark:text-zinc-400 text-sm font-mono">{entry.ip || "-"}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  color,
}: {
  label: string;
  value: string | number;
  color?: "blue" | "green" | "red";
}) {
  const colorClass =
    color === "blue"
      ? "text-blue-600 dark:text-blue-400"
      : color === "green"
      ? "text-green-600 dark:text-green-400"
      : color === "red"
      ? "text-red-600 dark:text-red-400"
      : "text-zinc-900 dark:text-white";

  return (
    <div className="bg-zinc-50 dark:bg-zinc-900 rounded-xl p-4 border border-zinc-200 dark:border-zinc-800">
      <p className="text-sm text-zinc-500 dark:text-zinc-400 mb-1">{label}</p>
      <p className={`text-2xl font-bold ${colorClass}`}>{value}</p>
    </div>
  );
}
