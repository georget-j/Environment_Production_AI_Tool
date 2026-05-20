import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { Button } from "@/components/ui/button";

export default async function DashboardPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  return (
    <div className="space-y-8 py-8">
      <header className="space-y-2">
        <h1 className="text-3xl font-semibold">Welcome{user?.email ? `, ${user.email}` : ""}</h1>
        <p className="text-muted-foreground">Pick up where you left off.</p>
      </header>
      <section className="rounded-lg border border-border p-6">
        <h2 className="mb-2 font-semibold">Backend Production Developer</h2>
        <p className="mb-4 text-sm text-muted-foreground">
          Python, FastAPI, and pytest — broken services to fix, all in your browser.
        </p>
        <Link href="/tracks/backend-production-python">
          <Button>Open track</Button>
        </Link>
      </section>
    </div>
  );
}
