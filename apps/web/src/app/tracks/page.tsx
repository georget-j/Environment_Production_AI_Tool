import Link from "next/link";
import { apiFetch, type TrackOut } from "@/lib/api";

export default async function TracksPage() {
  let tracks: TrackOut[] = [];
  try {
    tracks = await apiFetch<TrackOut[]>("/api/tracks");
  } catch {
    // The API may be momentarily unavailable; render an empty list rather than 500.
  }

  return (
    <div className="space-y-6 py-8">
      <h1 className="text-3xl font-semibold">Tracks</h1>
      <p className="text-muted-foreground">
        Pick a track and start. Lessons run in your browser — no setup needed.
      </p>
      <div className="grid gap-4">
        {tracks.map((t) => (
          <Link
            key={t.slug}
            href={`/tracks/${t.slug}`}
            className="rounded-lg border border-border p-6 hover:bg-muted"
          >
            <div className="flex items-center justify-between gap-3">
              <h2 className="font-semibold">{t.title}</h2>
              {t.difficulty && (
                <span className="rounded-full bg-muted px-2 py-0.5 text-xs">{t.difficulty}</span>
              )}
            </div>
            {t.description && (
              <p className="mt-2 text-sm text-muted-foreground">{t.description}</p>
            )}
          </Link>
        ))}
        {tracks.length === 0 && (
          <p className="text-sm text-muted-foreground">
            No tracks available right now. Try again in a moment.
          </p>
        )}
      </div>
    </div>
  );
}
