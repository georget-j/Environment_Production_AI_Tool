import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { apiFetch, type MeProgressOut, type TrackOut } from "@/lib/api";

export default async function TracksPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  const [tracksResult, progressResult] = await Promise.allSettled([
    apiFetch<TrackOut[]>("/api/tracks"),
    user
      ? apiFetch<MeProgressOut>("/api/me/progress", { requireAuth: true })
      : Promise.resolve(null),
  ]);

  const tracks: TrackOut[] =
    tracksResult.status === "fulfilled" ? tracksResult.value : [];
  const progress: MeProgressOut | null =
    progressResult.status === "fulfilled" && progressResult.value
      ? progressResult.value
      : null;
  const progressBySlug = new Map<
    string,
    { completed: number; total: number }
  >();
  for (const tp of progress?.tracks ?? []) {
    progressBySlug.set(tp.slug, { completed: tp.completed, total: tp.total });
  }

  return (
    <div className="space-y-6 py-8">
      <h1 className="text-3xl font-semibold">Tracks</h1>
      <p className="text-muted-foreground">
        Pick a track and start. Lessons run in your browser — no setup needed.
      </p>
      <div className="grid gap-4">
        {tracks.map((t) => {
          const tp = progressBySlug.get(t.slug);
          const pct =
            tp && tp.total > 0
              ? Math.round((tp.completed / tp.total) * 100)
              : 0;
          return (
            <Link
              key={t.slug}
              href={`/tracks/${t.slug}`}
              className="rounded-lg border border-border p-6 hover:bg-muted"
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h2 className="font-semibold">{t.title}</h2>
                <div className="flex items-center gap-2">
                  {tp && tp.total > 0 && (
                    <span className="rounded-full border border-border bg-background px-2 py-0.5 text-xs text-muted-foreground">
                      {tp.completed} / {tp.total} · {pct}%
                    </span>
                  )}
                  {t.difficulty && (
                    <span className="rounded-full bg-muted px-2 py-0.5 text-xs">
                      {t.difficulty}
                    </span>
                  )}
                </div>
              </div>
              {t.description && (
                <p className="mt-2 text-sm text-muted-foreground">
                  {t.description}
                </p>
              )}
            </Link>
          );
        })}
        {tracks.length === 0 && (
          <p className="text-sm text-muted-foreground">
            No tracks available right now. Try again in a moment.
          </p>
        )}
      </div>
    </div>
  );
}
