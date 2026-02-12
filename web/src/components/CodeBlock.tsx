"use client";

import { useState } from "react";

interface CodeBlockProps {
  language?: string;
  children: string;
}

export function CodeBlock({ language, children }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  function handleCopy() {
    navigator.clipboard.writeText(children);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <div className="relative group/code">
      <div className="flex items-center justify-between bg-zinc-300 dark:bg-zinc-800 rounded-t-lg px-3 py-1 border border-b-0 border-zinc-300 dark:border-zinc-700">
        <span className="text-[10px] font-mono text-zinc-500 dark:text-zinc-400 uppercase">
          {language || "code"}
        </span>
        <button
          onClick={handleCopy}
          className="text-[10px] text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white transition-colors px-1.5 py-0.5 rounded hover:bg-zinc-200 dark:hover:bg-zinc-700"
        >
          {copied ? "Copied!" : "Copy"}
        </button>
      </div>
      <pre className="!mt-0 !rounded-t-none">
        <code className={language ? `language-${language}` : ""}>{children}</code>
      </pre>
    </div>
  );
}
