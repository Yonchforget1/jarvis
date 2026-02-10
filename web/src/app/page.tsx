import { Navbar } from "@/components/layout/navbar";
import { Footer } from "@/components/layout/footer";
import { Hero } from "@/components/landing/hero";
import { StatsCounter } from "@/components/landing/stats-counter";
import { Features } from "@/components/landing/features";
import { PricingCards } from "@/components/landing/pricing-cards";
import { Testimonials } from "@/components/landing/testimonials";
import { CtaSection } from "@/components/landing/cta-section";

const jsonLd = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "SoftwareApplication",
      name: "JARVIS AI Agent Platform",
      applicationCategory: "BusinessApplication",
      operatingSystem: "Web",
      description:
        "The most advanced AI agent platform. Execute real tasks on real computers with 16+ professional tools.",
      offers: [
        {
          "@type": "Offer",
          name: "Starter",
          price: "97",
          priceCurrency: "USD",
          priceSpecification: { "@type": "UnitPriceSpecification", billingDuration: "P1M" },
        },
        {
          "@type": "Offer",
          name: "Professional",
          price: "297",
          priceCurrency: "USD",
          priceSpecification: { "@type": "UnitPriceSpecification", billingDuration: "P1M" },
        },
        {
          "@type": "Offer",
          name: "Enterprise",
          price: "497",
          priceCurrency: "USD",
          priceSpecification: { "@type": "UnitPriceSpecification", billingDuration: "P1M" },
        },
      ],
      featureList: [
        "Filesystem Control",
        "Code Execution",
        "Web Intelligence",
        "Game Development",
        "Self-Improving Memory",
        "Multi-Backend AI",
      ],
    },
    {
      "@type": "Organization",
      name: "JARVIS AI",
      url: "https://jarvis.ai",
      founder: { "@type": "Person", name: "Yonatan Weintraub" },
    },
  ],
};

export default function LandingPage() {
  return (
    <div className="min-h-screen">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <Navbar />
      <Hero />
      <StatsCounter />
      <Features />
      <Testimonials />
      <PricingCards />
      <CtaSection />
      <Footer />
    </div>
  );
}
