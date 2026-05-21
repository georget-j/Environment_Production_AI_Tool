"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { celebrate } from "@/lib/celebrate";
import { runCWasmDemo } from "@/lib/c-wasm";
import type { CWasmLessonConfig } from "@/lib/featured-files";

type Props = {
  config: CWasmLessonConfig;
  nextSlug: string | null;
};

const AUTO_ADVANCE_MS = 1500;

type RunState =
  | { kind: "idle" }
  | { kind: "running" }
  | { kind: "pass"; stdout: string }
  | { kind: "fail"; stdout: string; reason: string };

function normalise(s: string): string {
  return s.replace(/\s+/g, " ").trim();
}

export function LessonCWasm({ config, nextSlug }: Props) {
  const router = useRouter();
  const [runState, setRunState] = useState<RunState>({ kind: "idle" });
  const [autoCancelled, setAutoCancelled] = useState(false);

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
    setRunState({ kind: "running" });
    const { stdout, error } = await runCWasmDemo(config.wasm_demo);
    if (error) {
      setRunState({ kind: "fail", stdout, reason: error });
      return;
    }
    if (
      normalise(stdout).includes(normalise(config.expected_stdout_contains))
    ) {
      setRunState({ kind: "pass", stdout });
    } else {
      setRunState({
        kind: "fail",
        stdout,
        reason: `Output didn't include the expected text: "${config.expected_stdout_contains}"`,
      });
    }
  }

  return (
    <section className="flex h-full min-h-0 flex-col gap-3 overflow-hidden rounded-lg border border-border bg-background p-4">
      <header className="flex flex-none items-center justify-between gap-2">
        <h3 className="text-sm font-semibold">Read the C, then run it</h3>
        <Button
          type="button"
          size="sm"
          onClick={run}
          disabled={runState.kind === "running"}
        >
          {runState.kind === "running" ? "Running…" : "Run demo"}
        </Button>
      </header>

      <pre className="min-h-0 flex-1 overflow-auto rounded-md border border-border bg-zinc-950 p-3 text-xs text-zinc-100">
        <code>{config.source}</code>
      </pre>

      {config.hint && (
        <p className="text-xs text-muted-foreground">
          <span className="font-semibold">Hint:</span> {config.hint}
        </p>
      )}

      <p className="text-[11px] text-muted-foreground">
        This is read-only C compiled ahead-of-time with clang (Emscripten, -O3).
        Unlike the editable C lessons, this one runs at the speed of real
        compiled code — the benchmarks here are honest.
      </p>

      {(runState.kind === "pass" || runState.kind === "fail") && (
        <div
          className={`rounded-md border px-3 py-2 ${runState.kind === "pass" ? "border-green-300 bg-green-50" : "border-red-300 bg-red-50"}`}
        >
          {runState.kind === "fail" && runState.reason && (
            <p className="mb-2 text-xs font-semibold text-red-900">
              {runState.reason}
            </p>
          )}
          <p className="mb-1 text-[10px] uppercase tracking-wide text-muted-foreground">
            Demo output
          </p>
          <pre className="overflow-x-auto whitespace-pre-wrap rounded border border-border bg-white p-2 font-mono text-xs">
            <code>{runState.stdout || "(no output)"}</code>
          </pre>
        </div>
      )}

      {runState.kind === "pass" && nextSlug && (
        <div
          onPointerEnter={() => setAutoCancelled(true)}
          onFocusCapture={() => setAutoCancelled(true)}
          className="space-y-2"
        >
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
                Stay
              </button>
            </p>
          ) : null}
        </div>
      )}
    </section>
  );
}
