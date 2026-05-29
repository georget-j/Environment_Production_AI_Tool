import Link from "next/link";

import {
  fetchMyConceptMastery,
  listConcepts,
  type ConceptMasteryEntry,
} from "@/lib/concepts-server";
import type { ConceptSummary } from "@/lib/concepts";

/**
 * Mental Models track index (M9).
 *
 * Layered grid of concept atoms:
 *  - Row 1: Universal CS foundations (shared across concept-based tracks).
 *  - Row 2: Mental Models (topic-specific).
 *
 * Each concept renders as a card coloured by mastery:
 *  - mastered      → green
 *  - in-progress   → amber
 *  - recommended   → blue ring (first untouched concept with all prereqs mastered)
 *  - untouched     → grey
 *  - needs-review  → orange (reserved; spaced-recall not shipped yet)
 *
 * Prereq edges render as thin SVG lines underneath the cards. We don't pull
 * react-flow in for this — a single-screen layered DAG renders cleanly with
 * native CSS grid + an SVG overlay computed from each card's slug → element.
 *
 * (Deferred from CC.6 + v2-M9 — the concept-map UI before authoring the
 * final 3 Layer-2 concepts.)
 */

type ConceptStatus = "untouched" | "in_progress" | "mastered" | "recommended";

export default async function MentalModelsTrackPage() {
  let concepts: ConceptSummary[];
  let mastery: Record<string, ConceptMasteryEntry> = {};
  try {
    concepts = await listConcepts();
    // Mastery fetch is best-effort — if it 401s we still render the map.
    try {
      mastery = await fetchMyConceptMastery();
    } catch {
      mastery = {};
    }
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
  const masteredCount = concepts.filter(
    (c) => mastery[c.slug]?.mastered_at,
  ).length;
  const totalCount = concepts.length;

  // Compute the recommended-next concept: first one the learner hasn't
  // touched whose prereqs are all mastered. If everything is mastered or
  // every untouched concept still has unmet prereqs, recommend nothing.
  function status(c: ConceptSummary): ConceptStatus {
    const m = mastery[c.slug];
    if (m?.mastered_at) return "mastered";
    if (m?.started) return "in_progress";
    return "untouched";
  }
  const recommendedSlug = (() => {
    const sorted = [...concepts].sort(
      (a, b) =>
        (a.layer === "universal" ? 0 : 1) - (b.layer === "universal" ? 0 : 1) ||
        a.order_index - b.order_index,
    );
    for (const c of sorted) {
      if (status(c) !== "untouched") continue;
      const prereqs = c.prereqs ?? [];
      const ok = prereqs.every((s) => mastery[s]?.mastered_at);
      if (ok) return c.slug;
    }
    return null;
  })();

  return (
    <div className="mx-auto max-w-5xl py-8">
      <header className="flex flex-col gap-2">
        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          Track
        </p>
        <h1 className="text-3xl font-semibold leading-tight">
          Mental Models for Code
        </h1>
        <p className="max-w-3xl text-sm text-muted-foreground">
          Learn how to think about code, not just write it. Each concept is a
          six-stage UNIT — Try → Read → Play → Check → Apply → Reflect — built
          on cognitive-load theory, productive failure, retrieval practice, and
          Bret Victor&apos;s &quot;See the state&quot; principle.
        </p>
        {totalCount > 0 && (
          <p className="mt-1 text-sm font-medium">
            Your mastery: {masteredCount} / {totalCount}{" "}
            {masteredCount === totalCount && "✓"}
          </p>
        )}
      </header>

      <Legend />

      <ConceptLayer
        title="Universal CS foundations"
        subtitle="Shared library — mastering these here marks them mastered for every track."
        concepts={universal}
        mastery={mastery}
        recommendedSlug={recommendedSlug}
      />

      <ConceptLayer
        title="Mental models"
        subtitle="Topic-specific. Build on the universal foundations above."
        concepts={topic}
        mastery={mastery}
        recommendedSlug={recommendedSlug}
      />

      {topic.length < 4 && (
        <p className="mt-8 text-xs text-muted-foreground">
          {topic.length} of 4 mental-models atoms authored. The remaining{" "}
          {4 - topic.length} ship in a later sub-phase.
        </p>
      )}
    </div>
  );
}

function Legend() {
  return (
    <div className="mt-4 flex flex-wrap items-center gap-3 rounded-md border border-border bg-muted/20 p-3 text-xs">
      <span className="font-medium text-muted-foreground">Legend:</span>
      <LegendDot className="bg-green-500" label="mastered" />
      <LegendDot className="bg-amber-500" label="in progress" />
      <LegendDot
        className="bg-background ring-2 ring-blue-500"
        label="recommended next"
      />
      <LegendDot className="bg-muted" label="untouched" />
    </div>
  );
}

function LegendDot({ className, label }: { className: string; label: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <span
        aria-hidden="true"
        className={`inline-block h-2.5 w-2.5 rounded-full ${className}`}
      />
      <span>{label}</span>
    </span>
  );
}

function ConceptLayer({
  title,
  subtitle,
  concepts,
  mastery,
  recommendedSlug,
}: {
  title: string;
  subtitle: string;
  concepts: ConceptSummary[];
  mastery: Record<string, ConceptMasteryEntry>;
  recommendedSlug: string | null;
}) {
  if (concepts.length === 0) return null;
  return (
    <section className="mt-8">
      <h2 className="text-lg font-semibold">{title}</h2>
      <p className="mt-1 text-xs text-muted-foreground">{subtitle}</p>
      <ol className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {concepts.map((c) => {
          const isMastered = !!mastery[c.slug]?.mastered_at;
          const isStarted = !!mastery[c.slug]?.started && !isMastered;
          const isRecommended = c.slug === recommendedSlug;
          const stateClass = isMastered
            ? "border-green-400 bg-green-50/60 hover:bg-green-50"
            : isStarted
              ? "border-amber-400 bg-amber-50/60 hover:bg-amber-50"
              : isRecommended
                ? "border-blue-300 bg-background ring-2 ring-blue-400 hover:bg-blue-50/40"
                : "border-border bg-background hover:bg-muted/40";
          const stateLabel = isMastered
            ? "Mastered ✓"
            : isStarted
              ? "In progress"
              : isRecommended
                ? "Start here →"
                : null;
          const stateLabelClass = isMastered
            ? "text-green-800"
            : isStarted
              ? "text-amber-800"
              : "text-blue-800";
          return (
            <li key={c.slug}>
              <Link
                href={`/concepts/${c.slug}`}
                className={`flex flex-col gap-1.5 rounded-md border p-3 transition-colors ${stateClass}`}
              >
                {stateLabel && (
                  <span
                    className={`text-[10px] font-semibold uppercase tracking-wide ${stateLabelClass}`}
                  >
                    {stateLabel}
                  </span>
                )}
                <span className="text-sm font-semibold">{c.title}</span>
                <span className="text-xs text-muted-foreground">
                  {c.one_line}
                </span>
                {(c.prereqs?.length ?? 0) > 0 && (
                  <span className="mt-1 text-[10px] text-muted-foreground">
                    Needs: {(c.prereqs ?? []).join(", ")}
                  </span>
                )}
              </Link>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
