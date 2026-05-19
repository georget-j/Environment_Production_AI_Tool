import Link from "next/link";
import { notFound } from "next/navigation";
import { apiFetch, type TrackDetail } from "@/lib/api";

type Params = Promise<{ slug: string }>;

export default async function TrackDetailPage({ params }: { params: Params }) {
  const { slug } = await params;
  let track: TrackDetail;
  try {
    track = await apiFetch<TrackDetail>(`/api/tracks/${slug}`);
  } catch {
    notFound();
  }

  const moduleTitle = track.modules[0]?.title ?? "Challenges";
  const ordered = [...track.challenges].sort((a, b) => a.order_index - b.order_index);

  return (
    <div className="space-y-10 py-8">
      <header className="space-y-2">
        <h1 className="text-3xl font-semibold">{track.title}</h1>
        {track.description && (
          <p className="max-w-2xl text-muted-foreground">{track.description}</p>
        )}
      </header>

      <section className="space-y-4">
        <h2 className="text-xl font-semibold">{moduleTitle}</h2>
        <ul className="space-y-2">
          {ordered.map((c) => (
            <li key={c.id}>
              <Link
                href={`/challenges/${c.slug}`}
                className="flex items-center justify-between rounded-lg border border-border p-4 hover:bg-muted"
              >
                <div>
                  <p className="font-medium">
                    {c.order_index}. {c.title}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">{c.skills.join(" · ")}</p>
                </div>
                {c.is_free ? (
                  <span className="rounded-full bg-muted px-2 py-1 text-xs">Free</span>
                ) : (
                  <span className="rounded-full bg-primary px-2 py-1 text-xs text-primary-foreground">
                    Pro
                  </span>
                )}
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
