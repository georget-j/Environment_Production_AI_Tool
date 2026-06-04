"use client";

/**
 * Annotated-frames widget (M6).
 *
 * The generic Play-stage renderer used whenever a concept's widget kind
 * doesn't have a bespoke implementation. Each frame is `{caption_md,
 * detail_md?, visual?}`; learners step through them with Back / Next and
 * see the caption + (when present) a code block or ASCII visualisation.
 *
 * This is intentionally simple — the Bret Victor "see the state" principle
 * is preserved as long as the visual changes between frames in a way that
 * makes the underlying mechanic legible. Bespoke widgets can do more
 * elaborate animations later without changing the concept JSON.
 */

import { useState } from "react";
import ReactMarkdown from "react-markdown";

import { Button } from "@/components/ui/button";

export type AnnotatedFrame = {
  /** Required — short narration. Renders as markdown. */
  caption_md: string;
  /** Optional — longer explanation. Renders as markdown below the caption. */
  detail_md?: string;
  /** Optional pre-formatted text or ASCII visualisation rendered in a
   * monospace block above the caption. */
  visual?: string;
  /** Optional fenced-code-block content (typically Python) rendered in a
   * code block above the caption. Used by call-stack / state-machine
   * adapters that want syntax-coloured frames. */
  code?: string;
};

export function AnnotatedFrames({
  title,
  frames,
  onAllStepsViewed,
}: {
  title?: string;
  frames: AnnotatedFrame[];
  onAllStepsViewed?: () => void;
}) {
  const [i, setI] = useState(0);
  const [maxSeen, setMaxSeen] = useState(0);
  const total = frames.length;
  const frame = frames[i];

  function go(next: number) {
    const clamped = Math.max(0, Math.min(total - 1, next));
    setI(clamped);
    if (clamped > maxSeen) {
      const newMax = clamped;
      setMaxSeen(newMax);
      if (newMax === total - 1 && onAllStepsViewed) {
        onAllStepsViewed();
      }
    }
  }

  if (!total) {
    return (
      <div className="rounded-md border border-dashed border-border bg-muted/20 p-4 text-sm text-muted-foreground">
        No frames authored for this concept yet.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {title && (
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {title}
        </p>
      )}

      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>
          Step {i + 1} of {total}
        </span>
        <span>
          {maxSeen + 1} / {total} viewed
        </span>
      </div>

      <div className="rounded-md border border-border bg-background p-4">
        {frame.visual && (
          <pre className="mb-3 overflow-x-auto whitespace-pre rounded-md border border-border bg-muted/40 p-3 font-mono text-xs leading-relaxed">
            {frame.visual}
          </pre>
        )}
        {frame.code && (
          <pre className="mb-3 overflow-x-auto whitespace-pre rounded-md bg-foreground p-3 font-mono text-xs leading-relaxed text-background">
            {frame.code}
          </pre>
        )}
        <div className="prose prose-sm max-w-none prose-p:my-1 prose-code:rounded prose-code:bg-muted prose-code:px-1 prose-code:py-0.5 prose-code:font-mono prose-code:text-[0.88em] prose-code:before:content-none prose-code:after:content-none">
          <ReactMarkdown>{frame.caption_md}</ReactMarkdown>
          {frame.detail_md && <ReactMarkdown>{frame.detail_md}</ReactMarkdown>}
        </div>
      </div>

      <div className="flex items-center justify-between">
        <Button
          size="sm"
          variant="outline"
          onClick={() => go(i - 1)}
          disabled={i === 0}
        >
          ← Back
        </Button>
        <Button size="sm" onClick={() => go(i + 1)} disabled={i === total - 1}>
          {i === total - 1 ? "End of steps" : "Next →"}
        </Button>
      </div>
    </div>
  );
}
