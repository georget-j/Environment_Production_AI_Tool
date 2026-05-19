import { UpgradeButton } from "@/components/upgrade-button";

export default function PricingPage() {
  return (
    <div className="space-y-8 py-8">
      <header className="space-y-2 text-center">
        <h1 className="text-3xl font-semibold">Pricing</h1>
        <p className="text-muted-foreground">Start free. Upgrade when you&apos;re ready.</p>
      </header>
      <div className="grid gap-6 md:grid-cols-2">
        <div className="rounded-lg border border-border p-6">
          <h2 className="text-xl font-semibold">Free</h2>
          <p className="my-4 text-3xl font-bold">£0</p>
          <ul className="space-y-2 text-sm text-muted-foreground">
            <li>First 2 challenges</li>
            <li>AI mentor (limited)</li>
            <li>AI PR review</li>
          </ul>
        </div>
        <div className="rounded-lg border-2 border-primary p-6">
          <h2 className="text-xl font-semibold">Pro</h2>
          <p className="my-4 text-3xl font-bold">
            £19<span className="text-base font-normal text-muted-foreground">/mo</span>
          </p>
          <ul className="mb-6 space-y-2 text-sm text-muted-foreground">
            <li>All challenges in the Backend Production track</li>
            <li>Unlimited AI mentor</li>
            <li>Full PR review on every submission</li>
            <li>Portfolio summary</li>
          </ul>
          <UpgradeButton className="w-full" />
        </div>
      </div>
    </div>
  );
}
