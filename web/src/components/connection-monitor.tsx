"use client";

import { useEffect, useRef } from "react";
import { useConnection } from "@/hooks/use-connection";
import { useToast } from "@/components/ui/toast";

export function ConnectionMonitor() {
  const { status } = useConnection();
  const toast = useToast();
  const prevStatusRef = useRef(status);
  const hasInitializedRef = useRef(false);

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

    if (status === "disconnected" && prevStatus === "connected") {
      toast.warning("Connection lost", "Unable to reach the JARVIS API server.");
    } else if (status === "connected" && prevStatus === "disconnected") {
      toast.success("Reconnected", "Connection to the API server restored.");
    }
  }, [status, toast]);

  return null;
}
