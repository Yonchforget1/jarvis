"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

interface Tool {
  name: string;
  description: string;
  parameters: Record<string, unknown>;
}

const CATEGORY_MAP: Record<string, string> = {
  read_file: "Filesystem",
  write_file: "Filesystem",
  list_directory: "Filesystem",
  delete_file: "Filesystem",
  copy_file: "Filesystem",
  move_file: "Filesystem",
  file_info: "Filesystem",
  search_files: "Filesystem",
  run_shell: "Shell",
  run_python: "Shell",
  search_web: "Web",
  fetch_url: "Web",
  http_request: "Web",
  send_email: "Communication",
  create_godot_project: "Game Dev",
  system_info: "System",
  get_env_var: "System",
  list_env_vars: "System",
  clipboard_read: "System",
  clipboard_write: "System",
  create_plan: "Planning",
  update_plan: "Planning",
  save_learning: "Memory",
  search_learnings: "Memory",
  csv_query: "Data",
  json_transform: "Data",
  text_transform: "Data",
};

function getCategory(name: string): string {
  if (CATEGORY_MAP[name]) return CATEGORY_MAP[name];
  if (name.includes("file") || name.includes("dir")) return "Filesystem";
  if (name.includes("shell") || name.includes("python")) return "Shell";
  if (name.includes("web") || name.includes("http") || name.includes("url")) return "Web";
  if (name.includes("plan")) return "Planning";
  if (name.includes("learn") || name.includes("memory")) return "Memory";
  return "Other";
}

export default function ToolsPage() {
  const router = useRouter();
  const [tools, setTools] = useState<Tool[]>([]);
  const [filter, setFilter] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [expandedTool, setExpandedTool] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!api.isLoggedIn()) {
      router.push("/");
      return;
    }
    loadTools();
  }, []);

  async function loadTools() {
    try {
      const data = await api.getTools();
      setTools(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load tools");
    }
  }

  const categories = [...new Set(tools.map((t) => getCategory(t.name)))].sort();

  const filtered = tools.filter((t) => {
    const matchesFilter =
      !filter ||
      t.name.toLowerCase().includes(filter.toLowerCase()) ||
      t.description.toLowerCase().includes(filter.toLowerCase());
    const matchesCategory = !selectedCategory || getCategory(t.name) === selectedCategory;
    return matchesFilter && matchesCategory;
  });

  return (
    <div className="min-h-screen bg-zinc-950 text-white">
      <div className="max-w-5xl mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold">Tools</h1>
            <p className="text-zinc-400 text-sm mt-1">
              {tools.length} tools available for Jarvis to use
            </p>
          </div>
          <button
            onClick={() => router.push("/chat")}
            className="px-4 py-2 bg-zinc-800 rounded-lg hover:bg-zinc-700 text-sm"
          >
            Back to Chat
          </button>
        </div>

        {error && (
          <div className="bg-red-900/30 border border-red-800 text-red-300 px-4 py-2 rounded-lg mb-4">
            {error}
          </div>
        )}

        {/* Search and Category Filter */}
        <div className="flex flex-col sm:flex-row gap-3 mb-6">
          <input
            type="text"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="Search tools..."
            className="flex-1 bg-zinc-900 text-white px-4 py-2.5 rounded-lg border border-zinc-700 focus:border-blue-500 focus:outline-none"
          />
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setSelectedCategory(null)}
              className={`px-3 py-2 rounded-lg text-xs transition ${
                !selectedCategory
                  ? "bg-blue-600 text-white"
                  : "bg-zinc-900 text-zinc-400 hover:bg-zinc-800"
              }`}
            >
              All
            </button>
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat === selectedCategory ? null : cat)}
                className={`px-3 py-2 rounded-lg text-xs transition ${
                  selectedCategory === cat
                    ? "bg-blue-600 text-white"
                    : "bg-zinc-900 text-zinc-400 hover:bg-zinc-800"
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>

        {/* Results count */}
        <p className="text-zinc-500 text-sm mb-4">
          Showing {filtered.length} of {tools.length} tools
        </p>

        {/* Tool cards */}
        <div className="space-y-2">
          {filtered.map((tool) => (
            <div
              key={tool.name}
              className="bg-zinc-900 rounded-xl border border-zinc-800 overflow-hidden"
            >
              <div
                className="flex items-center justify-between px-4 py-3 cursor-pointer hover:bg-zinc-800/50 transition"
                onClick={() => setExpandedTool(expandedTool === tool.name ? null : tool.name)}
              >
                <div className="flex items-center gap-3">
                  <span className="font-mono text-sm font-medium text-blue-400">
                    {tool.name}
                  </span>
                  <span className="px-2 py-0.5 rounded text-xs bg-zinc-800 text-zinc-400">
                    {getCategory(tool.name)}
                  </span>
                </div>
                <span className="text-zinc-500 text-sm">
                  {expandedTool === tool.name ? "−" : "+"}
                </span>
              </div>

              <div className="px-4 pb-3 text-sm text-zinc-400">
                {tool.description}
              </div>

              {expandedTool === tool.name && tool.parameters && (
                <div className="px-4 pb-4 border-t border-zinc-800 pt-3">
                  <h4 className="text-xs font-medium text-zinc-500 uppercase mb-2">
                    Parameters
                  </h4>
                  <div className="space-y-2">
                    {Object.entries(
                      (tool.parameters as Record<string, Record<string, unknown>>)?.properties || {}
                    ).map(([name, rawSchema]) => {
                      const schema = rawSchema as Record<string, unknown>;
                      return (
                      <div key={name} className="flex items-start gap-3">
                        <code className="text-xs font-mono text-yellow-400 min-w-[120px]">
                          {name}
                        </code>
                        <span className="text-xs text-zinc-500">
                          {String(schema.type || "any")}
                        </span>
                        {typeof schema.description === "string" && (
                          <span className="text-xs text-zinc-400">
                            — {schema.description}
                          </span>
                        )}
                      </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
