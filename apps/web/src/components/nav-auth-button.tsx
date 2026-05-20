"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";

/**
 * Client-side auth state for the nav bar. Reads cookies for the presence of
 * the Supabase access token (no validation — middleware enforces real auth
 * on protected routes). Removes the Supabase round-trip that the previous
 * server-component SiteNav did on every page render.
 */
function hasAuthCookie(): boolean {
  if (typeof document === "undefined") return false;
  // Supabase SSR sets `sb-<project-ref>-auth-token` on sign-in.
  return /(?:^|;\s*)sb-[^=]+-auth-token=/.test(document.cookie);
}

export function NavAuthButton() {
  // Render the unauthenticated state first; flip to Dashboard once we see
  // the cookie. This avoids a hydration mismatch (server can't read cookies
  // synchronously here) and is invisible to the user — the swap happens
  // in the same paint.
  const [signedIn, setSignedIn] = useState(false);
  useEffect(() => {
    setSignedIn(hasAuthCookie());
    // Re-check on every focus, so signing out in another tab updates the nav.
    const onFocus = () => setSignedIn(hasAuthCookie());
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, []);

  return signedIn ? (
    <Link href="/dashboard">
      <Button size="sm" variant="outline">
        Dashboard
      </Button>
    </Link>
  ) : (
    <Link href="/login">
      <Button size="sm">Sign in</Button>
    </Link>
  );
}
