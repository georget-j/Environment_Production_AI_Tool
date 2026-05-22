"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { celebrate } from "@/lib/celebrate";
import type { FillBlankLessonConfig } from "@/lib/featured-files";
import {
  ensureDataset,
  getPyodide,
  resetPyodide,
  runPythonStdout,
} from "@/lib/pyodide";

const MonacoEditor = dynamic(() => import("@monaco-editor/react"), {
  ssr: false,
  loading: () => (
    <p className="p-6 text-center text-xs text-muted-foreground">
      Loading editor…
    </p>
  ),
});

type Props = {
  config: FillBlankLessonConfig;
  nextSlug: string | null;
  /** Notified whenever the learner edits the snippet. ChallengeView uses
   * this to keep the snapshot it ships to the mentor in sync. */
  onCodeChange?: (code: string) => void;
};

const AUTO_ADVANCE_MS = 1500;

type PyodideState =
  | { kind: "cold" }
  | { kind: "warming" }
  | { kind: "ready" }
  | { kind: "error"; message: string };

type RunState =
  | { kind: "idle" }
  | { kind: "running" }
  | { kind: "pass"; stdout: string }
  | { kind: "fail"; stdout: string; expected: string; error: string | null };

function normalise(s: string): string {
  return s.replace(/\s+$/g, "").trimStart();
}

export function LessonFillBlank({ config, nextSlug, onCodeChange }: Props) {
  const router = useRouter();
  const [code, setCode] = useState(config.template);

  // Push the initial template + every edit up to the parent so the mentor
  // snapshot stays current.
  useEffect(() => {
    onCodeChange?.(code);
  }, [code, onCodeChange]);
  const [pyodideState, setPyodideState] = useState<PyodideState>({
    kind: "cold",
  });
  const [runState, setRunState] = useState<RunState>({ kind: "idle" });
  const [autoCancelled, setAutoCancelled] = useState(false);

  // Celebrate the first time the run state flips to pass.
  useEffect(() => {
    if (runState.kind === "pass") void celebrate();
  }, [runState.kind]);

  // Auto-advance to the next lesson 1.5s after pass, unless cancelled.
  useEffect(() => {
    if (runState.kind !== "pass" || !nextSlug || autoCancelled) return;
    const id = window.setTimeout(
      () => router.push(`/challenges/${nextSlug}`),
      AUTO_ADVANCE_MS,
    );
    return () => window.clearTimeout(id);
  }, [runState.kind, nextSlug, autoCancelled, router]);

  useEffect(() => {
    if (pyodideState.kind !== "cold") return;
    setPyodideState({ kind: "warming" });
    void (async () => {
      try {
        await getPyodide();
        for (const slug of config.datasets ?? []) {
          await ensureDataset(slug);
        }
        setPyodideState({ kind: "ready" });
      } catch (exc) {
        setPyodideState({
          kind: "error",
          message: exc instanceof Error ? exc.message : String(exc),
        });
      }
    })();
  }, [pyodideState.kind, config.datasets]);

  async function run() {
    if (pyodideState.kind !== "ready") return;
    if (code.includes("___")) {
      setRunState({
        kind: "fail",
        stdout: "",
        expected: config.expected_stdout,
        error: "Replace the ___ placeholder(s) before clicking Run.",
      });
      return;
    }
    setRunState({ kind: "running" });
    const { stdout, error } = await runPythonStdout(code);
    if (error) {
      setRunState({
        kind: "fail",
        stdout,
        expected: config.expected_stdout,
        error,
      });
      return;
    }
    if (normalise(stdout) === normalise(config.expected_stdout)) {
      setRunState({ kind: "pass", stdout });
    } else {
      setRunState({
        kind: "fail",
        stdout,
        expected: config.expected_stdout,
        error: null,
      });
    }
  }

  function reset() {
    setCode(config.template);
    setRunState({ kind: "idle" });
  }

  /** Wipe the Pyodide singleton and re-warm. Used when the runtime has
   * gotten into a bad state — e.g. learner code overrode `print` or
   * `sys.stdout`. Cheap: ~3–5s to spin up a fresh instance. */
  function resetRuntime() {
    resetPyodide();
    setPyodideState({ kind: "cold" });
    setRunState({ kind: "idle" });
  }

  const runDisabled =
    pyodideState.kind !== "ready" || runState.kind === "running";

  return (
    <section className="flex flex-col gap-3 rounded-lg border border-border bg-background p-4">
      <header className="flex flex-none items-center justify-between gap-2">
        <h3 className="text-sm font-semibold">Replace the blanks</h3>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={resetRuntime}
            className="text-[11px] text-muted-foreground underline-offset-2 hover:underline"
            title="Wipe the Python sandbox if it gets stuck"
          >
            Reset Python
          </button>
          <Button type="button" variant="outline" size="sm" onClick={reset}>
            Reset code
          </Button>
          <Button type="button" size="sm" onClick={run} disabled={runDisabled}>
            {runState.kind === "running"
              ? "Running…"
              : pyodideState.kind === "warming"
                ? "Loading Python…"
                : "Run"}
          </Button>
        </div>
      </header>

      <div className="h-[50vh] min-h-[260px] overflow-hidden rounded-md border border-border">
        <MonacoEditor
          height="100%"
          defaultLanguage="python"
          theme="vs-dark"
          value={code}
          onChange={(value) => setCode(value ?? "")}
          options={{
            minimap: { enabled: false },
            fontSize: 13,
            lineNumbers: "on",
            renderWhitespace: "selection",
            scrollBeyondLastLine: false,
          }}
        />
      </div>

      {config.hint && (
        <p className="text-xs text-muted-foreground">
          <span className="font-semibold">Hint:</span> {config.hint}
        </p>
      )}

      {pyodideState.kind === "error" && (
        <p className="rounded-md border border-red-300 bg-red-50 px-3 py-2 text-xs text-red-800">
          Python failed to load: {pyodideState.message}
        </p>
      )}

      {runState.kind === "pass" && (
        <div
          onPointerEnter={() => setAutoCancelled(true)}
          onFocusCapture={() => setAutoCancelled(true)}
          className="space-y-3 rounded-md border border-green-300 bg-green-50 px-4 py-3"
        >
          <p className="text-sm font-semibold text-green-900">
            ✓ Output matches. Nice work.
          </p>
          {nextSlug ? (
            <>
              <Button
                type="button"
                className="w-full"
                onClick={() => router.push(`/challenges/${nextSlug}`)}
              >
                Next lesson →
              </Button>
              {!autoCancelled ? (
                <p className="text-center text-[11px] text-green-900/70">
                  Auto-advancing in {Math.round(AUTO_ADVANCE_MS / 1000)}s …{" "}
                  <button
                    type="button"
                    onClick={() => setAutoCancelled(true)}
                    className="underline hover:no-underline"
                  >
                    Stay on this lesson
                  </button>
                </p>
              ) : (
                <p className="text-center text-[11px] text-green-900/70">
                  Take your time — click Next when you&apos;re ready.
                </p>
              )}
            </>
          ) : (
            <p className="text-sm text-green-900">
              You&apos;ve finished the last lesson of this track 🎉
            </p>
          )}
        </div>
      )}

      {runState.kind === "fail" && (
        <div className="space-y-2 rounded-md border border-red-300 bg-red-50 px-3 py-2 text-xs text-red-800">
          <p className="font-semibold">Output didn&apos;t match.</p>
          {runState.error && (
            <pre className="overflow-x-auto rounded border border-red-200 bg-white p-2 font-mono">
              <code>{runState.error}</code>
            </pre>
          )}
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            <div>
              <p className="mb-1 font-semibold text-red-900">Your output:</p>
              <pre className="overflow-x-auto rounded border border-red-200 bg-white p-2 font-mono">
                <code>{runState.stdout || "(nothing)"}</code>
              </pre>
            </div>
            <div>
              <p className="mb-1 font-semibold text-red-900">Expected:</p>
              <pre className="overflow-x-auto rounded border border-red-200 bg-white p-2 font-mono">
                <code>{runState.expected}</code>
              </pre>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
