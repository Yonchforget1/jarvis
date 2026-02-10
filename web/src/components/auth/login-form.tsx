"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Loader2, ArrowRight } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function LoginForm() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(username, password);
      router.push("/chat");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed");
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
            <div className="rounded-xl bg-red-500/10 border border-red-500/20 p-3 text-sm text-red-400 animate-scale-in">
              {error}
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
              autoFocus
              className="h-11 rounded-xl bg-secondary/50 border-border/50 focus:border-primary/40"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password" className="text-xs">Password</Label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
              required
              className="h-11 rounded-xl bg-secondary/50 border-border/50 focus:border-primary/40"
            />
          </div>
          <Button
            type="submit"
            className="w-full h-11 rounded-xl gap-2 text-sm font-medium"
            disabled={loading}
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
