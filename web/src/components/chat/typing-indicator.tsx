export function TypingIndicator() {
  return (
    <div className="flex items-center gap-2 px-4 py-3">
      <div className="flex items-center gap-1.5 rounded-2xl rounded-bl-md bg-secondary px-4 py-3">
        <span className="text-sm text-muted-foreground">Jarvis is thinking</span>
        <div className="flex gap-1">
          <div className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse-dot" />
          <div
            className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse-dot"
            style={{ animationDelay: "0.2s" }}
          />
          <div
            className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse-dot"
            style={{ animationDelay: "0.4s" }}
          />
        </div>
      </div>
    </div>
  );
}
