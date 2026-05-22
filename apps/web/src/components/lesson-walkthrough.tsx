"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";

export type WalkthroughStep = {
  /** One-line plain-text caption shown in the right pane. */
  caption: string;
  /** 1-based line numbers in the code to highlight when this step is active. */
  lines: number[];
};

type Props = {
  code: string;
  steps: WalkthroughStep[];
  /** DOM id of the element to scroll to when "Now you try" is clicked.
   *  Pass an empty string when used inside a stage wizard — the wizard's
   *  own "Next →" handles the transition and the walkthrough should not
   *  render its own terminal CTA. */
  scrollTargetId: string;
};

/**
 * Two-pane walkthrough that sits above the editor on lessons that have
 * a worked Example. Left: read-only code with per-line highlight tied to
 * the active step. Right: numbered clickable steps. Final step swaps the
 * "Next step →" button for "Now you try ↓" which scrolls to the editor.
 *
 * Intentionally lightweight: a `<pre>` block (not Monaco) keeps the
 * bundle small and the highlight CSS trivial.
 */
export function LessonWalkthrough({ code, steps, scrollTargetId }: Props) {
  const [active, setActive] = useState(0);
  const [completed, setCompleted] = useState(false);
  const activeLines = new Set(steps[active]?.lines ?? []);
  const codeLines = code.split("\n");

  const onContinue = () => {
    if (active < steps.length - 1) {
      setActive((a) => a + 1);
      return;
    }
    setCompleted(true);
    const el = document.getElementById(scrollTargetId);
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const isLast = active === steps.length - 1;

  return (
    <section className="flex flex-col rounded-lg border border-primary/30 bg-background">
      <header className="flex flex-none flex-wrap items-center justify-between gap-2 border-b border-primary/20 px-4 py-2">
        <p className="text-sm font-semibold">
          Walk the example first
          <span className="ml-2 text-xs font-normal text-muted-foreground">
            Step {active + 1} of {steps.length}
          </span>
        </p>
        <p className="text-[11px] text-muted-foreground">
          Click a step to highlight its lines.
        </p>
      </header>
      {/* Natural-flow grid: on lg+ panes sit side-by-side (left can
       * stick); on mobile they stack vertically and the wizard's
       * stage container handles overflow scroll. */}
      <div className="grid gap-3 p-3 lg:grid-cols-[minmax(0,_1.1fr)_minmax(0,_0.9fr)]">
        {/* Left: read-only annotated code. Sticks to the top of the
         * scrollable stage on lg+ so the learner never loses sight
         * of the snippet as they read through the steps. */}
        <div className="max-h-[30vh] overflow-auto rounded-md border border-border bg-muted/30 p-3 font-mono text-[11px] leading-[1.6] sm:text-[12px] lg:sticky lg:top-0 lg:max-h-[calc(100dvh-12rem)] lg:text-[13px] lg:leading-[1.7]">
          {codeLines.map((line, i) => {
            const lineNum = i + 1;
            const isActive = activeLines.has(lineNum);
            return (
              <div
                key={i}
                className={cn(
                  "-mx-1 rounded px-1 transition-colors",
                  isActive ? "bg-primary/15" : "",
                )}
              >
                <span className="mr-3 inline-block w-5 select-none text-right text-muted-foreground/60">
                  {lineNum}
                </span>
                <span className="whitespace-pre">{line || " "}</span>
              </div>
            );
          })}
        </div>

        {/* Right: numbered clickable steps. Natural height — the
         * stage container (or this pane via lg:max-h) handles the
         * scroll. */}
        <div className="flex flex-col gap-2 pr-1">
          <ol className="space-y-2">
            {steps.map((s, i) => {
              const isCurrent = i === active;
              const isPast = i < active || completed;
              return (
                <li key={i}>
                  <button
                    type="button"
                    onClick={() => {
                      setActive(i);
                      setCompleted(false);
                    }}
                    className={cn(
                      "flex w-full items-start gap-3 rounded-md border p-3 text-left text-sm leading-relaxed",
                      isCurrent
                        ? "border-primary bg-primary/5 ring-1 ring-primary/30"
                        : "border-border bg-background hover:bg-muted/40",
                    )}
                  >
                    <span
                      className={cn(
                        "mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[11px] font-bold",
                        isCurrent
                          ? "bg-primary text-primary-foreground"
                          : isPast
                            ? "bg-green-600 text-white"
                            : "border border-border text-muted-foreground",
                      )}
                    >
                      {isPast && !isCurrent ? "✓" : i + 1}
                    </span>
                    <span
                      className={cn(
                        !isCurrent && !isPast && "text-muted-foreground",
                      )}
                    >
                      {s.caption}
                    </span>
                  </button>
                </li>
              );
            })}
          </ol>
          {/* Hide the terminal CTA when there's no scroll target (the wizard
           * owns the stage transition). On non-terminal steps, always show
           * "Next step →" so the learner can advance one annotation at a time. */}
          {(!isLast || scrollTargetId) && (
            <button
              type="button"
              onClick={onContinue}
              className="w-full rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
            >
              {isLast ? "Now you try ↓" : "Next step →"}
            </button>
          )}
        </div>
      </div>
    </section>
  );
}
