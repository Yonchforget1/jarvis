"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface Template {
  id: string;
  name: string;
  description: string;
  category: string;
  prompt: string;
  custom: boolean;
}

interface TemplateGridProps {
  onSelect: (prompt: string) => void;
}

const ICON_MAP: Record<string, string> = {
  code: "\u2318",
  bug: "\u26A0",
  test: "\u2713",
  book: "\u25B6",
  chart: "\u2191",
  mail: "\u2709",
  api: "\u21C4",
  server: "\u2601",
  pen: "\u270E",
  database: "\u25C9",
  terminal: ">_",
  custom: "\u2605",
};

export function TemplateGrid({ onSelect }: TemplateGridProps) {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  useEffect(() => {
    loadTemplates();
  }, []);

  async function loadTemplates() {
    try {
      const data = await api.getTemplates();
      setTemplates(data);
    } catch {
      // silently fail - templates are optional
    }
  }

  if (templates.length === 0) return null;

  const categories = [...new Set(templates.map((t) => t.category))];
  const filtered = selectedCategory
    ? templates.filter((t) => t.category === selectedCategory)
    : templates.slice(0, 8); // Show first 8 on "all"

  return (
    <div className="w-full max-w-2xl mx-auto">
      <p className="text-sm text-zinc-500 mb-3">Start with a template:</p>

      {/* Category pills */}
      <div className="flex gap-2 mb-3 flex-wrap">
        <button
          onClick={() => setSelectedCategory(null)}
          className={`px-2.5 py-1 rounded-full text-xs transition ${
            !selectedCategory
              ? "bg-zinc-700 text-zinc-200"
              : "bg-zinc-800/50 text-zinc-500 hover:text-zinc-300"
          }`}
        >
          Popular
        </button>
        {categories.map((cat) => (
          <button
            key={cat}
            onClick={() => setSelectedCategory(cat === selectedCategory ? null : cat)}
            className={`px-2.5 py-1 rounded-full text-xs transition ${
              selectedCategory === cat
                ? "bg-zinc-700 text-zinc-200"
                : "bg-zinc-800/50 text-zinc-500 hover:text-zinc-300"
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Template cards */}
      <div className="grid grid-cols-2 gap-2">
        {filtered.map((t) => (
          <button
            key={t.id}
            onClick={() => onSelect(t.prompt)}
            className="text-left bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 hover:border-zinc-700 rounded-lg p-3 transition group"
          >
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs text-zinc-500 font-mono">
                {ICON_MAP[t.id?.includes("custom") ? "custom" : t.id?.split("-")[0]] || "\u25CF"}
              </span>
              <span className="text-sm font-medium text-zinc-300 group-hover:text-white truncate">
                {t.name}
              </span>
            </div>
            <p className="text-xs text-zinc-500 line-clamp-2">{t.description}</p>
          </button>
        ))}
      </div>
    </div>
  );
}
