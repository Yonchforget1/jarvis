"use client";

import { useRef, useState, useEffect, useCallback, KeyboardEvent } from "react";
import { api } from "@/lib/api";

interface Attachment {
  file_id: string;
  filename: string;
  size: number;
}

interface SlashCommand {
  name: string;
  description: string;
  action: () => void;
}

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  slashCommands?: SlashCommand[];
}

export function ChatInput({ onSend, disabled, slashCommands = [] }: ChatInputProps) {
  const ref = useRef<HTMLTextAreaElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [uploading, setUploading] = useState(false);
  const [charCount, setCharCount] = useState(0);
  const [showCommands, setShowCommands] = useState(false);
  const [commandFilter, setCommandFilter] = useState("");
  const [selectedCommandIndex, setSelectedCommandIndex] = useState(0);
  const [listening, setListening] = useState(false);
  const [hasSpeechRecognition, setHasSpeechRecognition] = useState(false);
  const recognitionRef = useRef<SpeechRecognition | null>(null);

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      recognitionRef.current = null;
    }
    setListening(false);
  }, []);

  function startListening() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-US";

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let transcript = "";
      for (let i = 0; i < event.results.length; i++) {
        transcript += event.results[i][0].transcript;
      }
      if (ref.current) {
        ref.current.value = transcript;
        setCharCount(transcript.length);
        ref.current.style.height = "auto";
        ref.current.style.height = Math.min(ref.current.scrollHeight, 150) + "px";
      }
    };

    recognition.onerror = () => stopListening();
    recognition.onend = () => setListening(false);

    recognitionRef.current = recognition;
    recognition.start();
    setListening(true);
  }

  function toggleVoice() {
    if (listening) {
      stopListening();
    } else {
      startListening();
    }
  }

  useEffect(() => {
    setHasSpeechRecognition(
      !!(window.SpeechRecognition || window.webkitSpeechRecognition)
    );
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
    };
  }, []);

  const filteredCommands = commandFilter
    ? slashCommands.filter((c) => c.name.toLowerCase().startsWith(commandFilter.toLowerCase()))
    : slashCommands;

  function handleKey(e: KeyboardEvent) {
    if (showCommands && filteredCommands.length > 0) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedCommandIndex((i) => Math.min(i + 1, filteredCommands.length - 1));
        return;
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedCommandIndex((i) => Math.max(i - 1, 0));
        return;
      }
      if (e.key === "Tab" || (e.key === "Enter" && !e.shiftKey)) {
        e.preventDefault();
        executeCommand(filteredCommands[selectedCommandIndex]);
        return;
      }
      if (e.key === "Escape") {
        setShowCommands(false);
        return;
      }
    }

    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  function executeCommand(cmd: SlashCommand) {
    cmd.action();
    if (ref.current) ref.current.value = "";
    setShowCommands(false);
    setCommandFilter("");
    setCharCount(0);
  }

  function handleInput(e: React.FormEvent<HTMLTextAreaElement>) {
    const el = e.currentTarget;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 150) + "px";
    setCharCount(el.value.length);

    // Detect slash commands
    const val = el.value;
    if (val.startsWith("/") && !val.includes(" ") && slashCommands.length > 0) {
      setCommandFilter(val.slice(1));
      setShowCommands(true);
      setSelectedCommandIndex(0);
    } else {
      setShowCommands(false);
    }
  }

  async function submit() {
    const text = ref.current?.value.trim();
    if ((!text && attachments.length === 0) || disabled) return;

    // Check for slash commands
    if (text && text.startsWith("/") && !text.includes(" ")) {
      const cmd = slashCommands.find(
        (c) => c.name.toLowerCase() === text.slice(1).toLowerCase()
      );
      if (cmd) {
        executeCommand(cmd);
        return;
      }
    }

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
    setShowCommands(false);
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
    <div className="bg-zinc-50 dark:bg-zinc-900 border-t border-zinc-200 dark:border-zinc-800 relative">
      {/* Slash command autocomplete */}
      {showCommands && filteredCommands.length > 0 && (
        <div className="absolute bottom-full left-3 right-3 mb-1 bg-white dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 rounded-lg shadow-lg overflow-hidden">
          {filteredCommands.map((cmd, i) => (
            <button
              key={cmd.name}
              onClick={() => executeCommand(cmd)}
              className={`w-full flex items-center gap-3 px-3 py-2 text-left text-sm transition-colors ${
                i === selectedCommandIndex
                  ? "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300"
                  : "text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-700"
              }`}
            >
              <span className="font-mono text-xs text-zinc-500">/{cmd.name}</span>
              <span className="text-xs text-zinc-400">{cmd.description}</span>
            </button>
          ))}
        </div>
      )}

      {/* Attachments preview */}
      {attachments.length > 0 && (
        <div className="flex gap-2 px-3 pt-2 flex-wrap">
          {attachments.map((att) => (
            <div
              key={att.file_id}
              className="flex items-center gap-1.5 bg-zinc-200 dark:bg-zinc-800 rounded-lg px-2.5 py-1 text-xs"
            >
              <span className="text-zinc-700 dark:text-zinc-300 max-w-[150px] truncate">{att.filename}</span>
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
        {hasSpeechRecognition && (
          <button
            onClick={toggleVoice}
            disabled={disabled}
            className={`px-3 text-sm rounded-lg transition-colors border ${
              listening
                ? "bg-red-100 dark:bg-red-900/30 border-red-400 text-red-500 animate-pulse"
                : "bg-zinc-200 dark:bg-zinc-800 hover:bg-zinc-300 dark:hover:bg-zinc-700 border-zinc-300 dark:border-zinc-700 text-zinc-500 dark:text-zinc-400"
            } disabled:opacity-50`}
            title={listening ? "Stop listening" : "Voice input"}
          >
            {listening ? "\u23F9" : "\u{1F3A4}"}
          </button>
        )}
        <textarea
          ref={ref}
          placeholder="Message Jarvis... (type / for commands)"
          rows={1}
          disabled={disabled}
          onKeyDown={handleKey}
          className="flex-1 bg-white dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 rounded-lg px-4 py-2.5 text-sm text-zinc-900 dark:text-zinc-100 placeholder-zinc-400 dark:placeholder-zinc-500 resize-none outline-none focus:border-blue-500 disabled:opacity-50"
          onInput={handleInput}
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
      {charCount > 0 && !showCommands && (
        <div className="px-3 pb-1 text-right">
          <span className={`text-xs ${charCount > 9000 ? "text-orange-400" : "text-zinc-500"}`}>
            {charCount.toLocaleString()}/10,000
          </span>
        </div>
      )}
    </div>
  );
}
