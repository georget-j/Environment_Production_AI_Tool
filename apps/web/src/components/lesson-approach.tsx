"use client";

import { useEffect, useState, type ReactNode } from "react";

export type ApproachMode =
  | "pyodide-debug"
  | "pyodide-skeleton"
  | "pyodide-apifetch"
  | "pyodide-other"
  | "fillblank"
  | "predict"
  | "matplot"
  | "cscript"
  | "cwasm";

type Props = {
  mode: ApproachMode;
  challengeSlug: string;
  learnerGoal: string;
};

const STEPS: Record<ApproachMode, string[]> = {
  "pyodide-debug": [
    "Read `solution.py` and its docstring — it states what the code is *supposed* to do.",
    "Open `tests/test_solution.py` — each assertion is a specific claim the bug breaks.",
    "Click **Run tests** — note which test fails and what `expected` vs `got` says.",
    "Find the bug in `solution.py` and fix it.",
    "Re-run. The mentor on the right gives a Socratic hint if you're stuck.",
  ],
  "pyodide-skeleton": [
    "Open `tests/test_solution.py` — each test tells you what your function must return on given inputs.",
    "Read the docstring on the `raise NotImplementedError` function — it's the contract.",
    "Implement the function body in `solution.py`.",
    "Click **Run tests**. Iterate until green.",
  ],
  "pyodide-apifetch": [
    "Open `mock_api.py` — it lists the available endpoints and the `Response` object shape.",
    "Decide which endpoint(s) you need to call to satisfy the tests.",
    "In `solution.py`, call them via `mock_api.get(...)` and parse the JSON.",
    "Click **Run tests**.",
  ],
  "pyodide-other": [
    "Read the editable file's docstring — it states the goal.",
    "Read the read-only files (tests, support code) for the contract you must satisfy.",
    "Edit, then click **Run tests**.",
  ],
  fillblank: [
    "Read the code around the `___` — what role is that token playing?",
    "Type the missing piece in place of `___`.",
    "Click **Run**. If output matches, you advance automatically.",
  ],
  predict: [
    "Read the code line by line; trace what each variable holds.",
    "Predict the printed output mentally — don't run it yet.",
    "Type your prediction in the answer box and click **Check**.",
  ],
  matplot: [
    "Read the template — what plot shape is wanted.",
    "Fill in the matplotlib call.",
    "Click **Run** and check the rendered plot matches the description.",
  ],
  cscript: [
    "Read the C code around the `___` — what role is that token playing?",
    "Type the missing piece in place of `___`.",
    "Click **Run**.",
  ],
  cwasm: [
    "Read the C source on the right — it's a demo, not editable.",
    "Click **Run** to load the pre-built WebAssembly module and see its output.",
  ],
};

const HEADINGS: Record<ApproachMode, string> = {
  "pyodide-debug": "How to approach this debug task",
  "pyodide-skeleton": "How to approach this implementation",
  "pyodide-apifetch": "How to approach this API client",
  "pyodide-other": "How to approach this",
  fillblank: "How to approach this",
  predict: "How to approach this",
  matplot: "How to approach this",
  cscript: "How to approach this",
  cwasm: "How to approach this",
};

function storageKey(slug: string): string {
  return `prodready:approach-hidden:${slug}`;
}

/**
 * "How to approach this" card. Sits above the editor, expanded by default,
 * giving a mode-specific 3–5 step plan so the learner isn't dropped into
 * the editor without a strategy. Collapsed state persists per challenge
 * slug so a learner can hide it once they're familiar with that lesson
 * shape, without losing it for other lessons.
 */
export function LessonApproach({ mode, challengeSlug, learnerGoal }: Props) {
  const [open, setOpen] = useState(true);
  useEffect(() => {
    if (typeof window === "undefined") return;
    const stored = window.localStorage.getItem(storageKey(challengeSlug));
    if (stored === "true") setOpen(false);
  }, [challengeSlug]);

  const toggle = () => {
    setOpen((prev) => {
      const next = !prev;
      if (typeof window !== "undefined") {
        window.localStorage.setItem(
          storageKey(challengeSlug),
          next ? "false" : "true",
        );
      }
      return next;
    });
  };

  const steps = STEPS[mode];
  const heading = HEADINGS[mode];

  return (
    <section className="rounded-lg border border-primary/30 bg-primary/5">
      <button
        type="button"
        onClick={toggle}
        className="flex w-full items-center justify-between px-4 py-2 text-left"
        aria-expanded={open}
      >
        <span className="flex items-center gap-2 text-sm font-semibold">
          <span aria-hidden="true" className="text-primary">
            {open ? "▾" : "▸"}
          </span>
          {heading}
        </span>
        <span className="text-[11px] text-muted-foreground">
          {open ? "hide" : "show"}
        </span>
      </button>
      {open && (
        <div className="space-y-3 border-t border-primary/20 px-4 py-3 text-sm">
          <p>
            <span className="font-semibold">Goal: </span>
            {learnerGoal}
          </p>
          <ol className="list-decimal space-y-1.5 pl-5 text-foreground/90">
            {steps.map((s, i) => (
              <li key={i}>
                <Markdown>{s}</Markdown>
              </li>
            ))}
          </ol>
        </div>
      )}
    </section>
  );
}

/**
 * Tiny markdown renderer for inline backtick code + bold + italic only.
 * We don't pull in react-markdown here because the steps are short and
 * we want zero runtime cost on the most-visited card on the page.
 */
function Markdown({ children }: { children: string }) {
  const parts: ReactNode[] = [];
  const buf = children;
  let key = 0;

  // Process: **bold**, *italic*, `code` — in that order, non-overlapping.
  const tokenRe = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  while ((match = tokenRe.exec(buf)) !== null) {
    if (match.index > lastIndex) {
      parts.push(buf.slice(lastIndex, match.index));
    }
    const token = match[0];
    if (token.startsWith("**")) {
      parts.push(<strong key={key++}>{token.slice(2, -2)}</strong>);
    } else if (token.startsWith("`")) {
      parts.push(
        <code
          key={key++}
          className="rounded bg-muted px-1 py-0.5 font-mono text-[12px]"
        >
          {token.slice(1, -1)}
        </code>,
      );
    } else {
      parts.push(<em key={key++}>{token.slice(1, -1)}</em>);
    }
    lastIndex = match.index + token.length;
  }
  if (lastIndex < buf.length) parts.push(buf.slice(lastIndex));
  return <>{parts}</>;
}
