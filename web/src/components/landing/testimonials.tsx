const TESTIMONIALS = [
  {
    quote:
      "Jarvis automated our entire deployment pipeline in one conversation. What used to take my team a full day now happens in 5 minutes.",
    name: "Marcus Chen",
    title: "CTO, TechForge",
    initial: "M",
  },
  {
    quote:
      "I built a complete multiplayer game prototype in an afternoon. The game dev tools are incredible - it scaffolded the project, generated assets, and even wrote the game logic.",
    name: "Sarah Kim",
    title: "Indie Game Developer",
    initial: "S",
  },
  {
    quote:
      "The self-improvement system is what sets Jarvis apart. It remembers what worked and what didn't. It genuinely gets better over time.",
    name: "David Park",
    title: "AI Researcher",
    initial: "D",
  },
];

export function Testimonials() {
  return (
    <section className="px-4 py-24 bg-gradient-to-b from-transparent via-primary/[0.02] to-transparent">
      <div className="mx-auto max-w-6xl">
        <div className="text-center mb-16">
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight mb-4">
            Trusted by Builders
          </h2>
          <p className="text-muted-foreground">
            Professionals who demand results, not promises.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {TESTIMONIALS.map((t) => (
            <div
              key={t.name}
              className="rounded-2xl border border-white/5 bg-white/[0.02] p-6"
            >
              <p className="text-sm text-muted-foreground leading-relaxed mb-6">
                &ldquo;{t.quote}&rdquo;
              </p>
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 text-sm font-medium text-primary">
                  {t.initial}
                </div>
                <div>
                  <p className="text-sm font-medium">{t.name}</p>
                  <p className="text-xs text-muted-foreground">{t.title}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
