"use client";

import Link from "next/link";
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
 * Compact strip at the top of a lesson page. Title + module + scenario,
 * nothing else. The Concept / Example / action verb that used to live
 * here have moved into the LessonStages wizard (Example stage for
 * lessons with a walkthrough; Approach stage otherwise), so the page
 * frame is now a thin band and the wizard owns the screen.
 *
 * `learnerGoal` and `instructions` are still received for prop-shape
 * compatibility but no longer rendered here — the wizard reads them.
 */
export function LessonContextStrip({
  challengeSlug: _challengeSlug,
  moduleTitle,
  challengeTitle,
  scenario,
  learnerGoal: _learnerGoal,
  instructions: _instructions,
  previous,
  next,
  position,
  total,
}: Props) {
  void _challengeSlug;
  void _learnerGoal;
  void _instructions;
  const showNav = total > 1;
  const pct =
    total > 1 ? Math.max(0, Math.min(100, (position / total) * 100)) : 0;

  return (
    <section className="flex-none border-b border-border bg-background">
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

      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 px-1 pb-1 pt-0.5">
        <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
          {moduleTitle}
        </p>
        <h1 className="text-base font-semibold leading-tight sm:text-lg lg:text-xl">
          {challengeTitle}
        </h1>
      </div>

      <div className="px-1 pb-2">
        <p className="text-[12px] leading-snug text-foreground sm:text-[13px] lg:text-sm lg:leading-relaxed">
          {scenario}
        </p>
      </div>
    </section>
  );
}
