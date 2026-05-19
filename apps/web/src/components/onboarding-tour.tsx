"use client";

import { useEffect, useLayoutEffect, useState } from "react";

const STORAGE_KEY = "prodready:onboarded";

type Step = {
  /** CSS selector for the element this step is pointing at. Optional —
   * if missing or the element isn't found, the bubble centers itself. */
  targetSelector?: string;
  title: string;
  body: string;
  /** Hint about preferred placement; falls back to "below" if no room. */
  placement?: "above" | "below";
};

const STEPS: Step[] = [
  {
    title: "Welcome to your first challenge",
    body: "Each challenge has a scenario (what's broken in this fake company) and a goal (what you have to make true). Read those at the top of the page first.",
  },
  {
    targetSelector: "[data-onboarding='tests-panel']",
    title: "These are the tests we'll run",
    body: "We've written a fixed set of test cases. Each describes — in plain English — what your code needs to do. Pass them all and the challenge is done.",
    placement: "below",
  },
  {
    targetSelector: "[data-onboarding='workspace']",
    title: "This is your workspace",
    body: "Unlocked files are yours to edit. 🔒 Locked files are context the tests need. Your edits save automatically as you type.",
    placement: "above",
  },
  {
    targetSelector: "[data-onboarding='run-button']",
    title: "Click Run tests to check your work",
    body: "Python runs entirely inside your browser. The first time it's a ~10-second download — after that, every Run is instant. If something fails, we'll tell you exactly where to look.",
    placement: "above",
  },
  {
    title: "Stuck? The mentor will help",
    body: "Below the workspace there's an AI mentor and an 'I'm stuck — help' button in the result panel. Use them. Asking for help is part of the job.",
  },
];

type BubblePosition = {
  top: number;
  left: number;
  arrow: "top" | "bottom" | "none";
};

export function OnboardingTour() {
  const [active, setActive] = useState(false);
  const [stepIndex, setStepIndex] = useState(0);
  const [position, setPosition] = useState<BubblePosition | null>(null);
  const [targetRect, setTargetRect] = useState<DOMRect | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (window.localStorage.getItem(STORAGE_KEY)) return;
    // Skip on narrow viewports — the tour bubbles assume some horizontal room.
    if (window.innerWidth < 900) return;
    // Wait one frame so target elements exist.
    const id = window.requestAnimationFrame(() => setActive(true));
    return () => window.cancelAnimationFrame(id);
  }, []);

  const step = STEPS[stepIndex];

  useLayoutEffect(() => {
    if (!active || !step) return;

    function computePosition() {
      const bubbleWidth = 360;
      const bubbleEstHeight = 180;
      const margin = 16;

      if (!step.targetSelector) {
        setTargetRect(null);
        setPosition({
          top: window.innerHeight / 2 - bubbleEstHeight / 2,
          left: window.innerWidth / 2 - bubbleWidth / 2,
          arrow: "none",
        });
        return;
      }
      const el = document.querySelector(step.targetSelector);
      if (!(el instanceof HTMLElement)) {
        setTargetRect(null);
        setPosition({
          top: window.innerHeight / 2 - bubbleEstHeight / 2,
          left: window.innerWidth / 2 - bubbleWidth / 2,
          arrow: "none",
        });
        return;
      }
      el.scrollIntoView({ block: "center", behavior: "smooth" });
      const rect = el.getBoundingClientRect();
      setTargetRect(rect);

      const preferBelow = step.placement !== "above";
      const fitsBelow = rect.bottom + bubbleEstHeight + margin < window.innerHeight;
      const placeBelow = preferBelow ? fitsBelow : false || (!preferBelow && !fitsBelow);

      const top = placeBelow ? rect.bottom + margin : rect.top - bubbleEstHeight - margin;
      const left = Math.max(
        margin,
        Math.min(
          window.innerWidth - bubbleWidth - margin,
          rect.left + rect.width / 2 - bubbleWidth / 2,
        ),
      );
      setPosition({ top, left, arrow: placeBelow ? "top" : "bottom" });
    }

    computePosition();
    window.addEventListener("resize", computePosition);
    return () => window.removeEventListener("resize", computePosition);
  }, [active, step, stepIndex]);

  if (!active || !step) return null;

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
    <div className="pointer-events-none fixed inset-0 z-50">
      {/* Dimmer backdrop */}
      <div className="pointer-events-auto absolute inset-0 bg-black/40" onClick={dismiss} />

      {/* Cutout around the target (if any) for emphasis */}
      {targetRect && (
        <div
          className="absolute rounded-md ring-4 ring-yellow-300 ring-offset-2 ring-offset-transparent transition-all"
          style={{
            top: targetRect.top - 4,
            left: targetRect.left - 4,
            width: targetRect.width + 8,
            height: targetRect.height + 8,
          }}
        />
      )}

      {/* Tooltip bubble */}
      {position && (
        <div
          className="pointer-events-auto absolute w-[360px] rounded-lg border border-border bg-white p-5 shadow-xl"
          style={{ top: position.top, left: position.left }}
        >
          <p className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
            Step {stepIndex + 1} of {STEPS.length}
          </p>
          <h3 className="mb-2 text-base font-semibold">{step.title}</h3>
          <p className="mb-4 text-sm leading-relaxed text-muted-foreground">{step.body}</p>
          <div className="flex items-center justify-between">
            <button
              type="button"
              onClick={dismiss}
              className="text-xs text-muted-foreground hover:text-foreground"
            >
              Skip tour
            </button>
            <button
              type="button"
              onClick={next}
              className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90"
            >
              {stepIndex + 1 >= STEPS.length ? "Got it" : "Next →"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
