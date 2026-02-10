"use client";

import { useState, useRef, useCallback, type ReactNode } from "react";

interface TooltipProps {
  content: string;
  children: ReactNode;
  side?: "right" | "left" | "top" | "bottom";
  delay?: number;
}

export function Tooltip({ content, children, side = "right", delay = 200 }: TooltipProps) {
  const [visible, setVisible] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const show = useCallback(() => {
    timeoutRef.current = setTimeout(() => setVisible(true), delay);
  }, [delay]);

  const hide = useCallback(() => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    setVisible(false);
  }, []);

  const positionClasses: Record<string, string> = {
    right: "left-full top-1/2 -translate-y-1/2 ml-2",
    left: "right-full top-1/2 -translate-y-1/2 mr-2",
    top: "bottom-full left-1/2 -translate-x-1/2 mb-2",
    bottom: "top-full left-1/2 -translate-x-1/2 mt-2",
  };

  return (
    <div className="relative" onMouseEnter={show} onMouseLeave={hide} onFocus={show} onBlur={hide}>
      {children}
      {visible && (
        <div
          role="tooltip"
          className={`absolute z-50 whitespace-nowrap rounded-lg bg-popover border border-border/50 px-2.5 py-1.5 text-xs text-popover-foreground shadow-lg animate-fade-in pointer-events-none ${positionClasses[side]}`}
        >
          {content}
        </div>
      )}
    </div>
  );
}
