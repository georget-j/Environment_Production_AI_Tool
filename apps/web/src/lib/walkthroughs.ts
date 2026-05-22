/**
 * Per-lesson walkthroughs. A walkthrough is a sequence of (caption, lines[])
 * pairs that annotate the lesson's Example code. Rendered above the editor
 * by <LessonWalkthrough>. Add an entry here and it shows up on that lesson;
 * absent entries fall through to the existing layout.
 *
 * Authored by hand for now — one mode-pilot to validate the pattern.
 */

import type { WalkthroughStep } from "@/components/lesson-walkthrough";

type WalkthroughEntry = {
  /** The code shown in the left pane. Usually the lesson's `code` field
   *  (predict mode) or the Example block from instructions. */
  code: string;
  steps: WalkthroughStep[];
};

export const WALKTHROUGHS: Record<string, WalkthroughEntry> = {
  "quant-02-creating-arrays": {
    code: [
      "import numpy as np",
      "# A literal list — known coupon rates on three bonds.",
      "coupons = np.array([0.025, 0.032, 0.041])",
      "# Pre-allocated buffer for tomorrow's signals.",
      "signals = np.zeros(252)",
      "# Evenly-spaced strikes for an IV surface — 80% to 120% of spot.",
      "strikes = np.linspace(80, 120, 5)",
      "print(coupons, signals[:3], strikes, sep=' | ')",
    ].join("\n"),
    steps: [
      {
        caption:
          "Import numpy as `np` — the only sensible alias; every quant codebase uses it.",
        lines: [1],
      },
      {
        caption:
          "`np.array([...])` lifts a Python list into a fixed-size, contiguous numeric array. Use this when you already have the values in hand — here, three known coupon rates.",
        lines: [2, 3],
      },
      {
        caption:
          "`np.zeros(n)` pre-allocates a vector of `n` zeros. Use this as a *buffer* — somewhere to drop values you'll fill in later (e.g., tomorrow's daily signals across 252 trading days).",
        lines: [4, 5],
      },
      {
        caption:
          "`np.linspace(start, stop, n)` returns `n` evenly-spaced points *including both endpoints*. Use this for grids: strikes for an IV surface, parameter sweeps, plot x-axes.",
        lines: [6, 7],
      },
      {
        caption:
          "Print all three so you can see their shapes side-by-side. The `sep=' | '` separator just keeps the output readable. In the next stage you'll write two of these constructors yourself from scratch.",
        lines: [8],
      },
    ],
  },
  "quant-03-broadcasting-basics": {
    code: [
      "import numpy as np",
      "raw = np.full((4, 3), 0.012)",
      "rf = np.array([0.0001, 0.0001, 0.0002])",
      "excess = raw - rf",
      "print(excess[0])",
    ].join("\n"),
    steps: [
      {
        caption:
          "Import numpy. Standard alias is `np` — every quant codebase uses it.",
        lines: [1],
      },
      {
        caption:
          "Build a 4×3 matrix where every cell is 0.012. Think of it as 4 positions × 3 days of raw daily returns — all the same number for this demo.",
        lines: [2],
      },
      {
        caption:
          "Build a length-3 vector — the risk-free rate per day. Different from the matrix shape: `(3,)` not `(4, 3)`.",
        lines: [3],
      },
      {
        caption:
          "Subtract the (3,) vector from the (4, 3) matrix. Broadcasting silently stretches the vector down all 4 rows. No loop, no copies — one C call.",
        lines: [4],
      },
      {
        caption:
          "Print the first row of `excess` — all 4 positions on day-0, less day-0's risk-free rate. Now you predict what numpy actually prints.",
        lines: [5],
      },
    ],
  },
};
