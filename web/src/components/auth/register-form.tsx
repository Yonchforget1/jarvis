"use client";

import { useState, useMemo, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Loader2, ArrowRight, CheckCircle2, Eye, EyeOff, AlertCircle } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

function PasswordStrength({ password }: { password: string }) {
  const strength = useMemo(() => {
    if (!password) return 0;
    let score = 0;
    if (password.length >= 8) score++;
    if (password.length >= 12) score++;
    if (/[A-Z]/.test(password) && /[a-z]/.test(password)) score++;
    if (/[0-9]/.test(password)) score++;
    if (/[^A-Za-z0-9]/.test(password)) score++;
    return Math.min(score, 4);
  }, [password]);

  if (!password) return null;

  const colors = ["bg-red-500", "bg-orange-500", "bg-yellow-500", "bg-green-500"];
  const labels = ["Weak", "Fair", "Good", "Strong"];

  return (
    <div className="space-y-1.5">
      <div className="flex gap-1">
        {[0, 1, 2, 3].map((i) => (
          <div
            key={i}
            className={`h-1 flex-1 rounded-full transition-all duration-300 ${
              i < strength ? colors[strength - 1] : "bg-muted"
            }`}
          />
        ))}
      </div>
      <p className={`text-[10px] ${strength >= 3 ? "text-green-400" : "text-muted-foreground/50"}`}>
        {labels[strength - 1] || "Too short"}
      </p>
    </div>
  );
}

export function RegisterForm() {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const { register, isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();

  // Redirect to chat if already authenticated
  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      router.replace("/chat");
    }
  }, [authLoading, isAuthenticated, router]);

  const passwordsMatch = password && confirmPassword && password === confirmPassword;
  const emailRegex = /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$/;
  const emailValid = !email || emailRegex.test(email);
  const emailTouched = email.length > 0;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (loading) return;
    setError("");
    if (username.length < 3) {
      setError("Username must be at least 3 characters");
      return;
    }
    if (!/^[a-zA-Z0-9_-]+$/.test(username)) {
      setError("Username can only contain letters, numbers, underscores, and hyphens");
      return;
    }
    if (email && !/^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$/.test(email)) {
      setError("Please enter a valid email address");
      return;
    }
    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }
    if (/^\d+$/.test(password) || /^[a-zA-Z]+$/.test(password)) {
      setError("Password must contain both letters and numbers");
      return;
    }
    setLoading(true);
    try {
      await register(username, password, email);
      router.push("/chat");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Registration failed");
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
        </div>
        <CardTitle className="text-2xl font-bold">Create account</CardTitle>
        <CardDescription className="text-muted-foreground/60">
          Get started with JARVIS AI Agent
        </CardDescription>
      </CardHeader>
      <CardContent className="pt-2">
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div role="alert" id="register-error" className="rounded-xl bg-red-500/10 border border-red-500/20 p-3 text-sm text-red-400 animate-scale-in">
              {error}
            </div>
          )}
          <div className="space-y-2">
            <Label htmlFor="username" className="text-xs">Username</Label>
            <Input
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value.replace(/[^a-zA-Z0-9_-]/g, ""))}
              placeholder="Choose a username"
              required
              minLength={3}
              maxLength={32}
              pattern="[a-zA-Z0-9_-]+"
              title="Letters, numbers, underscores, and hyphens only"
              autoFocus
              autoComplete="username"
              enterKeyHint="next"
              aria-describedby={error ? "register-error" : undefined}
              aria-invalid={!!error && error.toLowerCase().includes("username")}
              className={`h-11 rounded-xl bg-secondary/50 border-border/50 focus:border-primary/40 ${error && error.toLowerCase().includes("username") ? "border-red-500/50" : ""}`}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="email" className="text-xs">Email <span className="text-muted-foreground/40">(optional)</span></Label>
            <div className="relative">
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                autoComplete="email"
                aria-invalid={emailTouched && !emailValid}
                aria-describedby={emailTouched && !emailValid ? "email-error" : undefined}
                className={`h-11 rounded-xl bg-secondary/50 border-border/50 focus:border-primary/40 pr-10 ${emailTouched && !emailValid ? "border-red-500/50" : ""}`}
              />
              {emailTouched && !emailValid && (
                <AlertCircle className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-red-400" />
              )}
              {emailTouched && emailValid && (
                <CheckCircle2 className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-green-500 animate-scale-in" />
              )}
            </div>
            {emailTouched && !emailValid && (
              <p id="email-error" className="text-[10px] text-red-400">Please enter a valid email address</p>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="password" className="text-xs">Password</Label>
            <div className="relative">
              <Input
                id="password"
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Create a password"
                required
                autoComplete="new-password"
                enterKeyHint="next"
                aria-describedby={error ? "register-error" : undefined}
              className="h-11 rounded-xl bg-secondary/50 border-border/50 focus:border-primary/40 pr-10"
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
            <PasswordStrength password={password} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="confirmPassword" className="text-xs">Confirm Password</Label>
            <div className="relative">
              <Input
                id="confirmPassword"
                type={showPassword ? "text" : "password"}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Confirm your password"
                required
                autoComplete="new-password"
                enterKeyHint="go"
                className={`h-11 rounded-xl bg-secondary/50 border-border/50 focus:border-primary/40 pr-10 ${
                  confirmPassword && !passwordsMatch ? "border-red-500/50" : ""
                }`}
              />
              {passwordsMatch && (
                <CheckCircle2 className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-green-500 animate-scale-in" />
              )}
            </div>
          </div>
          <Button
            type="submit"
            className="w-full h-11 rounded-xl gap-2 text-sm font-medium"
            disabled={loading}
          >
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Creating account...
              </>
            ) : (
              <>
                Create Account
                <ArrowRight className="h-4 w-4" />
              </>
            )}
          </Button>
          <p className="text-center text-sm text-muted-foreground/60 pt-2">
            Already have an account?{" "}
            <Link href="/login" className="text-primary hover:text-primary/80 transition-colors font-medium">
              Sign in
            </Link>
          </p>
        </form>
      </CardContent>
    </Card>
  );
}
