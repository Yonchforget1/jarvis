"use client";

import { useEffect, useRef, useState } from "react";
import { useConnection } from "@/hooks/use-connection";
import { useToast } from "@/components/ui/toast";

const STATUS_LABELS: Record<string, string> = {
  connected: "Connected to server",
  degraded: "Connection is slow",
  disconnected: "Disconnected from server",
  checking: "Checking connection",
};

export function ConnectionMonitor() {
  const { status } = useConnection();
  const toast = useToast();
  const prevStatusRef = useRef(status);
  const hasInitializedRef = useRef(false);
  const [announcement, setAnnouncement] = useState("");

  useEffect(() => {
    // Skip the very first status change from "checking"
    if (!hasInitializedRef.current) {
      if (status !== "checking") {
        hasInitializedRef.current = true;
        prevStatusRef.current = status;
      }
      return;
    }

    const prevStatus = prevStatusRef.current;
    prevStatusRef.current = status;

    if (prevStatus === status) return;

    // Announce to screen readers
    setAnnouncement(STATUS_LABELS[status] || "");

    if (status === "disconnected" && prevStatus === "connected") {
      toast.warning("Connection lost", "Unable to reach the JARVIS API server.");
    } else if (status === "connected" && prevStatus === "disconnected") {
      toast.success("Reconnected", "Connection to the API server restored.");
    }
  }, [status, toast]);

  // Invisible announcer for screen readers
  return (
    <div className="sr-only" role="status" aria-live="assertive" aria-atomic="true">
      {announcement}
    </div>
  );
}
