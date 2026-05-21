"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { celebrate } from "@/lib/celebrate";
import type { MatplotLessonConfig } from "@/lib/featured-files";
import {
  ensureDataset,
  ensureMatplotlib,
  getPyodide,
  resetPyodide,
  runPythonAndCaptureFigure,
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
  config: MatplotLessonConfig;
  nextSlug: string | null;
  /** Parent uses this to keep the mentor's code snapshot fresh. */
  onCodeChange?: (code: string) => void;
};

const AUTO_ADVANCE_MS = 1500;

type RuntimeState =
  | { kind: "cold" }
  | { kind: "warming-pyodide" }
  | { kind: "warming-matplotlib" }
  | { kind: "ready" }
  | { kind: "error"; message: string };

type RunState =
  | { kind: "idle" }
  | { kind: "running" }
  | { kind: "pass"; stdout: string; svg: string }
  | {
      kind: "fail";
      stdout: string;
      svg: string | null;
      reason: string;
    };

function normalise(s: string): string {
  return s.replace(/\s+$/g, "").trimStart();
}

export function LessonMatplot({ config, nextSlug, onCodeChange }: Props) {
  const router = useRouter();
  const [code, setCode] = useState(config.template);
  const [runtime, setRuntime] = useState<RuntimeState>({ kind: "cold" });
  const [runState, setRunState] = useState<RunState>({ kind: "idle" });
  const [autoCancelled, setAutoCancelled] = useState(false);

  useEffect(() => {
    onCodeChange?.(code);
  }, [code, onCodeChange]);

  useEffect(() => {
    if (runState.kind === "pass") void celebrate();
  }, [runState.kind]);

  useEffect(() => {
    if (runState.kind !== "pass" || !nextSlug || autoCancelled) return;
    const id = window.setTimeout(
      () => router.push(`/challenges/${nextSlug}`),
      AUTO_ADVANCE_MS,
    );
    return () => window.clearTimeout(id);
  }, [runState.kind, nextSlug, autoCancelled, router]);

  // Boot pyodide then matplotlib. Matplotlib adds ~3MB on first warm; the
  // quant track's prewarm hook starts this before the learner ever clicks Run.
  useEffect(() => {
    if (runtime.kind !== "cold") return;
    setRuntime({ kind: "warming-pyodide" });
    void (async () => {
      try {
        await getPyodide();
        setRuntime({ kind: "warming-matplotlib" });
        await ensureMatplotlib();
        for (const slug of config.datasets ?? []) {
          await ensureDataset(slug);
        }
        setRuntime({ kind: "ready" });
      } catch (exc) {
        setRuntime({
          kind: "error",
          message: exc instanceof Error ? exc.message : String(exc),
        });
      }
    })();
  }, [runtime.kind, config.datasets]);

  async function run() {
    if (runtime.kind !== "ready") return;
    if (code.includes("___")) {
      setRunState({
        kind: "fail",
        stdout: "",
        svg: null,
        reason: "Replace the ___ placeholder(s) before clicking Run.",
      });
      return;
    }
    setRunState({ kind: "running" });
    const { stdout, svg, error } = await runPythonAndCaptureFigure(code);
    if (error) {
      setRunState({ kind: "fail", stdout, svg, reason: error });
      return;
    }
    if (!svg) {
      setRunState({
        kind: "fail",
        stdout,
        svg: null,
        reason:
          "No chart was drawn. Use matplotlib (e.g. `plt.plot(...)`) and don't `plt.close()` before the end.",
      });
      return;
    }
    if (
      typeof config.expected_stdout === "string" &&
      normalise(stdout) !== normalise(config.expected_stdout)
    ) {
      setRunState({
        kind: "fail",
        stdout,
        svg,
        reason: `Chart drew, but stdout didn't match. Expected:\n${config.expected_stdout}`,
      });
      return;
    }
    setRunState({ kind: "pass", stdout, svg });
  }

  function reset() {
    setCode(config.template);
    setRunState({ kind: "idle" });
  }

  function resetRuntime() {
    resetPyodide();
    setRuntime({ kind: "cold" });
    setRunState({ kind: "idle" });
  }

  const runDisabled = runtime.kind !== "ready" || runState.kind === "running";
  const runLabel =
    runState.kind === "running"
      ? "Running…"
      : runtime.kind === "warming-pyodide"
        ? "Loading Python…"
        : runtime.kind === "warming-matplotlib"
          ? "Loading matplotlib…"
          : "Run";

  return (
    <section className="flex h-full min-h-0 flex-col gap-3 overflow-hidden rounded-lg border border-border bg-background p-4">
      <header className="flex flex-none items-center justify-between gap-2">
        <h3 className="text-sm font-semibold">Plot it</h3>
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
            {runLabel}
          </Button>
        </div>
      </header>

      <div className="min-h-[140px] flex-1 overflow-hidden rounded-md border border-border">
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

      {runtime.kind === "error" && (
        <p className="rounded-md border border-red-300 bg-red-50 px-3 py-2 text-xs text-red-800">
          Python failed to load: {runtime.message}
        </p>
      )}

      {(runState.kind === "pass" || runState.kind === "fail") &&
        runState.svg && (
          <div
            className="max-h-[280px] overflow-auto rounded-md border border-border bg-white p-2"
            dangerouslySetInnerHTML={{ __html: runState.svg }}
          />
        )}

      {runState.kind === "pass" && (
        <div
          onPointerEnter={() => setAutoCancelled(true)}
          onFocusCapture={() => setAutoCancelled(true)}
          className="space-y-3 rounded-md border border-green-300 bg-green-50 px-4 py-3"
        >
          <p className="text-sm font-semibold text-green-900">
            ✓ Chart drew. Nice work.
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
          <p className="font-semibold">Run didn&apos;t pass.</p>
          <pre className="overflow-x-auto whitespace-pre-wrap rounded border border-red-200 bg-white p-2 font-mono">
            <code>{runState.reason}</code>
          </pre>
          {runState.stdout && (
            <div>
              <p className="mb-1 font-semibold text-red-900">Your stdout:</p>
              <pre className="overflow-x-auto rounded border border-red-200 bg-white p-2 font-mono">
                <code>{runState.stdout}</code>
              </pre>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
