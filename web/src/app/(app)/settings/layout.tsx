import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Settings",
  description: "Configure JARVIS AI backend, model, appearance, and export your data.",
};

export default function SettingsLayout({ children }: { children: React.ReactNode }) {
  return children;
}
