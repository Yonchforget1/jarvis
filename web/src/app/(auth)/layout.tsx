export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative flex min-h-screen items-center justify-center bg-background p-4 overflow-hidden">
      {/* Background effects */}
      <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-purple-500/5" />
      <div className="absolute top-1/4 -left-32 h-64 w-64 rounded-full bg-primary/5 blur-3xl" />
      <div className="absolute bottom-1/4 -right-32 h-64 w-64 rounded-full bg-purple-500/5 blur-3xl" />

      {/* Content */}
      <div className="relative z-10 w-full animate-fade-in-up">{children}</div>
    </div>
  );
}
