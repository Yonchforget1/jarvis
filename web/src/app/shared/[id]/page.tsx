"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { ChatMessage } from "@/components/ChatMessage";

interface SharedMessage {
  role: string;
  content: string;
}

interface SharedData {
  title: string;
  username: string;
  messages: SharedMessage[];
  created_at: string;
  view_count: number;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:3000";

export default function SharedPage() {
  const params = useParams();
  const shareId = params.id as string;
  const [data, setData] = useState<SharedData | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    loadShared();
  }, [shareId]);

  async function loadShared() {
    try {
      const res = await fetch(`${API_BASE}/api/shared/${shareId}`);
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Not found" }));
        setError(err.detail || "Share not found");
        return;
      }
      const shared = await res.json();
      setData(shared);
    } catch {
      setError("Failed to load shared conversation");
    }
  }

  if (error) {
    return (
      <div className="min-h-screen bg-zinc-950 text-white flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold mb-3">Share Not Found</h1>
          <p className="text-zinc-400">{error}</p>
          <a href="/" className="mt-4 inline-block text-blue-400 hover:underline">
            Go to Jarvis
          </a>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen bg-zinc-950 text-white flex items-center justify-center">
        <div className="text-zinc-500 animate-pulse">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-white">
      <div className="max-w-3xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-2 text-sm text-zinc-500 mb-2">
            <span>Shared by {data.username}</span>
            <span>-</span>
            <span>{new Date(data.created_at).toLocaleDateString()}</span>
            <span>-</span>
            <span>{data.view_count} views</span>
          </div>
          <h1 className="text-2xl font-bold">{data.title}</h1>
        </div>

        {/* Messages */}
        <div className="space-y-3">
          {data.messages.map((msg, i) => (
            <ChatMessage
              key={i}
              role={msg.role as "user" | "assistant" | "system"}
              content={msg.content}
            />
          ))}
        </div>

        {/* Footer */}
        <div className="mt-12 pt-6 border-t border-zinc-800 text-center">
          <p className="text-zinc-500 text-sm">
            Powered by{" "}
            <a href="/" className="text-blue-400 hover:underline">
              Jarvis AI
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
