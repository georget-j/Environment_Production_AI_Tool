import Link from "next/link";
import { NavAuthButton } from "@/components/nav-auth-button";

/**
 * Site nav. Server component, no Supabase round-trip — the user-specific
 * Dashboard / Sign-in button is rendered client-side by NavAuthButton
 * after hydration. Removing the server-side `getUser()` call shaved a
 * Supabase call off every page render.
 */
export function SiteNav() {
  return (
    <header className="border-b border-border">
      <nav className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
        <Link href="/" className="text-lg font-semibold">
          ProdReady AI
        </Link>
        <div className="flex items-center gap-2">
          <Link
            href="/tracks"
            className="text-sm text-muted-foreground hover:text-foreground"
          >
            Tracks
          </Link>
          <Link
            href="/pricing"
            className="text-sm text-muted-foreground hover:text-foreground"
          >
            Pricing
          </Link>
          <NavAuthButton />
        </div>
      </nav>
    </header>
  );
}
