"use client";

import { useRef, useState, KeyboardEvent } from "react";
import { api } from "@/lib/api";

interface Attachment {
  file_id: string;
  filename: string;
  size: number;
}

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const ref = useRef<HTMLTextAreaElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [uploading, setUploading] = useState(false);
  const [charCount, setCharCount] = useState(0);

  function handleKey(e: KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  async function submit() {
    const text = ref.current?.value.trim();
    if ((!text && attachments.length === 0) || disabled) return;

    // Build message with file context
    let message = text || "";
    if (attachments.length > 0) {
      const fileContexts: string[] = [];
      for (const att of attachments) {
        try {
          const data = await api.getFileContent(att.file_id);
          fileContexts.push(
            `[Attached file: ${att.filename}]\n\`\`\`\n${data.content}\n\`\`\``
          );
        } catch {
          fileContexts.push(`[Attached file: ${att.filename} (could not read)]`);
        }
      }
      message = fileContexts.join("\n\n") + (text ? `\n\n${text}` : "");
    }

    onSend(message);
    if (ref.current) ref.current.value = "";
    setAttachments([]);
    setCharCount(0);
  }

  async function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setUploading(true);
    try {
      for (const file of Array.from(files)) {
        const result = await api.uploadFile(file);
        setAttachments((prev) => [...prev, result]);
      }
    } catch (err: unknown) {
      // Could show error but keep it simple
      console.error("Upload failed:", err);
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  function removeAttachment(fileId: string) {
    setAttachments((prev) => prev.filter((a) => a.file_id !== fileId));
  }

  function formatSize(bytes: number): string {
    if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)}MB`;
    if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)}KB`;
    return `${bytes}B`;
  }

  return (
    <div className="bg-zinc-50 dark:bg-zinc-900 border-t border-zinc-200 dark:border-zinc-800">
      {/* Attachments preview */}
      {attachments.length > 0 && (
        <div className="flex gap-2 px-3 pt-2 flex-wrap">
          {attachments.map((att) => (
            <div
              key={att.file_id}
              className="flex items-center gap-1.5 bg-zinc-800 rounded-lg px-2.5 py-1 text-xs"
            >
              <span className="text-zinc-300 max-w-[150px] truncate">{att.filename}</span>
              <span className="text-zinc-500">{formatSize(att.size)}</span>
              <button
                onClick={() => removeAttachment(att.file_id)}
                className="text-zinc-500 hover:text-red-400 ml-1"
              >
                x
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="flex gap-2 p-3">
        <input
          ref={fileRef}
          type="file"
          multiple
          onChange={handleFileSelect}
          className="hidden"
        />
        <button
          onClick={() => fileRef.current?.click()}
          disabled={disabled || uploading}
          className="px-3 bg-zinc-200 dark:bg-zinc-800 hover:bg-zinc-300 dark:hover:bg-zinc-700 disabled:opacity-50 text-zinc-500 dark:text-zinc-400 text-sm rounded-lg transition-colors border border-zinc-300 dark:border-zinc-700"
          title="Attach file"
        >
          {uploading ? "..." : "+"}
        </button>
        <textarea
          ref={ref}
          placeholder="Message Jarvis..."
          rows={1}
          disabled={disabled}
          onKeyDown={handleKey}
          className="flex-1 bg-white dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 rounded-lg px-4 py-2.5 text-sm text-zinc-900 dark:text-zinc-100 placeholder-zinc-400 dark:placeholder-zinc-500 resize-none outline-none focus:border-blue-500 disabled:opacity-50"
          onInput={(e) => {
            const el = e.currentTarget;
            el.style.height = "auto";
            el.style.height = Math.min(el.scrollHeight, 150) + "px";
            setCharCount(el.value.length);
          }}
          maxLength={10000}
        />
        <button
          onClick={submit}
          disabled={disabled}
          className="px-5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-colors"
        >
          Send
        </button>
      </div>
      {charCount > 0 && (
        <div className="px-3 pb-1 text-right">
          <span className={`text-xs ${charCount > 9000 ? "text-orange-400" : "text-zinc-500"}`}>
            {charCount.toLocaleString()}/10,000
          </span>
        </div>
      )}
    </div>
  );
}
