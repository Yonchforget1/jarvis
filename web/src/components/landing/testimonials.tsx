import { Star } from "lucide-react";

const TESTIMONIALS = [
  {
    quote:
      "Jarvis automated our entire deployment pipeline in one conversation. What used to take my team a full day now happens in 5 minutes.",
    name: "Marcus Chen",
    title: "CTO, TechForge",
    initial: "M",
    stars: 5,
  },
  {
    quote:
      "I built a complete multiplayer game prototype in an afternoon. The game dev tools are incredible - it scaffolded the project, generated assets, and even wrote the game logic.",
    name: "Sarah Kim",
    title: "Indie Game Developer",
    initial: "S",
    stars: 5,
  },
  {
    quote:
      "The self-improvement system is what sets Jarvis apart. It remembers what worked and what didn't. It genuinely gets better over time.",
    name: "David Park",
    title: "AI Researcher",
    initial: "D",
    stars: 5,
  },
  {
    quote:
      "We replaced three separate SaaS tools with Jarvis. The ROI was immediate - web scraping, file management, and code execution all in one platform.",
    name: "Elena Voss",
    title: "VP of Engineering, DataPulse",
    initial: "E",
    stars: 5,
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

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {TESTIMONIALS.map((t) => (
            <article
              key={t.name}
              aria-label={`Review by ${t.name}`}
              className="group rounded-2xl border border-white/5 bg-white/[0.02] p-6 transition-all duration-300 hover:border-primary/20 hover:bg-white/[0.04] hover:-translate-y-1 hover:shadow-xl hover:shadow-primary/5"
            >
              {/* Stars */}
              <div aria-label={`${t.stars} out of 5 stars`} className="flex gap-0.5 mb-4">
                {Array.from({ length: t.stars }).map((_, i) => (
                  <Star key={i} aria-hidden="true" className="h-3.5 w-3.5 fill-yellow-400 text-yellow-400" />
                ))}
              </div>
              <blockquote className="text-sm text-muted-foreground leading-relaxed mb-6">
                &ldquo;{t.quote}&rdquo;
              </blockquote>
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 text-sm font-medium text-primary group-hover:bg-primary/20 transition-colors">
                  {t.initial}
                </div>
                <div>
                  <p className="text-sm font-medium">{t.name}</p>
                  <p className="text-xs text-muted-foreground">{t.title}</p>
                </div>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
