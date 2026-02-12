"use client";

import { useState, useEffect } from "react";

interface WelcomeModalProps {
  onClose: () => void;
  onStartChat: (prompt: string) => void;
}

const FEATURES = [
  { icon: "\u{1F4AC}", title: "Multi-Model Chat", desc: "Switch between Claude, GPT-4o, and Gemini mid-conversation" },
  { icon: "\u{1F527}", title: "50+ Built-in Tools", desc: "File management, web search, shell commands, and more" },
  { icon: "\u{1F4C5}", title: "Scheduled Tasks", desc: "Automate recurring work with cron-based scheduling" },
  { icon: "\u{1F517}", title: "Share & Export", desc: "Share conversations via public links or export as Markdown" },
];

const STARTER_PROMPTS = [
  "What can you do? Show me your capabilities.",
  "Help me write a Python script to process CSV files.",
  "Analyze my project structure and suggest improvements.",
];

export function WelcomeModal({ onClose, onStartChat }: WelcomeModalProps) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    setTimeout(() => setVisible(true), 50);
  }, []);

  function dismiss() {
    setVisible(false);
    localStorage.setItem("jarvis_onboarded", "true");
    setTimeout(onClose, 200);
  }

  return (
    <div className={`fixed inset-0 z-50 flex items-center justify-center transition-opacity duration-200 ${visible ? "opacity-100" : "opacity-0"}`}>
      <div className="absolute inset-0 bg-black/60" onClick={dismiss} />
      <div className="relative bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl max-w-lg w-full mx-4 p-6 shadow-2xl">
        <h2 className="text-2xl font-bold mb-1">Welcome to Jarvis</h2>
        <p className="text-sm text-zinc-500 mb-5">Your AI agent platform. Here&apos;s what you can do:</p>

        <div className="grid grid-cols-2 gap-3 mb-6">
          {FEATURES.map((f) => (
            <div key={f.title} className="p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-200 dark:border-zinc-700">
              <div className="text-lg mb-1">{f.icon}</div>
              <div className="text-sm font-semibold">{f.title}</div>
              <div className="text-xs text-zinc-500 mt-0.5">{f.desc}</div>
            </div>
          ))}
        </div>

        <p className="text-xs text-zinc-500 mb-3">Quick start:</p>
        <div className="space-y-2 mb-5">
          {STARTER_PROMPTS.map((prompt) => (
            <button
              key={prompt}
              onClick={() => { dismiss(); onStartChat(prompt); }}
              className="block w-full text-left text-sm px-3 py-2 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 hover:border-blue-500 transition-colors"
            >
              {prompt}
            </button>
          ))}
        </div>

        <button
          onClick={dismiss}
          className="w-full py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors"
        >
          Get Started
        </button>
      </div>
    </div>
  );
}
