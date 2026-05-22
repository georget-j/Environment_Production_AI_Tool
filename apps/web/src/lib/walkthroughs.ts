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
