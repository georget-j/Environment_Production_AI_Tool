/**
 * Pyodide loader.
 *
 * Pyodide is heavy (~10 MB compressed). We load it from jsdelivr on first
 * use, not on page load. The loadPyodide() function is exposed by the
 * loader script we inject; we keep a single instance per page-session.
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
    // pytest is pure Python; install via micropip so we don't need a
    // pyodide-built distribution.
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
 * Paths like "tests/test_orders.py" auto-create the parent directory.
 */
export function writeTree(pyodide: PyodideInterface, files: Record<string, string>): void {
  for (const [path, body] of Object.entries(files)) {
    const segments = path.split("/");
    let cursor = "";
    for (let i = 0; i < segments.length - 1; i++) {
      cursor = cursor ? `${cursor}/${segments[i]}` : segments[i];
      if (!pyodide.FS.analyzePath(cursor).exists) {
        pyodide.FS.mkdir(cursor);
      }
    }
    pyodide.FS.writeFile(path, body);
  }
}

export type PytestResult = {
  exitCode: number;
  output: string;
};

export async function runPytest(
  pyodide: PyodideInterface,
  pytestArgs: string[],
): Promise<PytestResult> {
  const lines: string[] = [];
  pyodide.setStdout({ batched: (s) => lines.push(s) });
  pyodide.setStderr({ batched: (s) => lines.push(s) });

  const argsLiteral = JSON.stringify(pytestArgs);
  const exit = await pyodide.runPythonAsync(`
import pytest, os
os.chdir("/home/pyodide")
exit_code = pytest.main(${argsLiteral})
int(exit_code)
`);

  return { exitCode: Number(exit), output: lines.join("\n") };
}
