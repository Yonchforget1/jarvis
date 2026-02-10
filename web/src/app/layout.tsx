import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { ThemeProvider } from "@/components/theme-provider";
import { AuthProvider } from "@/lib/auth";
import { ToastProvider } from "@/components/ui/toast";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f8f8fc" },
    { media: "(prefers-color-scheme: dark)", color: "#1a1a2e" },
  ],
  width: "device-width",
  initialScale: 1,
};

export const metadata: Metadata = {
  title: {
    default: "JARVIS AI Agent Platform",
    template: "%s | JARVIS",
  },
  description:
    "The most advanced AI agent platform. Execute real tasks on real computers with 16+ professional tools. Deploy your AI workforce today.",
  keywords: [
    "AI agent",
    "automation",
    "artificial intelligence",
    "task automation",
    "AI platform",
    "code execution",
    "web scraping",
    "game development",
  ],
  authors: [{ name: "Yonatan Weintraub" }],
  creator: "JARVIS AI",
  openGraph: {
    type: "website",
    locale: "en_US",
    siteName: "JARVIS AI Agent Platform",
    title: "JARVIS - Deploy Your AI Workforce",
    description:
      "The most advanced AI agent platform. Execute real tasks with 16+ professional tools. From code to games to automation.",
  },
  twitter: {
    card: "summary_large_image",
    title: "JARVIS AI Agent Platform",
    description:
      "The most advanced AI agent platform. 16+ professional tools. Deploy your AI workforce today.",
  },
  robots: {
    index: true,
    follow: true,
  },
  manifest: "/manifest.json",
  icons: {
    icon: [
      { url: "/icon.svg", type: "image/svg+xml" },
      { url: "/icon-192x192.png", sizes: "192x192", type: "image/png" },
      { url: "/icon-512x512.png", sizes: "512x512", type: "image/png" },
    ],
    apple: "/apple-touch-icon.png",
  },
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "JARVIS",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href={process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"} />
        <link rel="dns-prefetch" href={process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"} />
      </head>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <ThemeProvider>
          <AuthProvider>
            <ToastProvider>{children}</ToastProvider>
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
