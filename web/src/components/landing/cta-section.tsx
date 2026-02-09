import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";

export function CtaSection() {
  return (
    <section className="px-4 py-24">
      <div className="mx-auto max-w-3xl text-center">
        <div className="rounded-3xl border border-primary/20 bg-gradient-to-b from-primary/5 to-transparent p-12 sm:p-16">
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight mb-4">
            Ready to Deploy Your AI Workforce?
          </h2>
          <p className="text-muted-foreground mb-8 max-w-lg mx-auto">
            Stop talking to chatbots. Start giving orders to an agent that executes.
            16 tools. 3 AI backends. Unlimited capability.
          </p>
          <Button
            asChild
            size="lg"
            className="gap-2 rounded-xl px-8 bg-gradient-to-r from-primary to-purple-500 hover:from-primary/90 hover:to-purple-500/90"
          >
            <Link href="/register">
              Get Started Now
              <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
          <p className="mt-4 text-xs text-muted-foreground">
            No credit card required. Free trial included.
          </p>
        </div>
      </div>
    </section>
  );
}
