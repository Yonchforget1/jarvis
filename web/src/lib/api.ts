const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const DEFAULT_TIMEOUT = 30000; // 30 seconds
const MAX_RETRIES = 2;
const RETRY_DELAY = 1000; // 1 second
const SLOW_REQUEST_MS = 3000; // Warn in console if request exceeds this

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
  // Retry on 429 rate limit (with longer backoff handled in request())
  if (error instanceof ApiError && error.status === 429) return true;
  // Retry on 5xx server errors
  if (error instanceof ApiError && error.status >= 500) return true;
  return false;
}

async function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// Deduplicate in-flight GET requests to the same path
const inflightGets = new Map<string, Promise<unknown>>();

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
  const requestStart = performance.now();

  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT);
    try {
      const res = await fetch(`${API_URL}${path}`, {
        ...options,
        headers,
        signal: options.signal || controller.signal,
      });

      clearTimeout(timeout);
      const elapsed = Math.round(performance.now() - requestStart);
      if (elapsed > SLOW_REQUEST_MS) {
        console.warn(`[api] Slow request: ${options.method || "GET"} ${path} took ${elapsed}ms`);
      }

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

      // Handle 204 No Content (common for DELETE)
      if (res.status === 204 || res.headers.get("content-length") === "0") {
        return undefined as T;
      }
      return res.json();
    } catch (err) {
      clearTimeout(timeout);
      lastError = err;
      // Don't retry 401s or non-retryable errors
      if (err instanceof ApiError && err.status === 401) throw err;
      if (!isRetryable(err) || attempt === MAX_RETRIES) throw err;
      // Wait before retrying with exponential backoff + jitter
      // Use longer base delay for 429 rate limits
      const is429 = err instanceof ApiError && err.status === 429;
      const base = is429 ? RETRY_DELAY * 4 : RETRY_DELAY;
      const baseDelay = Math.min(base * Math.pow(2, attempt), 30000);
      const jitter = Math.random() * baseDelay * 0.1;
      await sleep(baseDelay + jitter);
    }
  }

  throw lastError;
}

export const api = {
  get: <T>(path: string): Promise<T> => {
    const existing = inflightGets.get(path);
    if (existing) return existing as Promise<T>;
    const promise = request<T>(path).finally(() => inflightGets.delete(path));
    inflightGets.set(path, promise);
    return promise;
  },
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body) }),
  put: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PUT", body: JSON.stringify(body) }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
  /** Clear a cached in-flight GET so the next call fetches fresh data. */
  invalidate: (path: string) => {
    inflightGets.delete(path);
  },
  /** Clear all cached in-flight GETs. */
  invalidateAll: () => {
    inflightGets.clear();
  },
};

export { ApiError };
