"use client";

/**
 * Apply-stage Pyodide runner (M2).
 *
 * Renders the concept's apply_skeleton as a minimal "edit-and-run" lesson:
 *   - instructions_md above
 *   - textarea pre-filled with starter_code (no Monaco — small lessons)
 *   - Run button → writes solution.py + hidden_test.py to Pyodide, runs
 *     pytest, parses pass/fail
 *   - Pass → marks the Apply stage complete via the parent callback
 *
 * Deliberately simpler than the challenge runner. The concept's Apply is
 * meant to be a single quick exercise that proves the learner can use the
 * concept once on something runnable — not a full lesson.
 */

import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";

import { Button } from "@/components/ui/button";
import {
  detectUnsupportedFeatures,
  ensurePytest,
  getPyodide,
  runPytest,
  type PytestResult,
} from "@/lib/pyodide";

export type ApplySkeleton = {
  instructions_md: string;
  starter_code: string;
  hidden_test: string;
};

export function ConceptApplyRunner({
  skeleton,
  onPass,
}: {
  skeleton: ApplySkeleton;
  onPass: () => void | Promise<void>;
}) {
  const [code, setCode] = useState(skeleton.starter_code);
  const [running, setRunning] = useState(false);
  const [pyodideReady, setPyodideReady] = useState(false);
  const [result, setResult] = useState<PytestResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [passed, setPassed] = useState(false);

  // Pre-warm Pyodide so the first Run isn't an eye-watering wait.
  useEffect(() => {
    void (async () => {
      try {
        await getPyodide();
        await ensurePytest();
        setPyodideReady(true);
      } catch (exc) {
        setError(
          exc instanceof Error ? exc.message : "Failed to boot Pyodide.",
        );
      }
    })();
  }, []);

  async function run() {
    setError(null);
    setResult(null);
    const guard = detectUnsupportedFeatures(code);
    if (guard) {
      setError(guard);
      return;
    }
    setRunning(true);
    try {
      const files: Record<string, string> = {
        "solution.py": code,
        "test_apply.py": skeleton.hidden_test,
      };
      const res = await runPytest(files, ["-q", "--tb=short", "test_apply.py"]);
      setResult(res);
      const allPassed =
        res.exitCode === 0 && res.tests.every((t) => t.status === "passed");
      if (allPassed && !passed) {
        setPassed(true);
        await onPass();
      }
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Run failed.");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <article className="prose prose-sm max-w-none prose-p:my-1 prose-code:rounded prose-code:bg-muted prose-code:px-1 prose-code:font-mono prose-code:text-[0.88em] prose-code:before:content-none prose-code:after:content-none">
        <ReactMarkdown>{skeleton.instructions_md}</ReactMarkdown>
      </article>

      <label className="flex flex-col gap-1">
        <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Your code
        </span>
        <textarea
          value={code}
          onChange={(e) => setCode(e.target.value)}
          rows={Math.max(6, code.split("\n").length + 1)}
          spellCheck={false}
          className="rounded-md border border-border bg-background p-3 font-mono text-sm focus:border-foreground focus:outline-none"
          disabled={running}
        />
      </label>

      <div className="flex items-center justify-between gap-2">
        <p className="text-xs text-muted-foreground">
          {pyodideReady
            ? "Pyodide ready."
            : "Booting Pyodide… (first run takes ~5s)."}
        </p>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setCode(skeleton.starter_code)}
            className="text-xs text-muted-foreground underline-offset-4 hover:underline"
            disabled={running}
          >
            Reset
          </button>
          <Button onClick={run} disabled={running}>
            {running ? "Running…" : "Run tests"}
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-900">
          <p className="font-semibold">Error</p>
          <pre className="mt-1 whitespace-pre-wrap font-mono text-xs">
            {error}
          </pre>
        </div>
      )}

      {result && (
        <div
          className={
            passed
              ? "rounded-md border border-green-300 bg-green-50 p-3 text-sm text-green-900"
              : "rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900"
          }
        >
          <p className="font-semibold">
            {passed
              ? "✓ Tests pass. Apply stage complete."
              : `${result.tests.filter((t) => t.status === "passed").length} / ${result.tests.length} tests passed.`}
          </p>
          {!passed && (
            <pre className="mt-2 overflow-x-auto whitespace-pre-wrap font-mono text-xs">
              {result.output}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}
