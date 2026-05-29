import Link from "next/link";

import { listConcepts } from "@/lib/concepts-server";

/**
 * Minimal Mental Models track index — lists the 10 concept atoms
 * grouped by layer with deep-links to each unit. This is a tactical
 * stand-in until CC.6 ships the full concept-map UI (react-flow graph
 * + per-stage progress + recommended-next highlight).
 *
 * The dedicated slug `mental-models` is on this static route rather
 * than the generic `/tracks/[slug]` page because the underlying data
 * shape is concepts, not modules/challenges, and the rendering is
 * intentionally different.
 */
export default async function MentalModelsTrackPage() {
  let concepts: Awaited<ReturnType<typeof listConcepts>>;
  try {
    concepts = await listConcepts();
  } catch (err) {
    return (
      <div className="mx-auto max-w-2xl py-10">
        <h1 className="text-2xl font-semibold">Mental Models for Code</h1>
        <p className="mt-4 text-sm text-red-700">
          Couldn&apos;t load concepts: {String(err)}
        </p>
        <p className="mt-2 text-sm text-muted-foreground">
          If you&apos;re not signed in, head to{" "}
          <Link href="/login" className="underline">
            log in
          </Link>{" "}
          and come back.
        </p>
      </div>
    );
  }

  const universal = concepts.filter((c) => c.layer === "universal");
  const topic = concepts.filter((c) => c.layer === "topic");

  return (
    <div className="mx-auto max-w-3xl py-8">
      <header className="flex flex-col gap-2">
        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          Track
        </p>
        <h1 className="text-3xl font-semibold leading-tight">
          Mental Models for Code
        </h1>
        <p className="text-sm text-muted-foreground">
          A research-backed framework for learning how to think about code, not
          just write it. Each concept is a six-stage UNIT — Try → Read → Play →
          Check → Apply → Reflect — built on cognitive-load theory, productive
          failure, retrieval practice, and Bret Victor&apos;s &quot;See the
          state&quot; principle.
        </p>
      </header>

      <ConceptList
        title="Universal CS foundations"
        subtitle="Shared library — mastering these here marks them mastered for every track."
        concepts={universal}
      />

      <ConceptList
        title="Mental models"
        subtitle="Topic-specific. Build on the universal foundations above."
        concepts={topic}
      />

      {topic.length < 4 && (
        <p className="mt-8 text-xs text-muted-foreground">
          {topic.length} of 4 mental-models atoms authored. The remaining{" "}
          {4 - topic.length} ship in CC.5c.
        </p>
      )}
    </div>
  );
}

function ConceptList({
  title,
  subtitle,
  concepts,
}: {
  title: string;
  subtitle: string;
  concepts: Awaited<ReturnType<typeof listConcepts>>;
}) {
  if (concepts.length === 0) {
    return null;
  }
  return (
    <section className="mt-8">
      <h2 className="text-lg font-semibold">{title}</h2>
      <p className="mt-1 text-xs text-muted-foreground">{subtitle}</p>
      <ol className="mt-3 flex flex-col gap-2">
        {concepts.map((c) => (
          <li key={c.slug}>
            <Link
              href={`/concepts/${c.slug}`}
              className="flex flex-col gap-1 rounded-md border border-border bg-background p-3 transition-colors hover:border-foreground/50"
            >
              <span className="text-sm font-medium">{c.title}</span>
              <span className="text-xs text-muted-foreground">
                {c.one_line}
              </span>
            </Link>
          </li>
        ))}
      </ol>
    </section>
  );
}
