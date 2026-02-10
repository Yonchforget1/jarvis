import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Tools",
  description: "Browse JARVIS professional tools - filesystem, execution, web, game dev, and more.",
};

export default function ToolsLayout({ children }: { children: React.ReactNode }) {
  return children;
}
