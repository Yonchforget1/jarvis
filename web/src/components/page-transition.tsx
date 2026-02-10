"use client";

import { usePathname } from "next/navigation";
import { useEffect, useState, useRef } from "react";

export function PageTransition({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [isTransitioning, setIsTransitioning] = useState(false);
  const prevPathRef = useRef(pathname);

  useEffect(() => {
    if (pathname !== prevPathRef.current) {
      setIsTransitioning(true);
      prevPathRef.current = pathname;
      // Reset after animation completes
      const timer = setTimeout(() => setIsTransitioning(false), 200);
      return () => clearTimeout(timer);
    }
  }, [pathname]);

  return (
    <div
      className={`h-full transition-all duration-200 ease-out ${
        isTransitioning ? "opacity-0 translate-y-1" : "opacity-100 translate-y-0"
      }`}
    >
      {children}
    </div>
  );
}
