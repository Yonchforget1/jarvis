"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronRight, Home } from "lucide-react";
import { useSessionContext } from "@/lib/session-context";

const PAGE_LABELS: Record<string, string> = {
  chat: "Chat",
  dashboard: "Dashboard",
  tools: "Tools",
  learnings: "Learnings",
  settings: "Settings",
};

export function Breadcrumb() {
  const pathname = usePathname();
  const { selectedSessionName } = useSessionContext();

  const segments = pathname.split("/").filter(Boolean);
  if (segments.length === 0) return null;

  const crumbs: { label: string; href: string }[] = [];
  let path = "";
  for (const seg of segments) {
    path += `/${seg}`;
    const label = PAGE_LABELS[seg] || seg;
    crumbs.push({ label, href: path });
  }

  // Append session name if on chat page with active session
  if (segments[0] === "chat" && selectedSessionName) {
    crumbs.push({ label: selectedSessionName, href: pathname });
  }

  // Only show on tablet+ (hidden on mobile where space is tight)
  return (
    <nav aria-label="Breadcrumb" className="hidden md:flex items-center gap-1 px-4 py-1.5 text-[10px] text-muted-foreground/50 border-b border-border/20">
      <Link href="/dashboard" className="hover:text-foreground transition-colors" aria-label="Home">
        <Home className="h-3 w-3" />
      </Link>
      {crumbs.map((crumb, i) => (
        <span key={crumb.href} className="flex items-center gap-1">
          <ChevronRight className="h-2.5 w-2.5 text-muted-foreground/30" />
          {i === crumbs.length - 1 ? (
            <span className="text-foreground/70 font-medium truncate max-w-[150px]">{crumb.label}</span>
          ) : (
            <Link href={crumb.href} className="hover:text-foreground transition-colors truncate max-w-[100px]">
              {crumb.label}
            </Link>
          )}
        </span>
      ))}
    </nav>
  );
}
