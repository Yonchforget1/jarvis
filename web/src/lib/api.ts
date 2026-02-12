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
  async chat(message: string, sessionId?: string | null) {
    return apiFetch<ChatResponse>("/api/chat", {
      method: "POST",
      body: JSON.stringify({
        message,
        session_id: sessionId || undefined,
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
    onError: (error: string) => void
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
  async getSessions() {
    return apiFetch<SessionInfo[]>("/api/sessions");
  },

  async renameSession(sessionId: string, name: string) {
    return apiFetch<{ status: string; name: string }>(
      `/api/sessions/${sessionId}`,
      { method: "PATCH", body: JSON.stringify({ name }) }
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

  // Health (no auth needed)
  async health() {
    const res = await fetch(`${API_BASE}/api/health`);
    return res.json();
  },
};
