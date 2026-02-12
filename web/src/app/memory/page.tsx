"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

interface Learning {
  id: string;
  category: string;
  insight: string;
  context: string;
  task_description: string;
  timestamp: string;
}

interface SearchResult {
  id: string;
  text: string;
  distance: number;
}

export default function MemoryPage() {
  const router = useRouter();
  const [learnings, setLearnings] = useState<Learning[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [categoryFilter, setCategoryFilter] = useState("");

  useEffect(() => {
    if (!api.isLoggedIn()) {
      router.push("/");
      return;
    }
    loadLearnings();
  }, [router]);

  async function loadLearnings() {
    try {
      const data = await api.getMemoryLearnings("", 100);
      setLearnings(data.learnings);
      setTotal(data.total);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }

  async function handleSearch(query: string) {
    setSearchQuery(query);
    if (!query.trim()) {
      setSearchResults([]);
      return;
    }
    setSearching(true);
    try {
      const data = await api.searchMemory(query);
      setSearchResults(data.results);
    } catch {
      setSearchResults([]);
    } finally {
      setSearching(false);
    }
  }

  const categories = [...new Set(learnings.map((l) => l.category))].sort();
  const filtered = categoryFilter
    ? learnings.filter((l) => l.category === categoryFilter)
    : learnings;

  function formatDate(ts: string): string {
    try {
      const d = new Date(ts);
      return d.toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return ts;
    }
  }

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-white dark:bg-zinc-950 text-zinc-500">
        Loading memory...
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100">
      <header className="flex items-center justify-between px-6 py-4 bg-zinc-100 dark:bg-zinc-900 border-b border-zinc-200 dark:border-zinc-800">
        <div>
          <h1 className="text-lg font-semibold">Memory</h1>
          <p className="text-xs text-zinc-500">{total} learnings stored</p>
        </div>
        <button
          onClick={() => router.push("/chat")}
          className="text-sm text-zinc-400 hover:text-zinc-900 dark:hover:text-white border border-zinc-300 dark:border-zinc-700 rounded px-3 py-1"
        >
          Back to Chat
        </button>
      </header>

      <div className="max-w-4xl mx-auto p-6 space-y-6">
        {/* Search */}
        <div className="flex gap-3">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => handleSearch(e.target.value)}
            placeholder="Search memory (semantic)..."
            className="flex-1 bg-zinc-100 dark:bg-zinc-900 border border-zinc-300 dark:border-zinc-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
          />
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="bg-zinc-100 dark:bg-zinc-900 border border-zinc-300 dark:border-zinc-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
          >
            <option value="">All categories</option>
            {categories.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>

        {/* Search Results */}
        {searchQuery && (
          <div className="space-y-2">
            <h2 className="text-sm font-semibold text-zinc-500">
              {searching ? "Searching..." : `Search results (${searchResults.length})`}
            </h2>
            {searchResults.map((r) => (
              <div
                key={r.id}
                className="bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg p-4"
              >
                <p className="text-sm text-zinc-700 dark:text-zinc-300">{r.text}</p>
                <div className="mt-2 flex items-center gap-3">
                  <span className="text-xs text-zinc-500">Relevance: {(1 - r.distance).toFixed(2)}</span>
                  <span className="text-xs text-zinc-500 font-mono">{r.id}</span>
                </div>
              </div>
            ))}
            {!searching && searchResults.length === 0 && (
              <p className="text-sm text-zinc-500">No results found</p>
            )}
          </div>
        )}

        {/* Learnings List */}
        {!searchQuery && (
          <div className="space-y-3">
            <h2 className="text-sm font-semibold text-zinc-500">
              {categoryFilter ? `${categoryFilter} (${filtered.length})` : `All Learnings (${filtered.length})`}
            </h2>
            {filtered.length === 0 && (
              <p className="text-sm text-zinc-500">No learnings yet. Chat with Jarvis to build memory.</p>
            )}
            {[...filtered].reverse().map((l) => (
              <div
                key={l.id}
                className="bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg p-4"
              >
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300">
                    {l.category}
                  </span>
                  <span className="text-xs text-zinc-500">{formatDate(l.timestamp)}</span>
                </div>
                <p className="text-sm font-medium text-zinc-800 dark:text-zinc-200">{l.insight}</p>
                {l.context && (
                  <p className="mt-1 text-xs text-zinc-500 line-clamp-2">{l.context}</p>
                )}
                {l.task_description && (
                  <p className="mt-1 text-xs text-zinc-400">Task: {l.task_description}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
