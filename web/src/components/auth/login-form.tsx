"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Loader2, ArrowRight, Eye, EyeOff, ShieldAlert } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function LoginForm() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isRateLimited, setIsRateLimited] = useState(false);
  const [rateLimitSeconds, setRateLimitSeconds] = useState(0);
  const rateLimitTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const { login, isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();

  // Redirect to chat if already authenticated
  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      router.replace("/chat");
    }
  }, [authLoading, isAuthenticated, router]);

  // Cleanup rate limit timer on unmount
  useEffect(() => {
    return () => {
      if (rateLimitTimerRef.current) clearInterval(rateLimitTimerRef.current);
    };
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (loading) return;
    setError("");
    setLoading(true);
    try {
      await login(username, password);
      router.push("/chat");
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Login failed";
      // Detect rate limiting (429 Too Many Requests)
      const isRateLimit = message.toLowerCase().includes("rate") || message.toLowerCase().includes("too many");
      if (isRateLimit) {
        setIsRateLimited(true);
        setRateLimitSeconds(60);
        setError("Too many login attempts. Please wait before trying again.");
        // Start countdown timer
        if (rateLimitTimerRef.current) clearInterval(rateLimitTimerRef.current);
        rateLimitTimerRef.current = setInterval(() => {
          setRateLimitSeconds((prev) => {
            if (prev <= 1) {
              if (rateLimitTimerRef.current) clearInterval(rateLimitTimerRef.current);
              setIsRateLimited(false);
              setError("");
              return 0;
            }
            return prev - 1;
          });
        }, 1000);
      } else {
        setError(message);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="w-full max-w-md mx-auto border-border/50 bg-card/50 backdrop-blur-xl shadow-2xl">
      <CardHeader className="text-center pb-2">
        <div className="mx-auto mb-4 relative">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/20 border border-primary/10">
            <span className="text-2xl font-bold text-primary">J</span>
          </div>
          <div className="absolute -bottom-1 -right-1 h-5 w-5 rounded-full bg-green-500/20 border border-green-500/30 flex items-center justify-center">
            <div className="h-2 w-2 rounded-full bg-green-500" />
          </div>
        </div>
        <CardTitle className="text-2xl font-bold">Welcome back</CardTitle>
        <CardDescription className="text-muted-foreground/60">
          Sign in to your JARVIS account
        </CardDescription>
      </CardHeader>
      <CardContent className="pt-2">
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div role="alert" id="login-error" className="rounded-xl bg-red-500/10 border border-red-500/20 p-3 text-sm text-red-400 animate-scale-in">
              {isRateLimited && (
                <div className="flex items-center gap-2">
                  <ShieldAlert className="h-4 w-4 shrink-0" />
                  <div>
                    <p>{error}</p>
                    {rateLimitSeconds > 0 && (
                      <p className="text-xs text-red-400/70 mt-1">
                        Try again in {rateLimitSeconds}s
                      </p>
                    )}
                  </div>
                </div>
              )}
              {!isRateLimited && error}
            </div>
          )}
          <div className="space-y-2">
            <Label htmlFor="username" className="text-xs">Username</Label>
            <Input
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter your username"
              required
              minLength={3}
              autoFocus
              autoComplete="username"
              enterKeyHint="next"
              aria-describedby={error ? "login-error" : undefined}
              aria-invalid={!!error}
              className={`h-11 rounded-xl bg-secondary/50 border-border/50 focus:border-primary/40 ${error ? "border-red-500/50" : ""}`}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password" className="text-xs">Password</Label>
            <div className="relative">
              <Input
                id="password"
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your password"
                required
                minLength={8}
                autoComplete="current-password"
                enterKeyHint="go"
                aria-describedby={error ? "login-error" : undefined}
                aria-invalid={!!error}
                className={`h-11 rounded-xl bg-secondary/50 border-border/50 focus:border-primary/40 pr-10 ${error ? "border-red-500/50" : ""}`}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground/50 hover:text-foreground transition-colors"
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>
          <Button
            type="submit"
            className="w-full h-11 rounded-xl gap-2 text-sm font-medium"
            disabled={loading || isRateLimited}
          >
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Signing in...
              </>
            ) : (
              <>
                Sign In
                <ArrowRight className="h-4 w-4" />
              </>
            )}
          </Button>
          <p className="text-center text-sm text-muted-foreground/60 pt-2">
            Don&apos;t have an account?{" "}
            <Link href="/register" className="text-primary hover:text-primary/80 transition-colors font-medium">
              Create one
            </Link>
          </p>
        </form>
      </CardContent>
    </Card>
  );
}
