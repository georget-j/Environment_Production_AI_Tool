"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { Button } from "@/components/ui/button";

export default function LoginPage() {
  return (
    <Suspense fallback={<p className="py-12 text-center text-sm text-muted-foreground">Loading…</p>}>
      <LoginForm />
    </Suspense>
  );
}

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = searchParams.get("next") ?? "/dashboard";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setPending(true);
    setError(null);
    const supabase = createClient();
    const { error } =
      mode === "signin"
        ? await supabase.auth.signInWithPassword({ email, password })
        : await supabase.auth.signUp({ email, password });
    setPending(false);
    if (error) {
      setError(error.message);
      return;
    }
    router.push(next);
    router.refresh();
  }

  return (
    <div className="mx-auto max-w-sm space-y-6 py-12">
      <div className="space-y-2 text-center">
        <h1 className="text-2xl font-semibold">{mode === "signin" ? "Sign in" : "Create account"}</h1>
        <p className="text-sm text-muted-foreground">
          {mode === "signin" ? "Welcome back." : "Free for the first 2 challenges."}
        </p>
      </div>
      <form onSubmit={handleSubmit} className="space-y-4">
        <input
          type="email"
          required
          placeholder="you@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
        />
        <input
          type="password"
          required
          minLength={8}
          placeholder="Password (min 8 chars)"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
        />
        {error && <p className="text-sm text-red-600">{error}</p>}
        <Button type="submit" disabled={pending} className="w-full">
          {pending ? "…" : mode === "signin" ? "Sign in" : "Create account"}
        </Button>
      </form>
      <button
        type="button"
        onClick={() => setMode(mode === "signin" ? "signup" : "signin")}
        className="block w-full text-center text-sm text-muted-foreground hover:text-foreground"
      >
        {mode === "signin" ? "Need an account? Sign up" : "Already have an account? Sign in"}
      </button>
    </div>
  );
}
