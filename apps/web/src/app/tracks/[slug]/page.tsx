import Link from "next/link";
import { notFound } from "next/navigation";
import {
  apiFetch,
  type ChallengeSummary,
  type TrackDetail,
  type TrackProgressDetail,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { PyodidePrewarm } from "@/components/pyodide-prewarm";
import { createClient } from "@/lib/supabase/server";

type Params = Promise<{ slug: string }>;

export default async function TrackDetailPage({ params }: { params: Params }) {
  const { slug } = await params;

  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  // Track is public; progress requires auth. Run in parallel so an
  // unauthenticated visitor still sees the lesson list.
  const [trackResult, progressResult] = await Promise.allSettled([
    apiFetch<TrackDetail>(`/api/tracks/${slug}`),
    user
      ? apiFetch<TrackProgressDetail>(`/api/me/track/${slug}/progress`, {
          requireAuth: true,
        })
      : Promise.resolve(null),
  ]);

  if (trackResult.status !== "fulfilled") {
    notFound();
  }
  const track: TrackDetail = trackResult.value;
  const progress: TrackProgressDetail | null =
    progressResult.status === "fulfilled" && progressResult.value
      ? progressResult.value
      : null;

  const completedSet = new Set(progress?.completed_slugs ?? []);
  const inProgressSet = new Set(progress?.in_progress_slugs ?? []);
  const nextUnsolved = progress?.next_unsolved_slug ?? null;

  // The API returns track.modules in order_index; challenges are returned in
  // their own order but cross all modules. Bucket each challenge into its
  // module so the page renders module → its lessons.
  const challengesByModule = new Map<string, ChallengeSummary[]>();
  for (const c of track.challenges) {
    const lessons = challengesByModule.get(c.module_id) ?? [];
    lessons.push(c);
    challengesByModule.set(c.module_id, lessons);
  }
  const firstModuleId = track.modules[0]?.id;
  if (
    firstModuleId &&
    challengesByModule.size === 0 &&
    track.challenges.length > 0
  ) {
    challengesByModule.set(firstModuleId, [...track.challenges]);
  }

  const totalCompleted = progress?.completed ?? 0;
  const totalLessons = progress?.total ?? track.challenges.length;
  const pct =
    totalLessons > 0 ? Math.round((totalCompleted / totalLessons) * 100) : 0;

  return (
    <div className="space-y-8 py-8">
      <PyodidePrewarm trackSlug={slug} />
      <header className="space-y-3">
        <h1 className="text-3xl font-semibold">{track.title}</h1>
        {track.description && (
          <p className="max-w-3xl text-muted-foreground">{track.description}</p>
        )}
        {slug === "quant-programmer" && (
          <Link
            href="/quant-roadmap"
            className="inline-block rounded-md border border-border bg-muted/20 px-4 py-2 text-sm font-medium hover:bg-muted/40"
          >
            Read the roadmap →
          </Link>
        )}
      </header>

      {progress && totalLessons > 0 && (
        <section className="sticky top-0 z-10 -mx-3 flex flex-wrap items-center justify-between gap-3 rounded-md border border-border bg-background/95 px-3 py-2 backdrop-blur supports-[backdrop-filter]:bg-background/70">
          <div className="flex min-w-0 flex-1 items-center gap-3">
            <span className="text-sm font-medium">
              {totalCompleted} / {totalLessons} lessons done
            </span>
            <div
              role="progressbar"
              aria-valuenow={totalCompleted}
              aria-valuemin={0}
              aria-valuemax={totalLessons}
              className="h-1.5 max-w-[280px] flex-1 overflow-hidden rounded-full bg-muted"
            >
              <div
                className="h-full bg-primary transition-[width] duration-300"
                style={{ width: `${pct}%` }}
              />
            </div>
            <span className="text-xs text-muted-foreground">{pct}%</span>
          </div>
          {nextUnsolved && (
            <Link href={`/challenges/${nextUnsolved}`}>
              <Button size="sm">Jump to next unsolved →</Button>
            </Link>
          )}
        </section>
      )}

      <div className="space-y-8">
        {track.modules.map((m) => {
          const lessons = (challengesByModule.get(m.id) ?? []).sort(
            (a, b) => a.order_index - b.order_index,
          );
          const moduleStats = progress?.module_progress?.[m.id];
          return (
            <section key={m.id} className="space-y-3">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h2 className="text-xl font-semibold">{m.title}</h2>
                {moduleStats && moduleStats.total > 0 && (
                  <span className="text-xs text-muted-foreground">
                    {moduleStats.completed} / {moduleStats.total}
                    {moduleStats.completed === moduleStats.total ? " ✓" : ""}
                  </span>
                )}
              </div>
              {lessons.length === 0 ? (
                <div className="rounded-lg border border-dashed border-border bg-muted/10 px-4 py-6 text-center text-sm text-muted-foreground">
                  Coming soon
                </div>
              ) : (
                <ul className="space-y-2">
                  {lessons.map((c) => {
                    const isDone = completedSet.has(c.slug);
                    const isInProgress = inProgressSet.has(c.slug);
                    const isCurrent = !isDone && c.slug === nextUnsolved;
                    return (
                      <li key={c.id}>
                        <Link
                          href={`/challenges/${c.slug}`}
                          className={
                            isDone
                              ? "flex items-center justify-between rounded-lg border border-green-200 bg-green-50/40 p-4 hover:bg-green-50"
                              : isCurrent
                                ? "flex items-center justify-between rounded-lg border border-primary/50 bg-primary/5 p-4 hover:bg-primary/10"
                                : "flex items-center justify-between rounded-lg border border-border p-4 hover:bg-muted"
                          }
                        >
                          <div className="flex min-w-0 items-start gap-3">
                            <span
                              aria-hidden="true"
                              className={
                                isDone
                                  ? "mt-0.5 inline-flex h-5 w-5 flex-none items-center justify-center rounded-full bg-green-600 text-[11px] font-bold text-white"
                                  : isCurrent
                                    ? "mt-0.5 inline-flex h-5 w-5 flex-none items-center justify-center rounded-full bg-primary text-[11px] font-bold text-primary-foreground"
                                    : isInProgress
                                      ? "mt-0.5 inline-flex h-5 w-5 flex-none items-center justify-center rounded-full border border-amber-400 bg-amber-50 text-[11px] font-bold text-amber-700"
                                      : "mt-0.5 inline-flex h-5 w-5 flex-none items-center justify-center rounded-full border border-border text-[11px] text-muted-foreground"
                              }
                            >
                              {isDone
                                ? "✓"
                                : isCurrent
                                  ? "▸"
                                  : isInProgress
                                    ? "·"
                                    : ""}
                            </span>
                            <div className="min-w-0">
                              <p className="font-medium">
                                {c.order_index}. {c.title}
                              </p>
                              {c.skills.length > 0 && (
                                <p className="mt-1 text-xs text-muted-foreground">
                                  {c.skills.join(" · ")}
                                </p>
                              )}
                            </div>
                          </div>
                          {c.is_free ? (
                            <span className="rounded-full bg-muted px-2 py-1 text-xs">
                              Free
                            </span>
                          ) : (
                            <span className="rounded-full bg-primary px-2 py-1 text-xs text-primary-foreground">
                              Pro
                            </span>
                          )}
                        </Link>
                      </li>
                    );
                  })}
                </ul>
              )}
            </section>
          );
        })}
      </div>
    </div>
  );
}
