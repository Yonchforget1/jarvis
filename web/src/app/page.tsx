"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { AuthForm } from "@/components/AuthForm";

export default function Home() {
  const router = useRouter();
  const [showAuth, setShowAuth] = useState(false);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    if (api.isLoggedIn()) {
      router.push("/chat");
    } else {
      setShowAuth(true);
      setChecking(false);
    }
  }, [router]);

  if (checking && !showAuth) {
    return (
      <div className="h-screen bg-zinc-950 flex items-center justify-center">
        <div className="text-zinc-500 animate-pulse">Loading...</div>
      </div>
    );
  }

  return (
    <div className="h-screen bg-zinc-950">
      {showAuth && (
        <AuthForm
          onSuccess={() => {
            router.push("/chat");
          }}
        />
      )}
    </div>
  );
}
