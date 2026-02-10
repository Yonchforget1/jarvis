const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const DEFAULT_TIMEOUT = 30000; // 30 seconds
const MAX_RETRIES = 2;
const RETRY_DELAY = 1000; // 1 second

class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

function isRetryable(error: unknown): boolean {
  // Retry on network errors (no response)
  if (error instanceof TypeError && error.message.includes("fetch")) return true;
  // Retry on timeout
  if (error instanceof DOMException && error.name === "AbortError") return true;
  // Retry on 5xx server errors
  if (error instanceof ApiError && error.status >= 500) return true;
  return false;
}

async function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = typeof window !== "undefined" ? localStorage.getItem("jarvis_token") : null;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  let lastError: unknown;

  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT);

      const res = await fetch(`${API_URL}${path}`, {
        ...options,
        headers,
        signal: options.signal || controller.signal,
      });

      clearTimeout(timeout);

      if (res.status === 401) {
        if (typeof window !== "undefined") {
          localStorage.removeItem("jarvis_token");
          localStorage.removeItem("jarvis_user");
          window.location.href = "/login";
        }
        throw new ApiError("Unauthorized", 401);
      }

      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: res.statusText }));
        throw new ApiError(body.detail || res.statusText, res.status);
      }

      return res.json();
    } catch (err) {
      lastError = err;
      // Don't retry 401s or non-retryable errors
      if (err instanceof ApiError && err.status === 401) throw err;
      if (!isRetryable(err) || attempt === MAX_RETRIES) throw err;
      // Wait before retrying with exponential backoff + jitter
      const baseDelay = RETRY_DELAY * Math.pow(2, attempt);
      const jitter = Math.random() * baseDelay * 0.1;
      await sleep(baseDelay + jitter);
    }
  }

  throw lastError;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body) }),
  put: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PUT", body: JSON.stringify(body) }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};

export { ApiError };
