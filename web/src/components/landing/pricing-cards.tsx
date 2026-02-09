import Link from "next/link";
import { Check } from "lucide-react";
import { Button } from "@/components/ui/button";

const TIERS = [
  {
    name: "Starter",
    price: "$97",
    period: "/month",
    description: "For individuals getting started",
    features: [
      "1 user",
      "500 messages/month",
      "Claude backend",
      "All 16 tools",
      "Email support",
    ],
    cta: "Start Free Trial",
    highlighted: false,
  },
  {
    name: "Professional",
    price: "$297",
    period: "/month",
    description: "For teams and power users",
    features: [
      "5 users",
      "Unlimited messages",
      "All AI backends",
      "Custom tools & plugins",
      "Priority support",
      "API access",
    ],
    cta: "Start Free Trial",
    highlighted: true,
  },
  {
    name: "Enterprise",
    price: "$497",
    period: "/month",
    description: "For organizations at scale",
    features: [
      "Unlimited users",
      "Unlimited everything",
      "White-label branding",
      "Custom integrations",
      "Dedicated support",
      "On-premise deployment",
    ],
    cta: "Contact Sales",
    highlighted: false,
  },
];

export function PricingCards() {
  return (
    <section id="pricing" className="px-4 py-24">
      <div className="mx-auto max-w-6xl">
        <div className="text-center mb-16">
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight mb-4">
            Simple, Transparent Pricing
          </h2>
          <p className="text-muted-foreground max-w-xl mx-auto">
            Choose the plan that matches your ambition. Every plan includes all 16 tools.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto">
          {TIERS.map((tier) => (
            <div
              key={tier.name}
              className={`relative rounded-2xl border p-8 ${
                tier.highlighted
                  ? "border-primary/40 bg-primary/[0.03] shadow-[0_0_40px_rgba(99,102,241,0.1)]"
                  : "border-white/5 bg-white/[0.02]"
              }`}
            >
              {tier.highlighted && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-gradient-to-r from-primary to-purple-500 px-3 py-0.5 text-[10px] font-semibold text-white">
                  MOST POPULAR
                </div>
              )}
              <h3 className="text-lg font-semibold">{tier.name}</h3>
              <p className="text-sm text-muted-foreground mt-1">{tier.description}</p>
              <div className="mt-6 flex items-baseline gap-1">
                <span className="text-4xl font-bold">{tier.price}</span>
                <span className="text-sm text-muted-foreground">{tier.period}</span>
              </div>
              <ul className="mt-6 space-y-3">
                {tier.features.map((feature) => (
                  <li key={feature} className="flex items-center gap-2 text-sm">
                    <Check className="h-4 w-4 text-primary shrink-0" />
                    {feature}
                  </li>
                ))}
              </ul>
              <Button
                asChild
                className={`mt-8 w-full rounded-xl ${
                  tier.highlighted
                    ? "bg-gradient-to-r from-primary to-purple-500 hover:from-primary/90 hover:to-purple-500/90"
                    : ""
                }`}
                variant={tier.highlighted ? "default" : "outline"}
              >
                <Link href="/register">{tier.cta}</Link>
              </Button>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
