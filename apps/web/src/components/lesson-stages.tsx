"use client";

import { Fragment, useState, type ReactNode } from "react";
import { cn } from "@/lib/utils";

type StageId = "example" | "approach" | "solve";

type Stage = {
  id: StageId;
  label: string;
  content: ReactNode;
};

type Props = {
  /** The Example walkthrough. Omit for lessons that don't have a
   *  separable worked example (predict mode, debug/skeleton/apifetch). */
  example?: ReactNode;
  approach: ReactNode;
  solve: ReactNode;
};

/**
 * Three-stage wizard for a lesson page. Each stage fills the workspace
 * area; only one is visible at a time. A breadcrumb at the top lets the
 * learner jump back/forward; a "Next →" button advances. The container
 * is height-locked to its parent, so the page never needs to scroll —
 * within a stage, content scrolls internally if it exceeds the viewport.
 */
export function LessonStages({ example, approach, solve }: Props) {
  const stages: Stage[] = [
    ...(example
      ? [{ id: "example" as StageId, label: "Example", content: example }]
      : []),
    { id: "approach", label: "Approach", content: approach },
    { id: "solve", label: "Solve", content: solve },
  ];

  const [activeIdx, setActiveIdx] = useState(0);
  const active = stages[activeIdx];
  const isLast = activeIdx === stages.length - 1;
  const nextStage = stages[activeIdx + 1];

  return (
    <div className="flex h-full min-h-0 flex-col">
      {/* Breadcrumb: clickable stage chips. */}
      <nav className="flex flex-none items-center gap-2 border-b border-border bg-muted/20 px-2 py-2">
        {stages.map((s, i) => (
          <Fragment key={s.id}>
            {i > 0 && (
              <span aria-hidden="true" className="text-muted-foreground/40">
                ▸
              </span>
            )}
            <button
              type="button"
              onClick={() => setActiveIdx(i)}
              className={cn(
                "rounded-md px-3 py-1 text-xs font-medium",
                i === activeIdx
                  ? "bg-primary text-primary-foreground"
                  : i < activeIdx
                    ? "text-foreground hover:bg-muted"
                    : "text-muted-foreground hover:text-foreground",
              )}
              aria-current={i === activeIdx ? "step" : undefined}
            >
              <span className="mr-1.5 inline-flex h-4 w-4 items-center justify-center rounded-full text-[10px] font-bold">
                {i < activeIdx ? "✓" : i + 1}
              </span>
              {s.label}
            </button>
          </Fragment>
        ))}
      </nav>

      {/* Active stage area. Each rendered stage gets full height; inner
       * scroll is the responsibility of the stage's own content (so the
       * Solve stage's tests panel can scroll separately from the editor). */}
      <div
        key={active.id}
        className="flex min-h-0 flex-1 flex-col overflow-hidden"
      >
        {active.content}
      </div>

      {/* Next button at the bottom-right; absent on the terminal Solve stage. */}
      {!isLast && nextStage && (
        <div className="flex flex-none items-center justify-between border-t border-border bg-muted/10 px-3 py-2">
          <p className="text-xs text-muted-foreground">
            When you&apos;ve digested this, advance to{" "}
            <span className="font-medium text-foreground">
              {nextStage.label}
            </span>
            .
          </p>
          <button
            type="button"
            onClick={() => setActiveIdx(activeIdx + 1)}
            className="rounded-md bg-primary px-4 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            Next: {nextStage.label} →
          </button>
        </div>
      )}
    </div>
  );
}
