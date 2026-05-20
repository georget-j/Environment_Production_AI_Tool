"use client";

import Link from "next/link";
import type { ChallengeNavRef } from "@/lib/api";

type Props = {
  previous: ChallengeNavRef | null;
  next: ChallengeNavRef | null;
  position: number;
  total: number;
};

export function LessonNav({ previous, next, position, total }: Props) {
  if (total <= 1) return null;
  return (
    <nav
      aria-label="Lesson navigation"
      className="flex items-center justify-between gap-3 rounded-md border border-border bg-muted/20 px-4 py-2 text-xs text-muted-foreground"
    >
      {previous ? (
        <Link
          href={`/challenges/${previous.slug}`}
          className="flex items-center gap-1 truncate text-foreground hover:underline"
        >
          <span aria-hidden="true">←</span>
          <span className="truncate">{previous.title}</span>
        </Link>
      ) : (
        <span className="opacity-40">← Start of track</span>
      )}

      <span className="shrink-0 whitespace-nowrap font-medium text-foreground">
        Lesson {position} of {total}
      </span>

      {next ? (
        <Link
          href={`/challenges/${next.slug}`}
          className="flex items-center gap-1 justify-end truncate text-foreground hover:underline"
        >
          <span className="truncate">{next.title}</span>
          <span aria-hidden="true">→</span>
        </Link>
      ) : (
        <span className="opacity-40">End of track →</span>
      )}
    </nav>
  );
}
