export function Footer() {
  return (
    <footer className="border-t border-white/5 px-4 py-12">
      <div className="mx-auto max-w-6xl">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded-md bg-primary/20">
              <span className="text-xs font-bold text-primary">J</span>
            </div>
            <span className="text-sm font-semibold">JARVIS AI Agent Platform</span>
          </div>
          <p className="text-xs text-muted-foreground">
            &copy; {new Date().getFullYear()} Jarvis AI. Built by Yonatan Weintraub.
          </p>
        </div>
      </div>
    </footer>
  );
}
