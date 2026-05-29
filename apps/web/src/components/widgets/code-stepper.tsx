"use client";

/**
 * code-stepper — Bret Victor's "See the State" widget.
 *
 * Renders code on the left with the current step's line highlighted, and
 * a state panel on the right showing variable bindings + heap objects as
 * the learner steps forward and back. The captioned step below the panels
 * narrates each transition.
 *
 * Config shape (drawn from concepts.play_widget_json):
 *
 *   {
 *     title?: string,
 *     code: string,                       // multi-line source
 *     steps: Array<{
 *       line: number,                     // 1-indexed; current highlight
 *       bindings: Record<string, string>, // var name → human-readable ref
 *       heap?: Array<{ id: string; value: string }>,
 *       caption: string,
 *     }>,
 *   }
 *
 * The widget is purely declarative — no code execution. Authors describe
 * the state at each step; the widget animates between them.
 */

import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";

type Step = {
  line: number;
  bindings: Record<string, string>;
  heap?: Array<{ id: string; value: string }>;
  caption: string;
};

type Config = {
  title?: string;
  code: string;
  steps: Step[];
};

export function CodeStepper({
  config,
  onAllStepsViewed,
}: {
  config: Config;
  // Fires once the learner has stepped through the last step at least once.
  // The unit shell uses this to enable the "Mark Play complete" button.
  onAllStepsViewed?: () => void;
}) {
  const lines = useMemo(() => config.code.split("\n"), [config.code]);
  const steps = config.steps ?? [];
  const [idx, setIdx] = useState(0);
  const [viewedLast, setViewedLast] = useState(false);

  const step = steps[idx];

  useEffect(() => {
    if (idx === steps.length - 1 && !viewedLast) {
      setViewedLast(true);
      onAllStepsViewed?.();
    }
  }, [idx, steps.length, viewedLast, onAllStepsViewed]);

  if (steps.length === 0 || !step) {
    return (
      <p className="text-sm text-muted-foreground">
        No steps configured for this widget.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {config.title && <p className="text-sm font-semibold">{config.title}</p>}

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        {/* Code pane — current line highlighted. */}
        <pre className="overflow-auto rounded-md border border-border bg-muted/30 p-3 font-mono text-xs leading-relaxed">
          {lines.map((src, i) => {
            const lineNumber = i + 1;
            const active = lineNumber === step.line;
            return (
              <div
                key={i}
                className={`grid grid-cols-[2em_minmax(0,1fr)] rounded ${
                  active ? "bg-amber-100 text-amber-900" : ""
                }`}
              >
                <span className="select-none text-right text-muted-foreground/60">
                  {lineNumber}
                </span>
                <span className="pl-2 whitespace-pre-wrap break-words">
                  {src || " "}
                </span>
              </div>
            );
          })}
        </pre>

        {/* State pane — names + heap snapshot. */}
        <div className="flex flex-col gap-3 rounded-md border border-border bg-background p-3 text-xs">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
              Names → values
            </p>
            {Object.keys(step.bindings).length === 0 ? (
              <p className="mt-1 italic text-muted-foreground">
                (no names bound yet)
              </p>
            ) : (
              <ul className="mt-1 flex flex-col gap-1 font-mono">
                {Object.entries(step.bindings).map(([name, ref]) => (
                  <li key={name} className="flex items-center gap-2">
                    <span className="rounded bg-muted px-1.5 py-0.5">
                      {name}
                    </span>
                    <span className="text-muted-foreground">{ref}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {step.heap && step.heap.length > 0 && (
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                Heap (objects)
              </p>
              <ul className="mt-1 flex flex-col gap-1 font-mono">
                {step.heap.map((obj) => (
                  <li key={obj.id} className="flex items-center gap-2">
                    <span className="rounded bg-blue-50 px-1.5 py-0.5 text-blue-900">
                      {obj.id}
                    </span>
                    <span className="text-muted-foreground">{obj.value}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>

      <p className="rounded-md border border-blue-200 bg-blue-50 p-3 text-sm text-blue-900">
        <span className="font-semibold">
          Step {idx + 1} of {steps.length}:
        </span>{" "}
        {step.caption}
      </p>

      <div className="flex items-center justify-between gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setIdx((i) => Math.max(0, i - 1))}
          disabled={idx === 0}
        >
          ← Back
        </Button>
        <span className="text-xs text-muted-foreground">
          {viewedLast ? "All steps viewed ✓" : "Step through to unlock"}
        </span>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setIdx((i) => Math.min(steps.length - 1, i + 1))}
          disabled={idx === steps.length - 1}
        >
          Next →
        </Button>
      </div>
    </div>
  );
}
