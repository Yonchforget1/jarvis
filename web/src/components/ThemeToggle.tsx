"use client";

import { useEffect, useState } from "react";

export function ThemeToggle() {
  const [dark, setDark] = useState(true);

  useEffect(() => {
    const saved = localStorage.getItem("jarvis_theme");
    if (saved === "light") {
      setDark(false);
      document.documentElement.classList.remove("dark");
    }
  }, []);

  function toggle() {
    const next = !dark;
    setDark(next);
    if (next) {
      document.documentElement.classList.add("dark");
      localStorage.setItem("jarvis_theme", "dark");
    } else {
      document.documentElement.classList.remove("dark");
      localStorage.setItem("jarvis_theme", "light");
    }
  }

  return (
    <button
      onClick={toggle}
      className="w-8 h-8 flex items-center justify-center rounded-lg text-sm transition-colors hover:bg-zinc-700 dark:hover:bg-zinc-700 hover:bg-zinc-200"
      title={dark ? "Switch to light mode" : "Switch to dark mode"}
      aria-label="Toggle theme"
    >
      {dark ? "\u2600" : "\u263E"}
    </button>
  );
}
