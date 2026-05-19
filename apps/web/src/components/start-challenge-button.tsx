"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { Button } from "@/components/ui/button";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export function StartChallengeButton({ slug }: { slug: string }) {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleStart() {
    setPending(true);
    setError(null);
    const supabase = createClient();
    const {
      data: { session },
    } = await supabase.auth.getSession();
    if (!session) {
      router.push(`/login?next=/challenges/${slug}`);
      return;
    }
    const response = await fetch(`${API_BASE_URL}/api/challenges/${slug}/start`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${session.access_token}`,
      },
    });
    setPending(false);
    if (!response.ok) {
      setError(`Failed: ${response.status}`);
      return;
    }
    router.refresh();
  }

  return (
    <div className="space-y-2">
      <Button className="w-full" disabled={pending} onClick={handleStart}>
        {pending ? "…" : "Start challenge"}
      </Button>
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
}
