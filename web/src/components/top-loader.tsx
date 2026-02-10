"use client";

import { useEffect, useState, useRef } from "react";
import { usePathname } from "next/navigation";

export function TopLoader() {
  const pathname = usePathname();
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [visible, setVisible] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const prevPathRef = useRef(pathname);

  useEffect(() => {
    if (pathname !== prevPathRef.current) {
      // Route changed - show loader briefly
      prevPathRef.current = pathname;
      setLoading(true);
      setVisible(true);
      setProgress(0);

      // Animate to 90% quickly
      const step1 = setTimeout(() => setProgress(30), 50);
      const step2 = setTimeout(() => setProgress(60), 150);
      const step3 = setTimeout(() => setProgress(90), 300);

      // Complete
      const complete = setTimeout(() => {
        setProgress(100);
        // Hide after animation completes
        const hide = setTimeout(() => {
          setVisible(false);
          setLoading(false);
          setProgress(0);
        }, 300);
        timeoutRef.current = hide;
      }, 400);

      return () => {
        clearTimeout(step1);
        clearTimeout(step2);
        clearTimeout(step3);
        clearTimeout(complete);
        if (timeoutRef.current) clearTimeout(timeoutRef.current);
      };
    }
  }, [pathname]);

  if (!visible) return null;

  return (
    <div className="fixed top-0 left-0 right-0 z-[999] h-0.5">
      <div
        className={`h-full bg-primary shadow-[0_0_10px_rgba(108,58,237,0.5)] transition-all duration-300 ease-out ${
          !loading ? "opacity-0" : "opacity-100"
        }`}
        style={{ width: `${progress}%` }}
      />
    </div>
  );
}
