"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Markdown } from "@/components/markdown";
import type { ChallengeNavRef } from "@/lib/api";

type Props = {
  challengeSlug: string;
  moduleTitle: string;
  challengeTitle: string;
  scenario: string;
  learnerGoal: string;
  instructions: string;
  previous: ChallengeNavRef | null;
  next: ChallengeNavRef | null;
  position: number;
  total: number;
};

/**
 * Compact strip at the top of a lesson page. Expanded by default so the
 * Concept / Example / action verb are visible on first visit; collapsed
 * state persists per challenge slug in localStorage so a learner who
 * already knows the lesson shape can hide it.
 */
export function LessonContextStrip({
  challengeSlug,
  moduleTitle,
  challengeTitle,
  scenario,
  learnerGoal,
  instructions,
  previous,
  next,
  position,
  total,
}: Props) {
  // SSR/CSR consistency: initial render uses the default-expanded state.
  // The effect below restores a previously-collapsed choice once mounted.
  const [expanded, setExpanded] = useState(true);
  useEffect(() => {
    if (typeof window === "undefined") return;
    const stored = window.localStorage.getItem(
      `prodready:strip-collapsed:${challengeSlug}`,
    );
    if (stored === "true") setExpanded(false);
  }, [challengeSlug]);
  const toggleExpanded = () => {
    setExpanded((prev) => {
      const next = !prev;
      if (typeof window !== "undefined") {
        window.localStorage.setItem(
          `prodready:strip-collapsed:${challengeSlug}`,
          next ? "false" : "true",
        );
      }
      return next;
    });
  };
  const showNav = total > 1;
  const pct =
    total > 1 ? Math.max(0, Math.min(100, (position / total) * 100)) : 0;

  return (
    <section className="flex-none border-b border-border bg-background">
      {/* Row 1: nav + position + progress bar (only when track has >1 lesson) */}
      {showNav && (
        <div className="flex items-center gap-3 px-1 py-1.5 text-[11px] text-muted-foreground">
          {previous ? (
            <Link
              href={`/challenges/${previous.slug}`}
              className="shrink-0 truncate text-foreground hover:underline"
              title={previous.title}
            >
              ← {previous.title}
            </Link>
          ) : (
            <span className="shrink-0 opacity-40">← Start of track</span>
          )}
          <div className="flex flex-1 items-center gap-2 min-w-0">
            <span className="shrink-0 whitespace-nowrap font-medium text-foreground">
              Lesson {position} / {total}
            </span>
            <div
              role="progressbar"
              aria-valuenow={position}
              aria-valuemin={1}
              aria-valuemax={total}
              aria-label={`Lesson ${position} of ${total}`}
              className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted"
            >
              <div
                className="h-full bg-primary transition-[width] duration-300"
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
          {next ? (
            <Link
              href={`/challenges/${next.slug}`}
              className="shrink-0 truncate text-right text-foreground hover:underline"
              title={next.title}
            >
              {next.title} →
            </Link>
          ) : (
            <span className="shrink-0 opacity-40">End of track →</span>
          )}
        </div>
      )}

      {/* Row 2: module + title */}
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 px-1 pb-1 pt-0.5">
        <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
          {moduleTitle}
        </p>
        <h1 className="text-lg font-semibold leading-tight lg:text-xl">
          {challengeTitle}
        </h1>
      </div>

      {/* Row 3: scenario + More toggle */}
      <div className="flex items-start gap-2 px-1 pb-2">
        <p
          className={
            expanded
              ? "flex-1 text-sm leading-relaxed text-foreground"
              : "flex-1 truncate text-sm leading-relaxed text-muted-foreground"
          }
        >
          {scenario}
        </p>
        <button
          type="button"
          onClick={toggleExpanded}
          className="shrink-0 rounded-md border border-border px-2 py-0.5 text-[11px] font-medium text-foreground hover:bg-muted"
          aria-expanded={expanded}
        >
          {expanded ? "Less ↑" : "More ↓"}
        </button>
      </div>

      {/* Expanded body: goal callout + full instructions */}
      {expanded && (
        <div className="space-y-3 border-t border-border bg-muted/10 px-3 py-3">
          <div className="rounded-md border-l-4 border-primary bg-muted/40 px-3 py-2 text-sm leading-relaxed">
            <span className="font-semibold">Your goal: </span>
            {learnerGoal}
          </div>
          {instructions?.trim() && (
            <div className="rounded-md border border-border bg-background px-3 py-2">
              <Markdown>{instructions}</Markdown>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
