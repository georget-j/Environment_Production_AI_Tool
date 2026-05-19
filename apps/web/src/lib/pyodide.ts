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

let pyodidePromise: Promise<PyodideInterface> | null = null;

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
    const existing = document.querySelector<HTMLScriptElement>("script[data-pyodide]");
    if (existing) {
      existing.addEventListener("load", () => resolve());
      existing.addEventListener("error", () => reject(new Error("Pyodide loader failed")));
      return;
    }
    const script = document.createElement("script");
    script.src = `${PYODIDE_INDEX_URL}pyodide.js`;
    script.async = true;
    script.dataset.pyodide = "1";
    script.addEventListener("load", () => resolve());
    script.addEventListener("error", () => reject(new Error("Pyodide loader failed")));
    document.head.appendChild(script);
  });
}

export async function getPyodide(): Promise<PyodideInterface> {
  if (pyodidePromise) return pyodidePromise;

  pyodidePromise = (async () => {
    await injectLoaderScript();
    if (!window.loadPyodide) {
      throw new Error("loadPyodide not exposed after script load");
    }
    const pyodide = await window.loadPyodide({ indexURL: PYODIDE_INDEX_URL });
    await pyodide.loadPackage(["micropip"]);
    const micropip = pyodide.pyimport("micropip");
    await micropip.install(["pytest"]);
    return pyodide;
  })().catch((exc) => {
    pyodidePromise = null;
    throw exc;
  });

  return pyodidePromise;
}

/**
 * Write a tree of files into Pyodide's in-memory filesystem.
 * Coerces every path to absolute so writes don't depend on cwd.
 */
export function writeTree(pyodide: PyodideInterface, files: Record<string, string>): void {
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

export type PytestResult = {
  exitCode: number;
  output: string;
  tests: TestRow[];
  summary: string;
};

// "tests/test_orders.py::test_compute_total_without_coupon PASSED  [ 14%]"
const VERBOSE_LINE_RE = /^(.+?::[\w[\]\-.]+)\s+(PASSED|FAILED|ERROR|SKIPPED)\b/i;

const STATUS_MAP: Record<string, TestStatus> = {
  PASSED: "passed",
  FAILED: "failed",
  ERROR: "error",
  SKIPPED: "skipped",
};

function parseVerboseOutput(text: string): { tests: TestRow[]; summary: string } {
  const tests: TestRow[] = [];
  let summary = "";
  for (const line of text.split("\n")) {
    const match = VERBOSE_LINE_RE.exec(line);
    if (match) {
      tests.push({ name: match[1].split("::").pop() ?? match[1], status: STATUS_MAP[match[2].toUpperCase()] });
      continue;
    }
    // Summary line: "= 1 failed, 4 passed in 0.42s ="
    if (/=+\s*\d+ (passed|failed|error|skipped)/.test(line)) {
      summary = line.replace(/=/g, "").trim();
    }
  }
  return { tests, summary };
}

export async function runPytest(
  pyodide: PyodideInterface,
  pytestArgs: string[],
): Promise<PytestResult> {
  const lines: string[] = [];
  pyodide.setStdout({ batched: (s) => lines.push(s) });
  pyodide.setStderr({ batched: (s) => lines.push(s) });

  const argsLiteral = JSON.stringify(["-v", "--tb=short", "--no-header", ...pytestArgs]);

  const exit = await pyodide.runPythonAsync(`
import sys, os
sys.path.insert(0, "/home/pyodide")
os.chdir("/home/pyodide")
import pytest
exit_code = pytest.main(${argsLiteral})
int(exit_code)
`);

  const output = lines.join("\n");
  const { tests, summary } = parseVerboseOutput(output);

  return {
    exitCode: Number(exit),
    output,
    tests,
    summary: summary || (Number(exit) === 0 ? "All tests passed" : "Some tests failed"),
  };
}
