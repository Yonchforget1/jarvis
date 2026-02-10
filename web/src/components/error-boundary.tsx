"use client";

import React, { Component, type ReactNode, useState } from "react";
import { AlertTriangle, RotateCcw, Home, Copy, Check, ChevronDown, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";

function ErrorDetails({ error }: { error: Error }) {
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const errorInfo = `${error.name}: ${error.message}\n\n${error.stack || "No stack trace available"}`;

  const handleCopy = () => {
    navigator.clipboard.writeText(errorInfo);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="w-full">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1.5 text-xs text-muted-foreground/50 hover:text-muted-foreground transition-colors mx-auto"
      >
        {expanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
        Technical details
      </button>
      {expanded && (
        <div className="mt-3 rounded-xl border border-border/50 bg-muted/30 p-3 animate-fade-in-up">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground/60">
              Error Stack
            </span>
            <button
              onClick={handleCopy}
              className="flex items-center gap-1 text-[10px] text-muted-foreground/50 hover:text-muted-foreground transition-colors"
            >
              {copied ? (
                <>
                  <Check className="h-3 w-3 text-green-400" />
                  <span className="text-green-400">Copied</span>
                </>
              ) : (
                <>
                  <Copy className="h-3 w-3" />
                  Copy
                </>
              )}
            </button>
          </div>
          <pre className="text-[10px] font-mono text-muted-foreground/70 whitespace-pre-wrap break-all max-h-32 overflow-y-auto leading-relaxed">
            {error.stack || error.message}
          </pre>
        </div>
      )}
    </div>
  );
}

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error("[ErrorBoundary]", {
      error: error.message,
      stack: error.stack,
      componentStack: errorInfo.componentStack,
      url: typeof window !== "undefined" ? window.location.href : "unknown",
      timestamp: new Date().toISOString(),
    });
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  handleGoHome = () => {
    this.setState({ hasError: false, error: null });
    window.location.href = "/chat";
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;

      return (
        <div className="flex h-full items-center justify-center p-8">
          <div className="flex flex-col items-center gap-4 max-w-md text-center animate-fade-in-up">
            <div className="relative">
              <div className="absolute -inset-2 rounded-3xl bg-red-500/10 blur-xl" />
              <div className="relative flex h-16 w-16 items-center justify-center rounded-2xl bg-red-500/10 border border-red-500/20">
                <AlertTriangle className="h-8 w-8 text-red-400" />
              </div>
            </div>
            <div>
              <h2 className="text-xl font-semibold mb-1">Something went wrong</h2>
              <p className="text-sm text-muted-foreground/70 leading-relaxed">
                {this.state.error?.message || "An unexpected error occurred. Please try again."}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button onClick={this.handleReset} variant="outline" className="gap-2 rounded-xl">
                <RotateCcw className="h-4 w-4" />
                Try Again
              </Button>
              <Button onClick={this.handleGoHome} variant="ghost" className="gap-2 rounded-xl text-muted-foreground">
                <Home className="h-4 w-4" />
                Go to Chat
              </Button>
            </div>
            {this.state.error && <ErrorDetails error={this.state.error} />}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
