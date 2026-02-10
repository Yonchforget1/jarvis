import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Dashboard",
  description: "Real-time system overview and performance metrics for JARVIS AI.",
};

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return children;
}
