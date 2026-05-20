/**
 * Pyodide loader.
 *
 * Pyodide is heavy (~10 MB compressed). We load it from jsdelivr lazily.
 * The runner pre-warms it on page mount so first Run feels instant.
 */

const PYODIDE_VERSION = "0.26.4";
const PYODIDE_INDEX_URL = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;

type PyodideInterface = {
  FS: {
    writeFile(path: string, content: string): void;
    readdir(path: string): string[];
    mkdir(path: string): void;
    analyzePath(path: string): { exists: boolean };
  };
  runPythonAsync(code: string): Promise<unknown>;
  loadPackage(names: string | string[]): Promise<void>;
  pyimport(name: string): { install(deps: string[]): Promise<void> };
  setStdout(opts: { batched: (s: string) => void }): void;
  setStderr(opts: { batched: (s: string) => void }): void;
};

declare global {
  interface Window {
    loadPyodide?: (options: { indexURL: string }) => Promise<PyodideInterface>;
  }
}

// Module-scope singletons. Next.js soft navigation (clicking <Link> for the
// next lesson) preserves the module — so these survive page transitions
// without re-paying the ~5s Pyodide warm-up. A full reload resets them.
let pyodidePromise: Promise<PyodideInterface> | null = null;
let pytestPromise: Promise<void> | null = null;

function injectLoaderScript(): Promise<void> {
  return new Promise((resolve, reject) => {
    if (typeof window === "undefined") {
      reject(new Error("Pyodide can only load in the browser"));
      return;
    }
    if (window.loadPyodide) {
      resolve();
      return;
    }
    const existing = document.querySelector<HTMLScriptElement>(
      "script[data-pyodide]",
    );
    if (existing) {
      existing.addEventListener("load", () => resolve());
      existing.addEventListener("error", () =>
        reject(new Error("Pyodide loader failed")),
      );
      return;
    }
    const script = document.createElement("script");
    script.src = `${PYODIDE_INDEX_URL}pyodide.js`;
    script.async = true;
    script.dataset.pyodide = "1";
    script.addEventListener("load", () => resolve());
    script.addEventListener("error", () =>
      reject(new Error("Pyodide loader failed")),
    );
    document.head.appendChild(script);
  });
}

/**
 * Bare Pyodide — no pytest, no micropip work. Used by the Python Basics
 * `fillblank` runner (which only needs `runPythonStdout`) and as the base
 * the pytest-mode runners extend via `ensurePytest()`.
 */
export async function getPyodide(): Promise<PyodideInterface> {
  if (pyodidePromise) return pyodidePromise;

  pyodidePromise = (async () => {
    await injectLoaderScript();
    if (!window.loadPyodide) {
      throw new Error("loadPyodide not exposed after script load");
    }
    return window.loadPyodide({ indexURL: PYODIDE_INDEX_URL });
  })().catch((exc) => {
    pyodidePromise = null;
    throw exc;
  });

  return pyodidePromise;
}

/**
 * Install pytest on top of bare Pyodide, exactly once. Subsequent calls
 * return the cached promise so the FastAPI runner can call this on every
 * `handleRun` without paying the install cost twice.
 */
export async function ensurePytest(pyodide: PyodideInterface): Promise<void> {
  if (pytestPromise) return pytestPromise;
  pytestPromise = (async () => {
    await pyodide.loadPackage(["micropip"]);
    const micropip = pyodide.pyimport("micropip");
    await micropip.install(["pytest"]);
  })().catch((exc) => {
    pytestPromise = null;
    throw exc;
  });
  return pytestPromise;
}

/**
 * Write a tree of files into Pyodide's in-memory filesystem.
 * Coerces every path to absolute so writes don't depend on cwd.
 */
export function writeTree(
  pyodide: PyodideInterface,
  files: Record<string, string>,
): void {
  for (const [rawPath, body] of Object.entries(files)) {
    const abs = rawPath.startsWith("/") ? rawPath : `/${rawPath}`;
    const segments = abs.split("/").filter(Boolean);
    let cursor = "";
    for (let i = 0; i < segments.length - 1; i++) {
      cursor = `${cursor}/${segments[i]}`;
      if (!pyodide.FS.analyzePath(cursor).exists) {
        pyodide.FS.mkdir(cursor);
      }
    }
    pyodide.FS.writeFile(abs, body);
  }
}

export type TestStatus = "passed" | "failed" | "error" | "skipped";

export type TestRow = {
  name: string;
  status: TestStatus;
};

/** Production-code locations parsed out of the `--tb=short` traceback.
 * Maps a file path (e.g. "app/orders.py") to the set of 1-indexed line
 * numbers that appeared in failure tracebacks. Test files are excluded.
 */
export type FailureLocations = Record<string, number[]>;

export type PytestResult = {
  exitCode: number;
  output: string;
  tests: TestRow[];
  summary: string;
  failureLocations: FailureLocations;
};

// "tests/test_orders.py::test_compute_total_without_coupon PASSED  [ 14%]"
const VERBOSE_LINE_RE =
  /^(.+?::[\w[\]\-.]+)\s+(PASSED|FAILED|ERROR|SKIPPED)\b/i;
// Short traceback line: "app/orders.py:24: in compute_total" or "app/orders.py:24:"
const TB_LOCATION_RE = /^([\w./-]+\.py):(\d+):/;

const STATUS_MAP: Record<string, TestStatus> = {
  PASSED: "passed",
  FAILED: "failed",
  ERROR: "error",
  SKIPPED: "skipped",
};

function parseVerboseOutput(text: string): {
  tests: TestRow[];
  summary: string;
  failureLocations: FailureLocations;
} {
  const tests: TestRow[] = [];
  let summary = "";
  const failureLocations: FailureLocations = {};
  for (const rawLine of text.split("\n")) {
    const line = rawLine.trimStart();

    const statusMatch = VERBOSE_LINE_RE.exec(line);
    if (statusMatch) {
      tests.push({
        name: statusMatch[1].split("::").pop() ?? statusMatch[1],
        status: STATUS_MAP[statusMatch[2].toUpperCase()],
      });
      continue;
    }

    // Summary line: "= 1 failed, 4 passed in 0.42s ="
    if (/=+\s*\d+ (passed|failed|error|skipped)/.test(line)) {
      summary = line.replace(/=/g, "").trim();
      continue;
    }

    // Traceback location: skip test files, pytest internals, std-lib, and pyodide.
    const tbMatch = TB_LOCATION_RE.exec(line);
    if (tbMatch) {
      const path = tbMatch[1];
      const lineNumber = parseInt(tbMatch[2], 10);
      if (
        path.startsWith("tests/") ||
        path.includes("/_pytest/") ||
        path.includes("/pluggy/") ||
        path.includes("/python3") ||
        path.startsWith("/lib/")
      ) {
        continue;
      }
      const existing = failureLocations[path] ?? [];
      if (!existing.includes(lineNumber)) {
        failureLocations[path] = [...existing, lineNumber];
      }
    }
  }
  return { tests, summary, failureLocations };
}

/**
 * Run a Python string and return what it printed to stdout.
 * No pytest, no test discovery, no file system writes — used by the
 * Python Basics `predict` and `fillblank` lesson modes.
 */
export async function runPythonStdout(
  pyodide: PyodideInterface,
  code: string,
): Promise<{ stdout: string; error: string | null }> {
  const lines: string[] = [];
  const errLines: string[] = [];
  pyodide.setStdout({ batched: (s) => lines.push(s) });
  pyodide.setStderr({ batched: (s) => errLines.push(s) });
  try {
    await pyodide.runPythonAsync(code);
    return { stdout: lines.join("\n"), error: errLines.join("\n") || null };
  } catch (exc) {
    const message = exc instanceof Error ? exc.message : String(exc);
    return { stdout: lines.join("\n"), error: message };
  }
}

export async function runPytest(
  pyodide: PyodideInterface,
  pytestArgs: string[],
): Promise<PytestResult> {
  const lines: string[] = [];
  pyodide.setStdout({ batched: (s) => lines.push(s) });
  pyodide.setStderr({ batched: (s) => lines.push(s) });

  const argsLiteral = JSON.stringify([
    "-v",
    "--tb=short",
    "--no-header",
    ...pytestArgs,
  ]);

  const exit = await pyodide.runPythonAsync(`
import sys, os
sys.path.insert(0, "/home/pyodide")
os.chdir("/home/pyodide")
import pytest
exit_code = pytest.main(${argsLiteral})
int(exit_code)
`);

  const output = lines.join("\n");
  const { tests, summary, failureLocations } = parseVerboseOutput(output);

  return {
    exitCode: Number(exit),
    output,
    tests,
    summary:
      summary ||
      (Number(exit) === 0 ? "All tests passed" : "Some tests failed"),
    failureLocations,
  };
}
