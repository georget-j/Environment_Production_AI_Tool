/**
 * Pyodide proxy.
 *
 * The heavy lifting lives in apps/web/src/lib/pyodide-worker.ts. This
 * module spins up that worker on first call and forwards typed RPCs to
 * it, so callers don't need to know about Worker / postMessage.
 *
 * Public API is intentionally close to the previous in-process version
 * so the lesson runners didn't need much refactoring:
 *   - getPyodide(): resolves when the worker has booted Pyodide
 *   - ensurePytest(): installs pytest inside the worker (idempotent)
 *   - ensureMatplotlib(): installs matplotlib (idempotent)
 *   - runPythonStdout(code): one-shot run + stdout capture
 *   - runPythonAndCaptureFigure(code): run + grab the active figure as SVG
 *   - runPytest(files, pytestArgs): writes files, runs pytest, returns result
 *   - resetPyodide(): terminate the worker; next call boots a fresh one
 *   - detectUnsupportedFeatures(code): pure pre-flight check
 */

export type TestStatus = "passed" | "failed" | "error" | "skipped";
export type TestRow = { name: string; status: TestStatus };
export type FailureLocations = Record<string, number[]>;
export type PytestResult = {
  exitCode: number;
  output: string;
  tests: TestRow[];
  summary: string;
  failureLocations: FailureLocations;
};

const INPUT_CALL_RE = /(^|\W)input\s*\(/m;
export function detectUnsupportedFeatures(code: string): string | null {
  if (INPUT_CALL_RE.test(code)) {
    return "This sandbox doesn't support `input()` — there's no terminal to type into. Replace `input(...)` with a hard-coded value (e.g. `name = \"Ada\"`) and click Run again.";
  }
  return null;
}

type Pending = { resolve: (v: unknown) => void; reject: (e: Error) => void };

let workerInstance: Worker | null = null;
let nextId = 0;
const pending = new Map<number, Pending>();

function getWorker(): Worker {
  if (workerInstance) return workerInstance;
  // Webpack/Next.js recognises this pattern and bundles the worker as a
  // separate chunk. Module workers are required because pyodide-worker.ts
  // uses TypeScript type imports etc.
  workerInstance = new Worker(new URL("./pyodide-worker.ts", import.meta.url), {
    type: "classic",
  });
  workerInstance.onmessage = (e: MessageEvent) => {
    const data = e.data as
      | { id: number; result: unknown }
      | { id: number; error: string };
    const slot = pending.get(data.id);
    if (!slot) return;
    pending.delete(data.id);
    if ("error" in data) slot.reject(new Error(data.error));
    else slot.resolve(data.result);
  };
  workerInstance.onerror = (e) => {
    // Reject everything in flight if the worker itself errors out.
    const message = (e as ErrorEvent).message || "Pyodide worker crashed";
    for (const slot of pending.values()) slot.reject(new Error(message));
    pending.clear();
  };
  return workerInstance;
}

function call<T>(fn: string, args?: unknown): Promise<T> {
  const id = ++nextId;
  return new Promise<T>((resolve, reject) => {
    pending.set(id, {
      resolve: (v) => resolve(v as T),
      reject,
    });
    getWorker().postMessage({ id, fn, args });
  });
}

export async function getPyodide(): Promise<void> {
  await call<null>("init");
}

export async function ensurePytest(): Promise<void> {
  await call<null>("ensurePytest");
}

export async function ensureMatplotlib(): Promise<void> {
  await call<null>("ensureMatplotlib");
}

/** Fetch /data/quant/<slug>.csv and mount it inside Pyodide's FS so lessons
 *  can `pd.read_csv("/data/quant/<slug>.csv")` without thinking about it. */
export async function ensureDataset(slug: string): Promise<void> {
  await call<null>("ensureDataset", { slug });
}

export async function runPythonStdout(
  code: string,
): Promise<{ stdout: string; error: string | null }> {
  const unsupported = detectUnsupportedFeatures(code);
  if (unsupported) return { stdout: "", error: unsupported };
  return call<{ stdout: string; error: string | null }>("runPythonStdout", {
    code,
  });
}

export async function runPythonAndCaptureFigure(
  code: string,
): Promise<{ stdout: string; svg: string | null; error: string | null }> {
  const unsupported = detectUnsupportedFeatures(code);
  if (unsupported) return { stdout: "", svg: null, error: unsupported };
  return call<{ stdout: string; svg: string | null; error: string | null }>(
    "runPythonAndCaptureFigure",
    { code },
  );
}

export async function runPytest(
  files: Record<string, string>,
  pytestArgs: string[],
): Promise<PytestResult> {
  return call<PytestResult>("runPytest", { files, pytestArgs });
}

/** Throw away the current worker (and its Pyodide instance). The next call
 *  to any of the above spins up a fresh worker. */
export function resetPyodide(): void {
  if (workerInstance) {
    workerInstance.terminate();
    workerInstance = null;
  }
  for (const slot of pending.values()) {
    slot.reject(new Error("Pyodide was reset"));
  }
  pending.clear();
}
