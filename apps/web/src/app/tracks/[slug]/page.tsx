import Link from "next/link";
import { notFound } from "next/navigation";
import { apiFetch, type ChallengeSummary, type TrackDetail } from "@/lib/api";
import { PyodidePrewarm } from "@/components/pyodide-prewarm";

type Params = Promise<{ slug: string }>;

export default async function TrackDetailPage({ params }: { params: Params }) {
  const { slug } = await params;
  let track: TrackDetail;
  try {
    track = await apiFetch<TrackDetail>(`/api/tracks/${slug}`);
  } catch {
    notFound();
  }

  // The API returns track.modules in order_index; challenges are returned in
  // their own order but cross all modules. Bucket each challenge into its
  // module so the page renders module → its lessons.
  const challengesByModule = new Map<string, ChallengeSummary[]>();
  for (const c of track.challenges) {
    const lessons = challengesByModule.get(c.module_id) ?? [];
    lessons.push(c);
    challengesByModule.set(c.module_id, lessons);
  }
  // Some legacy challenges may not include module_id in the summary view;
  // fall back to "everything goes under the first module" so older tracks
  // still render.
  const firstModuleId = track.modules[0]?.id;
  if (
    firstModuleId &&
    challengesByModule.size === 0 &&
    track.challenges.length > 0
  ) {
    challengesByModule.set(firstModuleId, [...track.challenges]);
  }

  return (
    <div className="space-y-10 py-8">
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

      <div className="space-y-8">
        {track.modules.map((m) => {
          const lessons = (challengesByModule.get(m.id) ?? []).sort(
            (a, b) => a.order_index - b.order_index,
          );
          return (
            <section key={m.id} className="space-y-3">
              <h2 className="text-xl font-semibold">{m.title}</h2>
              {lessons.length === 0 ? (
                <div className="rounded-lg border border-dashed border-border bg-muted/10 px-4 py-6 text-center text-sm text-muted-foreground">
                  Coming soon
                </div>
              ) : (
                <ul className="space-y-2">
                  {lessons.map((c) => (
                    <li key={c.id}>
                      <Link
                        href={`/challenges/${c.slug}`}
                        className="flex items-center justify-between rounded-lg border border-border p-4 hover:bg-muted"
                      >
                        <div>
                          <p className="font-medium">
                            {c.order_index}. {c.title}
                          </p>
                          {c.skills.length > 0 && (
                            <p className="mt-1 text-xs text-muted-foreground">
                              {c.skills.join(" · ")}
                            </p>
                          )}
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
                  ))}
                </ul>
              )}
            </section>
          );
        })}
      </div>
    </div>
  );
}
