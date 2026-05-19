"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { Button } from "@/components/ui/button";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export function UpgradeButton({ className }: { className?: string }) {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleUpgrade() {
    setPending(true);
    setError(null);

    const supabase = createClient();
    const {
      data: { session },
    } = await supabase.auth.getSession();
    if (!session) {
      router.push("/login?next=/pricing");
      return;
    }

    const origin = window.location.origin;
    const response = await fetch(`${API_BASE_URL}/api/billing/checkout`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${session.access_token}`,
      },
      body: JSON.stringify({
        success_url: `${origin}/dashboard?upgrade=success`,
        cancel_url: `${origin}/pricing?upgrade=cancelled`,
      }),
    });

    setPending(false);
    if (!response.ok) {
      const body = await response.text();
      setError(`Could not start checkout (${response.status}). ${body.slice(0, 200)}`);
      return;
    }
    const { url } = await response.json();
    window.location.href = url;
  }

  return (
    <div className="space-y-2">
      <Button onClick={handleUpgrade} disabled={pending} className={className}>
        {pending ? "Opening Stripe…" : "Upgrade to Pro"}
      </Button>
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
}
