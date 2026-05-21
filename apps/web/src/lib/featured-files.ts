/**
 * Per-challenge in-browser runner config.
 *
 * Each challenge declares:
 *  - editable: files the learner can change (shown in Monaco tabs)
 *  - readonly: support files loaded into Pyodide but not editable
 *  - tests:    the test cases that will run when the learner clicks Run.
 *              Each is shown in the 'Tests for this challenge' panel
 *              with a plain-English description so the learner knows
 *              what we're checking *before* hitting Run.
 *  - pytestArgs: the actual pytest target IDs derived from `tests`
 *                (e.g. ["tests/test_orders.py::test_..."]).
 *  - mode: 'pyodide' (Monaco + pytest) or 'reading' (read-only preview)
 *
 * Files are fetched from raw.githubusercontent.com on `repo_branch`
 * (the template repo holds canonical content), but the learner never
 * leaves the page.
 */

export type TestCase = {
  /** pytest node id, e.g. tests/test_orders.py::test_compute_total_without_coupon */
  id: string;
  /** Display name shown in the panel. Defaults to the part after :: */
  label?: string;
  /** Plain-English description: what does this test prove? */
  description: string;
};

/**
 * Python Basics 'predict' lesson: show code, learner types what they
 * expect stdout to be, JS compares. No Pyodide execution.
 */
export type PredictLessonConfig = {
  mode: "predict";
  /** The Python snippet shown read-only to the learner. */
  code: string;
  /** Exact stdout the snippet would print (whitespace-trimmed compare). */
  expected_stdout: string;
  /** Short hint shown above the input box (e.g. "Type the number you expect"). */
  prompt?: string;
};

/**
 * Python Basics 'fillblank' lesson: Monaco editor with `___` placeholders.
 * Learner replaces the blanks, clicks Run, Pyodide executes the file,
 * stdout is compared to `expected_stdout`.
 */
export type FillBlankLessonConfig = {
  mode: "fillblank";
  /** Initial editor content. Use `___` (triple underscore) where the learner edits. */
  template: string;
  /** Exact stdout the finished code should print (whitespace-trimmed compare). */
  expected_stdout: string;
  /** One-line hint shown under the editor. */
  hint?: string;
};

/**
 * Quant track 'cscript' lesson: editable C in JSCPP. Same shape as
 * fillblank but runs through the C interpreter instead of Pyodide.
 * Compares stdout to `expected_stdout` whitespace-trimmed.
 */
export type CScriptLessonConfig = {
  mode: "cscript";
  /** Initial editor content. Use `___` for blanks. */
  template: string;
  /** Exact stdout the finished code should print (whitespace-trimmed compare). */
  expected_stdout: string;
  /** One-line hint shown under the editor. */
  hint?: string;
};

/**
 * Quant track 'matplot' lesson: Monaco + Pyodide + inline matplotlib SVG.
 * Pass criterion is "code runs cleanly AND a non-empty figure was drawn AND
 * (if expected_stdout is set) stdout matches". No pixel-diff: too brittle.
 */
/**
 * Quant track 'cwasm' lesson: read-only `.c` source preview + a Run button
 * that loads a pre-built WASM module from /wasm/quant/<slug>.js and
 * captures its stdout. Pass criterion: stdout matches `expected_stdout`
 * loosely (substring match — timings vary). Use when picoc-js can't run
 * the lesson (deep recursion, perf benchmarks needing real -O3 code).
 */
export type CWasmLessonConfig = {
  mode: "cwasm";
  /** The .c source the learner reads (rendered with syntax highlight). */
  source: string;
  /** Slug under /wasm/quant/ — must match an entry in c-wasm.ts. */
  wasm_demo:
    | "ring_buffer"
    | "struct_layout"
    | "lob_node"
    | "cache_locality"
    | "manual_vs_libc_strlen"
    | "printf_internals";
  /** Substring expected in stdout for the lesson to pass. */
  expected_stdout_contains: string;
  /** One-line hint shown above the demo. */
  hint?: string;
};

export type MatplotLessonConfig = {
  mode: "matplot";
  /** Initial editor content. Use `___` for blanks if you want a fill-in shape. */
  template: string;
  /** Optional exact stdout (e.g. a printed Sharpe ratio). */
  expected_stdout?: string;
  /** One-line hint shown under the editor. */
  hint?: string;
};

export type ChallengeRunnerConfig =
  | {
      mode: "pyodide";
      editable: string[];
      readonly: string[];
      tests: TestCase[];
    }
  | {
      mode: "reading";
      readonly: string[];
    }
  | PredictLessonConfig
  | FillBlankLessonConfig
  | MatplotLessonConfig
  | CScriptLessonConfig
  | CWasmLessonConfig;

import { PYTHON_BASICS_CONFIG } from "@/lib/python-basics-config.generated";
import { QUANT_CONFIG } from "@/lib/quant-config.generated";

export const CHALLENGE_CONFIG: Record<string, ChallengeRunnerConfig> = {
  ...PYTHON_BASICS_CONFIG,
  ...QUANT_CONFIG,

  "fastapi-commerce-run-and-explore": {
    mode: "reading",
    readonly: ["app/main.py", "app/orders.py", "tests/test_orders.py"],
  },

  "fastapi-commerce-fix-failing-test": {
    mode: "pyodide",
    editable: ["app/orders.py"],
    readonly: [
      "app/__init__.py",
      "app/coupons.py",
      "app/models.py",
      "tests/__init__.py",
      "tests/conftest.py",
      "tests/test_orders.py",
    ],
    tests: [
      {
        id: "tests/test_orders.py::test_compute_total_without_coupon",
        description:
          "1 × £12 notebook + 2 × £9.50 coffee mugs should total £33.50.",
      },
      {
        id: "tests/test_orders.py::test_compute_total_with_valid_coupon",
        description:
          "A valid WELCOME10 coupon should knock 10% off the subtotal.",
      },
      {
        id: "tests/test_orders.py::test_compute_total_create_order_persists_total",
        description:
          "Creating an order persists the right total to the store (the canonical failing test).",
      },
      {
        id: "tests/test_orders.py::test_invalid_quantity_rejected",
        description: "Quantity = 0 should raise ValueError.",
      },
    ],
  },

  "fastapi-commerce-reject-invalid-coupons": {
    mode: "pyodide",
    editable: ["app/coupons.py", "app/main.py", "tests/test_coupons.py"],
    readonly: [
      "app/__init__.py",
      "app/models.py",
      "app/orders.py",
      "tests/__init__.py",
      "tests/conftest.py",
      "tests/test_orders.py",
    ],
    tests: [
      {
        id: "tests/test_coupons.py::test_valid_code_is_recognised",
        description: "WELCOME10 is a known code; is_valid() returns True.",
      },
      {
        id: "tests/test_coupons.py::test_none_is_invalid",
        description: "None / empty input is not a valid coupon.",
      },
      {
        id: "tests/test_orders.py::test_compute_total_without_coupon",
        description: "Untouched order maths still works after your changes.",
      },
      {
        id: "tests/test_orders.py::test_compute_total_with_valid_coupon",
        description: "WELCOME10 still applies the correct discount.",
      },
    ],
  },
};
