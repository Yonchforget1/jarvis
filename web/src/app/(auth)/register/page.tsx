import type { Metadata } from "next";
import { RegisterForm } from "@/components/auth/register-form";

export const metadata: Metadata = {
  title: "Create Account | JARVIS",
  description: "Create your JARVIS account and deploy your AI workforce today.",
};

export default function RegisterPage() {
  return <RegisterForm />;
}
