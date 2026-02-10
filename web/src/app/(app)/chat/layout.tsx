import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Chat",
  description: "Chat with JARVIS AI agent - execute tasks, write code, and build projects.",
};

export default function ChatLayout({ children }: { children: React.ReactNode }) {
  return children;
}
