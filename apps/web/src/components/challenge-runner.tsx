"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { createClient } from "@/lib/supabase/client";
import {
  getPyodide,
  runPytest,
  writeTree,
  type PytestResult,
  type TestStatus,
} from "@/lib/pyodide";
import type { ChallengeRunnerConfig, TestCase } from "@/lib/featured-files";

type FailureExplanation = {
  test_name: string;
  what_was_checked: string;
  what_happened: string;
  where_to_look: string;
};

const MonacoEditor = dynamic(() => import("@monaco-editor/react"), {
  ssr: false,
  loading: () => <p className="p-6 text-center text-xs text-muted-foreground">Loading editor…</p>,
});

const RAW_BASE = "https://raw.githubusercontent.com";
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const SUBMIT_REPO_URL = "https://prodready-ai.vercel.app/in-browser";

type Props = {
  challengeSlug: string;
  challengeId: string;
  repoTemplateUrl: string;
  branch: string;
  config: Extract<ChallengeRunnerConfig, { mode: "pyodide" }>;
  onTestsPassed?: () => void;
};

type ExplainState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "ready"; failures: FailureExplanation[] }
  | { kind: "error"; message: string };

type PyodideState =
  | { kind: "cold" }
  | { kind: "warming" }
  | { kind: "ready" }
  | { kind: "error"; message: string };

type RunState =
  | { kind: "idle" }
  | { kind: "running" }
  | { kind: "done"; result: PytestResult };

type SubmitState =
  | { kind: "idle" }
  | { kind: "submitting" }
  | { kind: "error"; message: string };

function parseOwnerRepo(url: string): { owner: string; repo: string } | null {
  try {
    const u = new URL(url);
    const [, owner, repo] = u.pathname.split("/");
    return owner && repo ? { owner, repo: repo.replace(/\.git$/, "") } : null;
  } catch {
    return null;
  }
}

function languageFromPath(p: string): string {
  if (p.endsWith(".py")) return "python";
  if (p.endsWith(".md")) return "markdown";
  if (p.endsWith(".yml") || p.endsWith(".yaml")) return "yaml";
  return "plaintext";
}

function storageKey(slug: string, path: string): string {
  return `prodready:edit:${slug}:${path}`;
}

function shortName(test: TestCase): string {
  return test.label ?? test.id.split("::").pop() ?? test.id;
}

function statusEmoji(status: TestStatus): string {
  switch (status) {
    case "passed":
      return "✓";
    case "failed":
      return "✗";
    case "error":
      return "!";
    case "skipped":
      return "—";
  }
}

function statusClass(status: TestStatus | "pending"): string {
  switch (status) {
    case "passed":
      return "text-green-700";
    case "failed":
    case "error":
      return "text-red-700";
    case "skipped":
      return "text-muted-foreground";
    case "pending":
      return "text-muted-foreground";
  }
}

export function ChallengeRunner({
  challengeSlug,
  challengeId,
  repoTemplateUrl,
  branch,
  config,
  onTestsPassed,
}: Props) {
  const meta = parseOwnerRepo(repoTemplateUrl);
  const allPaths = [...config.editable, ...config.readonly];

  const [files, setFiles] = useState<Record<string, string>>({});
  const [activeTab, setActiveTab] = useState<string>(config.editable[0] ?? allPaths[0]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [pyodideState, setPyodideState] = useState<PyodideState>({ kind: "cold" });
  const [runState, setRunState] = useState<RunState>({ kind: "idle" });
  const [submitState, setSubmitState] = useState<SubmitState>({ kind: "idle" });
  const [explainState, setExplainState] = useState<ExplainState>({ kind: "idle" });
  const passedNotified = useRef(false);
  const router = useRouter();

  // Pre-warm Pyodide on mount so the first Run feels instant.
  useEffect(() => {
    let cancelled = false;
    setPyodideState({ kind: "warming" });
    getPyodide()
      .then(() => {
        if (!cancelled) setPyodideState({ kind: "ready" });
      })
      .catch((exc) => {
        if (!cancelled) {
          setPyodideState({
            kind: "error",
            message: exc instanceof Error ? exc.message : String(exc),
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Load all files (editable get hydrated from localStorage on top of canonical).
  useEffect(() => {
    if (!meta) {
      setLoadError("Invalid repo URL");
      return;
    }
    let cancelled = false;
    (async () => {
      const next: Record<string, string> = {};
      for (const path of allPaths) {
        const url = `${RAW_BASE}/${meta.owner}/${meta.repo}/${branch}/${path}`;
        try {
          const res = await fetch(url, { cache: "no-cache" });
          if (!res.ok) {
            next[path] = "";
            continue;
          }
          next[path] = await res.text();
        } catch {
          next[path] = "";
        }
      }
      if (cancelled) return;

      for (const path of config.editable) {
        const saved =
          typeof window !== "undefined"
            ? window.localStorage.getItem(storageKey(challengeSlug, path))
            : null;
        if (saved !== null) next[path] = saved;
      }
      setFiles(next);
    })().catch((exc) => {
      if (!cancelled) setLoadError(exc instanceof Error ? exc.message : String(exc));
    });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [meta?.owner, meta?.repo, branch, challengeSlug]);

  const handleEdit = useCallback(
    (value: string | undefined) => {
      if (value === undefined) return;
      setFiles((prev) => ({ ...prev, [activeTab]: value }));
      if (typeof window !== "undefined") {
        window.localStorage.setItem(storageKey(challengeSlug, activeTab), value);
      }
    },
    [activeTab, challengeSlug],
  );

  const handleReset = useCallback(async () => {
    if (!meta) return;
    if (!confirm("Reset your edits to the original code? This can't be undone.")) return;
    const next = { ...files };
    for (const path of config.editable) {
      const url = `${RAW_BASE}/${meta.owner}/${meta.repo}/${branch}/${path}`;
      try {
        const res = await fetch(url, { cache: "no-cache" });
        if (res.ok) next[path] = await res.text();
      } catch {
        /* ignore */
      }
      if (typeof window !== "undefined") {
        window.localStorage.removeItem(storageKey(challengeSlug, path));
      }
    }
    setFiles(next);
    setRunState({ kind: "idle" });
  }, [meta, files, config.editable, branch, challengeSlug]);

  const explainFailures = useCallback(
    async (testOutput: string, currentFiles: Record<string, string>) => {
      setExplainState({ kind: "loading" });
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session) {
        setExplainState({ kind: "error", message: "Sign in to see AI explanations." });
        return;
      }
      try {
        const response = await fetch(`${API_BASE_URL}/api/ai/explain-tests`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${session.access_token}`,
          },
          body: JSON.stringify({
            challenge_id: challengeId,
            test_output: testOutput,
            files: currentFiles,
          }),
        });
        if (!response.ok) {
          setExplainState({ kind: "error", message: `Explanation API ${response.status}` });
          return;
        }
        const data = (await response.json()) as { failures: FailureExplanation[] };
        setExplainState({ kind: "ready", failures: data.failures });
      } catch (exc) {
        setExplainState({
          kind: "error",
          message: exc instanceof Error ? exc.message : "Explanation failed",
        });
      }
    },
    [challengeId],
  );

  const handleRun = useCallback(async () => {
    setRunState({ kind: "running" });
    setExplainState({ kind: "idle" });
    try {
      const pyodide = await getPyodide();
      setPyodideState({ kind: "ready" });
      const rooted: Record<string, string> = {};
      for (const [p, body] of Object.entries(files)) {
        rooted[`/home/pyodide/${p}`] = body;
      }
      writeTree(pyodide, rooted);
      const result = await runPytest(
        pyodide,
        config.tests.map((t) => t.id),
      );
      setRunState({ kind: "done", result });
      if (result.exitCode === 0 && !passedNotified.current) {
        passedNotified.current = true;
        onTestsPassed?.();
      }
      // If any test failed, kick off the AI explanation in the background.
      const hasFailure = result.tests.some(
        (t) => t.status === "failed" || t.status === "error",
      );
      if (hasFailure) {
        void explainFailures(result.output, files);
      }
    } catch (exc) {
      setRunState({
        kind: "done",
        result: {
          exitCode: -1,
          output: exc instanceof Error ? exc.message : String(exc),
          tests: [],
          summary: "Runner error",
        },
      });
    }
  }, [files, config.tests, onTestsPassed, explainFailures]);

  const editable = config.editable.includes(activeTab);
  const passed = runState.kind === "done" && runState.result.exitCode === 0;

  const handleSubmit = useCallback(async () => {
    if (runState.kind !== "done" || runState.result.exitCode !== 0) return;
    setSubmitState({ kind: "submitting" });
    const supabase = createClient();
    const {
      data: { session },
    } = await supabase.auth.getSession();
    if (!session) {
      setSubmitState({ kind: "error", message: "Sign in first." });
      return;
    }
    const response = await fetch(`${API_BASE_URL}/api/challenges/${challengeSlug}/submit`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${session.access_token}`,
      },
      body: JSON.stringify({
        repo_url: SUBMIT_REPO_URL,
        test_output: runState.result.output,
      }),
    });
    if (!response.ok) {
      const body = await response.text();
      setSubmitState({
        kind: "error",
        message: `Submit failed (${response.status}): ${body.slice(0, 200)}`,
      });
      return;
    }
    const data = await response.json();
    router.push(`/submissions/${data.id}`);
  }, [runState, challengeSlug, router]);

  // Build a per-test view by joining config.tests with the parsed pytest output
  // and the AI explanation, if any.
  function findExplanation(t: TestCase): FailureExplanation | undefined {
    if (explainState.kind !== "ready") return undefined;
    const short = shortName(t);
    return explainState.failures.find((f) => {
      const name = f.test_name;
      return (
        name === t.id ||
        name === short ||
        name.endsWith(`::${short}`) ||
        t.id.endsWith(`::${name}`) ||
        name.includes(short) ||
        short.includes(name)
      );
    });
  }

  const testRows = config.tests.map((t) => {
    const observed =
      runState.kind === "done"
        ? runState.result.tests.find(
            (r) => r.name === shortName(t) || t.id.endsWith(`::${r.name}`),
          )
        : undefined;
    return { ...t, status: observed?.status ?? ("pending" as const) };
  });

  return (
    <section className="space-y-4">
      <div className="rounded-md border border-border bg-blue-50/40 p-4 text-xs leading-relaxed text-foreground">
        <p className="mb-2 font-semibold">How this works</p>
        <ol className="list-decimal space-y-1 pl-5 text-muted-foreground">
          <li>
            Edit the unlocked files in the workspace below — your changes are saved as you type.
          </li>
          <li>
            Click <strong>Run tests</strong>. Pytest runs <em>inside your browser</em> via Pyodide
            (Python compiled to WebAssembly). No code is sent anywhere.
          </li>
          <li>
            We run a fixed set of test cases — listed below — and show pass/fail per test plus the
            raw pytest output.
          </li>
          <li>
            When all tests pass, <strong>Submit solution</strong> records your win and runs the AI
            review.
          </li>
        </ol>
      </div>

      {pyodideState.kind === "warming" && (
        <div className="rounded-md border border-border bg-muted/20 px-3 py-2 text-xs text-muted-foreground">
          Loading the Python runtime (~10 MB, one-time). You can start editing — Run will be ready
          shortly.
        </div>
      )}
      {pyodideState.kind === "error" && (
        <div className="rounded-md border border-red-300 bg-red-50 px-3 py-2 text-xs text-red-700">
          Couldn&apos;t load Python: {pyodideState.message}
        </div>
      )}

      <section className="rounded-md border border-border">
        <header className="flex items-center justify-between border-b border-border bg-muted/30 px-3 py-2 text-xs font-semibold">
          <span>Tests for this challenge ({config.tests.length})</span>
          {explainState.kind === "loading" && (
            <span className="font-normal text-muted-foreground">Asking mentor about failures…</span>
          )}
          {explainState.kind === "error" && (
            <span className="font-normal text-red-700">{explainState.message}</span>
          )}
        </header>
        <ul className="divide-y divide-border">
          {testRows.map((t) => {
            const ex = findExplanation(t);
            const showFailureBox = t.status === "failed" || t.status === "error";
            return (
              <li key={t.id} className="px-3 py-2">
                <div className="flex items-start gap-3 text-xs">
                  <span className={cn("w-4 shrink-0 font-mono", statusClass(t.status))}>
                    {t.status === "pending" ? "·" : statusEmoji(t.status)}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-mono text-[11px]">{shortName(t)}</p>
                    <p className="text-muted-foreground">{t.description}</p>
                  </div>
                </div>
                {showFailureBox && (
                  <div className="mt-2 ml-7 space-y-2 rounded-md border border-red-200 bg-red-50/60 p-4 text-sm leading-relaxed">
                    {ex ? (
                      <>
                        <p>
                          <span className="font-semibold">What this test checked: </span>
                          {ex.what_was_checked}
                        </p>
                        <p>
                          <span className="font-semibold">What happened: </span>
                          {ex.what_happened}
                        </p>
                        <p>
                          <span className="font-semibold">Where to look next: </span>
                          {ex.where_to_look}
                        </p>
                      </>
                    ) : explainState.kind === "loading" ? (
                      <p className="text-muted-foreground">Generating explanation…</p>
                    ) : explainState.kind === "ready" ? (
                      <p className="text-muted-foreground">
                        Mentor returned an explanation but couldn&apos;t match it to this test.
                        Check the raw pytest output below.
                      </p>
                    ) : explainState.kind === "error" ? (
                      <p className="text-muted-foreground">
                        Mentor couldn&apos;t reach the AI ({explainState.message}). Check the raw
                        output below.
                      </p>
                    ) : null}
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      </section>

      <section className="space-y-3">
        <header className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-sm font-semibold">Workspace</h2>
            <p className="text-xs text-muted-foreground">
              {config.editable.length} editable file{config.editable.length === 1 ? "" : "s"} ·{" "}
              {config.readonly.length} read-only (context for the tests)
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="ghost"
              onClick={handleReset}
              disabled={Object.keys(files).length === 0}
            >
              Reset
            </Button>
            <Button
              size="sm"
              onClick={handleRun}
              disabled={runState.kind === "running" || pyodideState.kind === "warming"}
            >
              {runState.kind === "running"
                ? "Running tests…"
                : pyodideState.kind === "warming"
                  ? "Loading Python…"
                  : "Run tests"}
            </Button>
          </div>
        </header>

        {loadError && <p className="text-xs text-red-600">Could not load files: {loadError}</p>}

        <div className="flex flex-wrap gap-1 overflow-x-auto border-b border-border">
          {allPaths.map((p) => {
            const isEditable = config.editable.includes(p);
            return (
              <button
                key={p}
                type="button"
                onClick={() => setActiveTab(p)}
                className={cn(
                  "flex items-center gap-1 rounded-t-md border-b-2 px-3 py-1.5 font-mono text-xs",
                  p === activeTab
                    ? "border-primary bg-muted text-foreground"
                    : "border-transparent text-muted-foreground hover:text-foreground",
                )}
                title={isEditable ? "Editable" : "Read-only"}
              >
                <span>{p}</span>
                {!isEditable && <span className="text-[10px]">🔒</span>}
              </button>
            );
          })}
        </div>

        <div className="overflow-hidden rounded-md border border-border">
          <MonacoEditor
            key={activeTab}
            height="420px"
            language={languageFromPath(activeTab)}
            value={files[activeTab] ?? ""}
            onChange={editable ? handleEdit : undefined}
            options={{
              readOnly: !editable,
              minimap: { enabled: false },
              fontSize: 13,
              scrollBeyondLastLine: false,
              tabSize: 4,
            }}
            theme="vs-light"
          />
        </div>
      </section>

      {runState.kind === "done" && (
        <section
          className={cn(
            "space-y-3 rounded-md border p-3",
            passed ? "border-green-300 bg-green-50" : "border-red-300 bg-red-50",
          )}
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-sm font-semibold">
              {passed
                ? `✓ ${runState.result.summary || "All tests passed"}`
                : runState.result.exitCode === -1
                  ? "Runner error"
                  : `✗ ${runState.result.summary || `pytest exited ${runState.result.exitCode}`}`}
            </p>
            {passed && (
              <Button
                size="sm"
                onClick={handleSubmit}
                disabled={submitState.kind === "submitting"}
              >
                {submitState.kind === "submitting" ? "Submitting…" : "Submit solution"}
              </Button>
            )}
          </div>
          {submitState.kind === "error" && (
            <p className="text-xs text-red-700">{submitState.message}</p>
          )}
          <details className="text-xs">
            <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
              Raw pytest output
            </summary>
            <pre className="mt-2 max-h-80 overflow-auto rounded bg-white p-3 font-mono text-[11px] leading-relaxed">
              {runState.result.output || "(no output)"}
            </pre>
          </details>
        </section>
      )}
    </section>
  );
}
