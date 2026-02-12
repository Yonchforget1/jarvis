/**
 * API client for the Jarvis backend.
 * Talks to FastAPI on port 3000.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:3000";

interface AuthResponse {
  access_token: string;
  token_type: string;
  username: string;
  role: string;
}

interface ChatResponse {
  session_id: string;
  response: string;
  tool_calls: { name: string; args: Record<string, unknown> }[];
}

interface SessionInfo {
  session_id: string;
  title: string;
  message_count: number;
  created_at: string;
  last_active: string;
}

interface StatsResponse {
  uptime_seconds: number;
  active_sessions: number;
  memory_entries: number;
}

interface ToolInfo {
  name: string;
  description: string;
  parameters: Record<string, unknown>;
}

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("jarvis_token");
}

function setToken(token: string) {
  localStorage.setItem("jarvis_token", token);
}

function clearToken() {
  localStorage.removeItem("jarvis_token");
}

function getUsername(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("jarvis_username");
}

function setUsername(name: string) {
  localStorage.setItem("jarvis_username", name);
}

async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (res.status === 401) {
    clearToken();
    if (typeof window !== "undefined") {
      window.location.href = "/";
    }
    throw new Error("Unauthorized");
  }

  if (!res.ok) {
    const data = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(data.detail || `HTTP ${res.status}`);
  }

  return res.json();
}

export const api = {
  // Auth
  async register(username: string, password: string, email = "") {
    const data = await apiFetch<AuthResponse>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ username, password, email }),
    });
    setToken(data.access_token);
    setUsername(data.username);
    return data;
  },

  async login(username: string, password: string, rememberMe = false) {
    const data = await apiFetch<AuthResponse>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({
        username,
        password,
        remember_me: rememberMe,
      }),
    });
    setToken(data.access_token);
    setUsername(data.username);
    return data;
  },

  logout() {
    clearToken();
    localStorage.removeItem("jarvis_username");
  },

  isLoggedIn() {
    return !!getToken();
  },

  getUsername,

  // Chat
  async chat(message: string, sessionId?: string | null, model?: string | null) {
    return apiFetch<ChatResponse>("/api/chat", {
      method: "POST",
      body: JSON.stringify({
        message,
        session_id: sessionId || undefined,
        model: model || undefined,
      }),
    });
  },

  // Streaming chat
  async chatStream(
    message: string,
    sessionId: string | null | undefined,
    onChunk: (text: string) => void,
    onMeta: (data: { session_id: string }) => void,
    onDone: (fullText: string) => void,
    onError: (error: string) => void,
    model?: string | null
  ) {
    const token = getToken();
    const res = await fetch(`${API_BASE}/api/chat?stream=true`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        message,
        session_id: sessionId || undefined,
        model: model || undefined,
      }),
    });

    if (!res.ok) {
      const data = await res.json().catch(() => ({ detail: res.statusText }));
      onError(data.detail || `HTTP ${res.status}`);
      return;
    }

    const reader = res.body?.getReader();
    if (!reader) {
      onError("No response body");
      return;
    }

    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      let eventType = "message";
      for (const line of lines) {
        if (line.startsWith("event: ")) {
          eventType = line.slice(7).trim();
        } else if (line.startsWith("data: ")) {
          try {
            const data = JSON.parse(line.slice(6));
            if (eventType === "meta") {
              onMeta(data);
            } else if (eventType === "done") {
              onDone(data.full_text);
            } else if (eventType === "error") {
              onError(data.error);
            } else if (data.text !== undefined) {
              onChunk(data.text);
            }
          } catch {
            // ignore parse errors
          }
          eventType = "message";
        }
      }
    }
  },

  // Sessions
  async getSessions(limit = 50, offset = 0) {
    const data = await apiFetch<{ sessions: SessionInfo[]; total: number }>(`/api/sessions?limit=${limit}&offset=${offset}`);
    return data.sessions;
  },

  async renameSession(sessionId: string, name: string) {
    return apiFetch<{ status: string; name: string }>(
      `/api/sessions/${sessionId}`,
      { method: "PATCH", body: JSON.stringify({ name }) }
    );
  },

  async pinSession(sessionId: string, pinned: boolean) {
    return apiFetch<{ status: string; pinned: boolean }>(
      `/api/sessions/${sessionId}`,
      { method: "PATCH", body: JSON.stringify({ pinned }) }
    );
  },

  async getSessionMessages(sessionId: string) {
    return apiFetch<{ session_id: string; messages: { role: string; content: string }[] }>(
      `/api/sessions/${sessionId}/messages`
    );
  },

  async forkSession(sessionId: string, fromIndex = -1) {
    return apiFetch<{ session_id: string; title: string; message_count: number }>(
      `/api/sessions/${sessionId}/fork?from_index=${fromIndex}`,
      { method: "POST" }
    );
  },

  async deleteSession(sessionId: string) {
    return apiFetch<{ status: string }>(
      `/api/sessions/${sessionId}`,
      { method: "DELETE" }
    );
  },

  // Tools
  async getTools() {
    const data = await apiFetch<{ tools: ToolInfo[] }>("/api/tools");
    return data.tools;
  },

  // Stats
  async getStats() {
    return apiFetch<StatsResponse>("/api/stats");
  },

  // Settings
  async getSettings() {
    return apiFetch<{
      backend: string;
      model: string;
      max_tokens: number;
      system_prompt: string;
      available_backends: string[];
    }>("/api/settings");
  },

  async updateSettings(settings: {
    backend?: string;
    model?: string;
    max_tokens?: number;
    system_prompt?: string;
    api_key?: string;
  }) {
    return apiFetch<{ status: string; changed: string[] }>("/api/settings", {
      method: "PATCH",
      body: JSON.stringify(settings),
    });
  },

  // Admin
  async getAdminUsers() {
    return apiFetch<{ id: string; username: string; email: string; role: string; created_at: string }[]>("/api/admin/users");
  },

  async updateUserRole(userId: string, role: string) {
    return apiFetch<{ status: string; changed: Record<string, string> }>(`/api/admin/users/${userId}`, {
      method: "PATCH",
      body: JSON.stringify({ role }),
    });
  },

  async deleteUser(userId: string) {
    return apiFetch<{ status: string; username: string }>(`/api/admin/users/${userId}`, {
      method: "DELETE",
    });
  },

  async getAdminStats() {
    return apiFetch<{
      total_users: number;
      admin_users: number;
      active_sessions: number;
      uptime_seconds: number;
      total_tasks: number;
      running_tasks: number;
      completed_tasks: number;
      failed_tasks: number;
    }>("/api/admin/stats");
  },

  async getAuditLog(limit = 50) {
    return apiFetch<{ entries: { timestamp: string; username: string; action: string; ip: string }[]; total: number }>(`/api/admin/audit?limit=${limit}`);
  },

  async getUsage() {
    return apiFetch<{
      total_input_tokens: number;
      total_output_tokens: number;
      total_tokens: number;
      total_requests: number;
      estimated_cost_usd: number;
    }>("/api/usage");
  },

  // API Keys
  async getApiKeys() {
    return apiFetch<{ key_id: string; name: string; prefix: string; created_at: string; usage_count: number }[]>("/api/keys");
  },

  async createApiKey(name: string) {
    return apiFetch<{ key_id: string; name: string; key: string; warning: string }>("/api/keys", {
      method: "POST",
      body: JSON.stringify({ name }),
    });
  },

  async revokeApiKey(keyId: string) {
    return apiFetch<{ status: string }>(`/api/keys/${keyId}`, { method: "DELETE" });
  },

  // Schedules
  async getSchedules() {
    return apiFetch<{
      schedule_id: string;
      name: string;
      cron: string;
      task_type: string;
      payload: Record<string, unknown>;
      enabled: boolean;
      last_run: string | null;
      last_status: string | null;
      run_count: number;
      consecutive_failures: number;
    }[]>("/api/schedules");
  },

  async createSchedule(name: string, cron: string, taskType: string, payload: Record<string, unknown>) {
    return apiFetch<Record<string, unknown>>("/api/schedules", {
      method: "POST",
      body: JSON.stringify({ name, cron, task_type: taskType, payload }),
    });
  },

  async updateSchedule(scheduleId: string, updates: { name?: string; cron?: string; enabled?: boolean }) {
    return apiFetch<Record<string, unknown>>(`/api/schedules/${scheduleId}`, {
      method: "PATCH",
      body: JSON.stringify(updates),
    });
  },

  async deleteSchedule(scheduleId: string) {
    return apiFetch<{ status: string }>(`/api/schedules/${scheduleId}`, { method: "DELETE" });
  },

  async getCronAliases() {
    return apiFetch<{
      aliases: Record<string, string>;
      examples: { cron: string; description: string }[];
    }>("/api/schedules/cron-aliases");
  },

  // Sharing
  async shareSession(sessionId: string, expiresHours?: number) {
    return apiFetch<{ share_id: string; url: string; expires_at: string | null }>("/api/share", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, expires_hours: expiresHours || undefined }),
    });
  },

  async getShares() {
    return apiFetch<{ share_id: string; title: string; created_at: string; expires_at: string | null; view_count: number }[]>("/api/share");
  },

  async deleteShare(shareId: string) {
    return apiFetch<{ status: string }>(`/api/share/${shareId}`, { method: "DELETE" });
  },

  // Templates
  async getTemplates() {
    return apiFetch<{
      id: string;
      name: string;
      description: string;
      category: string;
      icon: string;
      prompt: string;
      custom: boolean;
    }[]>("/api/templates");
  },

  async createTemplate(name: string, description: string, category: string, prompt: string) {
    return apiFetch<Record<string, unknown>>("/api/templates", {
      method: "POST",
      body: JSON.stringify({ name, description, category, prompt }),
    });
  },

  async deleteTemplate(templateId: string) {
    return apiFetch<{ status: string }>(`/api/templates/${templateId}`, { method: "DELETE" });
  },

  // Uploads
  async uploadFile(file: File) {
    const formData = new FormData();
    formData.append("file", file);
    const token = localStorage.getItem("jarvis_token");
    const res = await fetch(`${API_BASE}/api/uploads`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: formData,
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(data.detail || "Upload failed");
    }
    return res.json() as Promise<{ file_id: string; filename: string; size: number }>;
  },

  async getUploads() {
    return apiFetch<{ file_id: string; filename: string; size: number }[]>("/api/uploads");
  },

  async deleteUpload(fileId: string) {
    return apiFetch<{ status: string }>(`/api/uploads/${fileId}`, { method: "DELETE" });
  },

  async getFileContent(fileId: string) {
    return apiFetch<{ file_id: string; filename: string; content: string }>(`/api/uploads/${fileId}/content`);
  },

  // Search
  async searchSessions(query: string) {
    return apiFetch<{
      results: { session_id: string; title: string; matches: { role: string; content: string }[] }[];
    }>(`/api/sessions/search?q=${encodeURIComponent(query)}`);
  },

  // Health (no auth needed)
  async health() {
    const res = await fetch(`${API_BASE}/api/health`);
    return res.json();
  },
};
