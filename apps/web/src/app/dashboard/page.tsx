import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { Button } from "@/components/ui/button";
import { apiFetch, type TrackOut } from "@/lib/api";

export default async function DashboardPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  let tracks: TrackOut[] = [];
  try {
    tracks = await apiFetch<TrackOut[]>("/api/tracks");
  } catch {
    // Render the page without the list rather than 500 the dashboard.
  }

  return (
    <div className="space-y-8 py-8">
      <header className="space-y-2">
        <h1 className="text-3xl font-semibold">Welcome{user?.email ? `, ${user.email}` : ""}</h1>
        <p className="text-muted-foreground">Pick a track and start.</p>
      </header>

      <section className="grid gap-4 md:grid-cols-2">
        {tracks.map((t) => (
          <div key={t.slug} className="flex flex-col rounded-lg border border-border p-6">
            <div className="flex items-center justify-between gap-3">
              <h2 className="font-semibold">{t.title}</h2>
              {t.difficulty && (
                <span className="rounded-full bg-muted px-2 py-0.5 text-xs">{t.difficulty}</span>
              )}
            </div>
            {t.description && (
              <p className="mt-2 mb-4 text-sm text-muted-foreground">{t.description}</p>
            )}
            <div className="mt-auto">
              <Link href={`/tracks/${t.slug}`}>
                <Button size="sm">Open track</Button>
              </Link>
            </div>
          </div>
        ))}
        {tracks.length === 0 && (
          <p className="text-sm text-muted-foreground">
            No tracks available right now. Try again in a moment.
          </p>
        )}
      </section>
    </div>
  );
}
