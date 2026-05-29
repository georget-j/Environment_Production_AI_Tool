import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { Button } from "@/components/ui/button";
import {
  apiFetch,
  type MeProgressOut,
  type TrackOut,
  type TrackProgressOut,
} from "@/lib/api";

export default async function DashboardPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  // Fetch the public tracks list (no auth) AND the per-user progress
  // aggregate (auth) in parallel. Either call may fail (network, signed-out)
  // without taking down the rest of the page.
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

  const progressBySlug = new Map<string, TrackProgressOut>();
  for (const tp of progress?.tracks ?? []) progressBySlug.set(tp.slug, tp);
  const cont = progress?.continue_lesson ?? null;

  return (
    <div className="space-y-8 py-8">
      <header className="space-y-2">
        <h1 className="text-3xl font-semibold">
          Welcome{user?.email ? `, ${user.email}` : ""}
        </h1>
        <p className="text-muted-foreground">
          {cont
            ? "Pick up where you left off, or jump into a different track."
            : "Pick a track and start."}
        </p>
      </header>

      {cont && (
        <section className="rounded-lg border border-primary/40 bg-primary/5 p-5">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-primary">
            Continue · Lesson {cont.position} / {cont.total}
          </p>
          <h2 className="mt-1 text-xl font-semibold">{cont.challenge_title}</h2>
          <p className="mt-0.5 text-sm text-muted-foreground">
            {cont.track_title} · {cont.module_title}
          </p>
          <div className="mt-3">
            <Link href={`/challenges/${cont.challenge_slug}`}>
              <Button>Resume →</Button>
            </Link>
          </div>
        </section>
      )}

      <section className="space-y-3">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Your tracks
        </h2>
        <div className="grid gap-4 md:grid-cols-2">
          {tracks.map((t) => {
            const tp = progressBySlug.get(t.slug);
            const pct =
              tp && tp.total > 0
                ? Math.round((tp.completed / tp.total) * 100)
                : 0;
            const hasInProgress = !!tp?.latest_in_progress_slug;
            // Concept-based tracks (M5) deep-link to /concepts/<slug>,
            // not /challenges/<slug>, when resuming.
            const isConceptTrack = (tp?.concept_total ?? 0) > 0;
            const inProgressHref = isConceptTrack
              ? `/concepts/${tp!.latest_in_progress_slug}`
              : `/challenges/${tp!.latest_in_progress_slug}`;
            const ctaHref = hasInProgress
              ? inProgressHref
              : `/tracks/${t.slug}`;
            const ctaLabel = hasInProgress
              ? "Continue track →"
              : tp && tp.completed > 0
                ? "Open track"
                : "Start track →";
            return (
              <div
                key={t.slug}
                className="flex flex-col rounded-lg border border-border p-6"
              >
                <div className="flex items-center justify-between gap-3">
                  <h3 className="font-semibold">{t.title}</h3>
                  {t.difficulty && (
                    <span className="rounded-full bg-muted px-2 py-0.5 text-xs">
                      {t.difficulty}
                    </span>
                  )}
                </div>
                {t.description && (
                  <p className="mt-2 text-sm text-muted-foreground">
                    {t.description}
                  </p>
                )}
                {tp && tp.total > 0 && (
                  <div className="mt-4 space-y-1">
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <span>
                        {tp.completed} / {tp.total} lessons
                      </span>
                      <span>{pct}%</span>
                    </div>
                    <div
                      role="progressbar"
                      aria-valuenow={tp.completed}
                      aria-valuemin={0}
                      aria-valuemax={tp.total}
                      className="h-1.5 overflow-hidden rounded-full bg-muted"
                    >
                      <div
                        className="h-full bg-primary transition-[width] duration-300"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                )}
                <div className="mt-4">
                  <Link href={ctaHref}>
                    <Button size="sm">{ctaLabel}</Button>
                  </Link>
                </div>
              </div>
            );
          })}
          {tracks.length === 0 && (
            <p className="text-sm text-muted-foreground">
              No tracks available right now. Try again in a moment.
            </p>
          )}
        </div>
      </section>
    </div>
  );
}
