import type { Metadata } from "next";
import { LoginForm } from "@/components/auth/login-form";

export const metadata: Metadata = {
  title: "Sign In | JARVIS",
  description: "Sign in to JARVIS AI Agent Platform to access your AI workforce.",
};

export default function LoginPage() {
  return <LoginForm />;
}
