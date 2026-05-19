"use client";

import { useEffect, useState } from "react";

const STORAGE_KEY = "prodready:onboarded";

type Step = {
  title: string;
  body: string;
};

const STEPS: Step[] = [
  {
    title: "Welcome — this is a coding workspace.",
    body: "Not a lecture. You edit code in the middle, hit Run to test it in your browser, and iterate. The whole loop fits on one page.",
  },
  {
    title: "The mentor on the right gives you hints.",
    body: "Click Hint 1 for a Socratic nudge, Hint 3 for a pseudocode sketch. If you're truly stuck, 'Show me the answer' replaces your code with a working version so you can read the fix.",
  },
  {
    title: "When tests fail, the mentor explains why.",
    body: "Failure cards include 'where to look next' with the file and line number. Click those references to jump straight into the editor at the right spot.",
  },
  {
    title: "Submit when all tests pass.",
    body: "Your edits save automatically as you type. Submit records your win and runs an AI code review.",
  },
];

export function OnboardingTour() {
  const [active, setActive] = useState(false);
  const [stepIndex, setStepIndex] = useState(0);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (window.localStorage.getItem(STORAGE_KEY)) return;
    // Defer one tick so the page renders before the dimmer appears.
    const id = window.setTimeout(() => setActive(true), 200);
    return () => window.clearTimeout(id);
  }, []);

  if (!active) return null;
  const step = STEPS[stepIndex];

  function dismiss() {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, "true");
    }
    setActive(false);
  }

  function next() {
    if (stepIndex + 1 >= STEPS.length) {
      dismiss();
    } else {
      setStepIndex(stepIndex + 1);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-black/40"
        onClick={dismiss}
        aria-hidden="true"
      />
      <div
        role="dialog"
        aria-labelledby="onboarding-title"
        className="relative w-full max-w-md rounded-lg border border-border bg-white p-6 shadow-2xl"
      >
        <p className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
          Quick intro · step {stepIndex + 1} of {STEPS.length}
        </p>
        <h3 id="onboarding-title" className="mb-3 text-lg font-semibold">
          {step.title}
        </h3>
        <p className="mb-5 text-sm leading-relaxed text-muted-foreground">{step.body}</p>
        <div className="flex items-center justify-between">
          <button
            type="button"
            onClick={dismiss}
            className="text-xs text-muted-foreground hover:text-foreground"
          >
            Skip
          </button>
          <div className="flex items-center gap-1">
            {STEPS.map((_, i) => (
              <span
                key={i}
                aria-hidden="true"
                className={
                  i === stepIndex
                    ? "h-1.5 w-4 rounded-full bg-primary"
                    : "h-1.5 w-1.5 rounded-full bg-muted-foreground/30"
                }
              />
            ))}
          </div>
          <button
            type="button"
            onClick={next}
            className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            {stepIndex + 1 >= STEPS.length ? "Got it" : "Next →"}
          </button>
        </div>
      </div>
    </div>
  );
}
