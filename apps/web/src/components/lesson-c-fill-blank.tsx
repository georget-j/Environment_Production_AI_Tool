"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { celebrate } from "@/lib/celebrate";
import type { CScriptLessonConfig } from "@/lib/featured-files";
import { resetCRuntime, runC } from "@/lib/c-runtime";

const MonacoEditor = dynamic(() => import("@monaco-editor/react"), {
  ssr: false,
  loading: () => (
    <p className="p-6 text-center text-xs text-muted-foreground">
      Loading editor…
    </p>
  ),
});

type Props = {
  config: CScriptLessonConfig;
  nextSlug: string | null;
  onCodeChange?: (code: string) => void;
};

const AUTO_ADVANCE_MS = 1500;

type RunState =
  | { kind: "idle" }
  | { kind: "running" }
  | { kind: "pass"; stdout: string }
  | { kind: "fail"; stdout: string; expected: string; error: string | null };

function normalise(s: string): string {
  return s.replace(/\s+$/g, "").trimStart();
}

export function LessonCFillBlank({ config, nextSlug, onCodeChange }: Props) {
  const router = useRouter();
  const [code, setCode] = useState(config.template);
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

  async function run() {
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
    const { stdout, error } = await runC(code);
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

  function resetCode() {
    setCode(config.template);
    setRunState({ kind: "idle" });
  }

  function resetRuntime() {
    resetCRuntime();
    setRunState({ kind: "idle" });
  }

  return (
    <section className="flex h-full min-h-0 flex-col gap-3 overflow-hidden rounded-lg border border-border bg-background p-4">
      <header className="flex flex-none items-center justify-between gap-2">
        <h3 className="text-sm font-semibold">Write the C</h3>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={resetRuntime}
            className="text-[11px] text-muted-foreground underline-offset-2 hover:underline"
            title="Reload the C interpreter if it gets stuck"
          >
            Reset C runtime
          </button>
          <Button type="button" variant="outline" size="sm" onClick={resetCode}>
            Reset code
          </Button>
          <Button
            type="button"
            size="sm"
            onClick={run}
            disabled={runState.kind === "running"}
          >
            {runState.kind === "running" ? "Running…" : "Run"}
          </Button>
        </div>
      </header>

      <div className="min-h-[160px] flex-1 overflow-hidden rounded-md border border-border">
        <MonacoEditor
          height="100%"
          defaultLanguage="c"
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

      <p className="text-[11px] text-muted-foreground">
        Runs in an in-browser C interpreter (picoc / WASM). Real C compiles
        ahead-of-time with gcc/clang; this sandbox supports a subset —{" "}
        <code>printf</code>, structs, pointers, malloc/free, function pointers,
        and the basics of <code>&lt;math.h&gt;</code>,{" "}
        <code>&lt;string.h&gt;</code>, <code>&lt;stdlib.h&gt;</code>. Avoid deep
        recursion (small stack).
      </p>

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
            <pre className="overflow-x-auto whitespace-pre-wrap rounded border border-red-200 bg-white p-2 font-mono">
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
