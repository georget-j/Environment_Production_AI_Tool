"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { createClient } from "@/lib/supabase/client";
import { getPyodide, runPytest, writeTree, type PytestResult } from "@/lib/pyodide";
import type { ChallengeRunnerConfig } from "@/lib/featured-files";

const MonacoEditor = dynamic(() => import("@monaco-editor/react"), {
  ssr: false,
  loading: () => <p className="p-6 text-center text-xs text-muted-foreground">Loading editor…</p>,
});

const RAW_BASE = "https://raw.githubusercontent.com";
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const SUBMIT_REPO_URL = "https://prodready-ai.vercel.app/in-browser";

type Props = {
  challengeSlug: string;
  repoTemplateUrl: string;
  branch: string;
  config: Extract<ChallengeRunnerConfig, { mode: "pyodide" }>;
  onTestsPassed?: () => void;
};

type RunState =
  | { kind: "idle" }
  | { kind: "loading-pyodide" }
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

export function ChallengeRunner({
  challengeSlug,
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
  const [runState, setRunState] = useState<RunState>({ kind: "idle" });
  const [submitState, setSubmitState] = useState<SubmitState>({ kind: "idle" });
  const passedNotified = useRef(false);
  const router = useRouter();

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
          const res = await fetch(url, { cache: "force-cache" });
          if (!res.ok) {
            // tests/__init__.py and similar may be empty/missing — treat as empty.
            next[path] = "";
            continue;
          }
          next[path] = await res.text();
        } catch {
          next[path] = "";
        }
      }
      if (cancelled) return;

      // Restore learner edits from localStorage.
      for (const path of config.editable) {
        const saved = typeof window !== "undefined"
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
    // allPaths is derived from config; depending on it would re-fetch on every render.
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

  const handleRun = useCallback(async () => {
    setRunState({ kind: "loading-pyodide" });
    try {
      const pyodide = await getPyodide();
      // Map our paths into /home/pyodide so cwd is consistent.
      const rooted: Record<string, string> = {};
      for (const [p, body] of Object.entries(files)) {
        rooted[`home/pyodide/${p}`] = body;
      }
      writeTree(pyodide, rooted);
      setRunState({ kind: "running" });
      const result = await runPytest(pyodide, config.pytestArgs);
      setRunState({ kind: "done", result });
      if (result.exitCode === 0 && !passedNotified.current) {
        passedNotified.current = true;
        onTestsPassed?.();
      }
    } catch (exc) {
      setRunState({
        kind: "done",
        result: { exitCode: -1, output: exc instanceof Error ? exc.message : String(exc) },
      });
    }
  }, [files, config.pytestArgs, onTestsPassed]);

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

  return (
    <section className="space-y-3">
      <header className="flex items-center justify-between">
        <h2 className="text-sm font-semibold">Workspace</h2>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="ghost" onClick={handleReset} disabled={Object.keys(files).length === 0}>
            Reset
          </Button>
          <Button
            size="sm"
            onClick={handleRun}
            disabled={runState.kind === "loading-pyodide" || runState.kind === "running"}
          >
            {runState.kind === "loading-pyodide"
              ? "Booting Python…"
              : runState.kind === "running"
                ? "Running tests…"
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

      {runState.kind === "done" && (
        <div
          className={cn(
            "space-y-2 rounded-md border p-3",
            passed ? "border-green-300 bg-green-50" : "border-red-300 bg-red-50",
          )}
        >
          <div className="flex items-center justify-between gap-2">
            <p className="text-xs font-semibold">
              {passed ? "✓ All tests passed" : `✗ pytest exited ${runState.result.exitCode}`}
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
          <pre className="max-h-80 overflow-auto rounded bg-white p-3 font-mono text-[11px] leading-relaxed">
            {runState.result.output || "(no output)"}
          </pre>
        </div>
      )}

      {runState.kind === "idle" && (
        <p className="text-xs text-muted-foreground">
          Edit the files on the left and hit <strong>Run tests</strong>. First run downloads Python
          (~10 MB) — subsequent runs are instant.
        </p>
      )}
    </section>
  );
}
