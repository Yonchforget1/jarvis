import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Learnings",
  description: "View insights and learnings JARVIS has gained from past tasks.",
};

export default function LearningsLayout({ children }: { children: React.ReactNode }) {
  return children;
}
