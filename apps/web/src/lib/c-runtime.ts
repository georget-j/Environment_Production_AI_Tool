/**
 * C runtime — runs editable C lessons in the browser via picoc-js.
 *
 * picoc-js is the canonical picoc C interpreter (~3500 lines of real C
 * compiled to ~1.5MB WASM). It supports the C subset we need for quant
 * lessons: stdio (`printf`, `scanf`), control flow, arrays, pointers,
 * structs, manual memory (`malloc`/`free`), function pointers, and the
 * basics of `<string.h>`, `<math.h>`, `<stdlib.h>`. It does NOT support
 * threads, file I/O beyond stdin/stdout, system calls, or unbounded
 * recursion (the interpreter stack is small — teach iterative versions).
 *
 * The published npm bundle imports Node-only modules at parse time, so
 * we don't bundle it; instead we load the UMD build from jsdelivr at
 * runtime and grab `window.picocjs.runC`. Same CDN as Pyodide.
 *
 * picoc's `runC` is fire-and-forget; output and errors both come back
 * via a single `consoleWrite(s)` callback. Errors are formatted as
 *   <source line>
 *   <caret>
 *   file.c:LINE:COL message
 * We detect that prefix and surface it as an error.
 */

const PICOC_VERSION = "1.0.12";
// Self-hosted UMD bundle (vendored under apps/web/public/vendor/). We
// avoid CDN dependencies at runtime — same trade-off as our WASM C demos.
const PICOC_UMD_URL = "/vendor/picoc.umd.js";
const RUNTIME_TIMEOUT_MS = 2500;
const SETTLE_DELAY_MS = 200;
const ERROR_LINE_RE = /^file\.c:\d+:\d+\s/m;

const UNSUPPORTED_INCLUDE_RE =
  /#\s*include\s*[<"](pthread\.h|unistd\.h|sys\/.*|signal\.h|fcntl\.h|dirent\.h|netinet\/.*|sys\/socket\.h)[>"]/;

export function detectUnsupportedC(code: string): string | null {
  const m = UNSUPPORTED_INCLUDE_RE.exec(code);
  if (m) {
    return `This sandbox runs a small in-browser C interpreter and can't include <${m[1]}>. Real C compiles ahead-of-time with gcc/clang and has the full system surface; here we're limited to stdio, math, string, and stdlib. Try a different approach for this lesson.`;
  }
  return null;
}

export type CRunResult = {
  stdout: string;
  error: string | null;
};

type PicocApi = {
  runC(code: string, consoleWrite: (s: string) => void): void;
};

let picocPromise: Promise<PicocApi> | null = null;

/** Load picoc into the page. We fetch the bundle body and run it via an
 *  INLINE script element — that's executed synchronously when appended,
 *  so we never have to negotiate with `script.onload` event timing.
 *  After the inline script runs, `window.picocjs.runC` is set. */
async function loadPicoc(): Promise<PicocApi> {
  if (picocPromise) return picocPromise;
  if (typeof window === "undefined") {
    throw new Error("C runtime only loads in the browser");
  }
  const w = window as typeof window & { picocjs?: PicocApi };
  if (w.picocjs?.runC) {
    picocPromise = Promise.resolve(w.picocjs);
    return picocPromise;
  }
  picocPromise = (async () => {
    const res = await fetch(PICOC_UMD_URL, { credentials: "omit" });
    if (!res.ok) {
      throw new Error(`HTTP ${res.status} loading ${PICOC_UMD_URL}`);
    }
    const body = await res.text();
    const inline = document.createElement("script");
    inline.dataset.picoc = PICOC_VERSION;
    inline.text = body;
    // Appending an inline script with text-content runs it synchronously
    // (per HTML spec). After this line, the UMD's IIFE has finished and
    // window.picocjs is populated.
    document.head.appendChild(inline);
    if (!w.picocjs?.runC) {
      throw new Error("picoc bundle evaluated but window.picocjs is missing");
    }
    return w.picocjs;
  })().catch((exc) => {
    picocPromise = null;
    throw exc;
  });
  return picocPromise;
}

export async function runC(code: string): Promise<CRunResult> {
  const unsupported = detectUnsupportedC(code);
  if (unsupported) {
    return { stdout: "", error: unsupported };
  }
  let picoc: PicocApi;
  try {
    picoc = await loadPicoc();
  } catch (exc) {
    return {
      stdout: "",
      error: `Couldn't load the C runtime: ${exc instanceof Error ? exc.message : String(exc)}`,
    };
  }
  return new Promise<CRunResult>((resolve) => {
    const chunks: string[] = [];
    let settleTimer: ReturnType<typeof setTimeout> | null = null;
    let resolved = false;

    const finish = () => {
      if (resolved) return;
      resolved = true;
      if (settleTimer) clearTimeout(settleTimer);
      clearTimeout(hardCap);
      const joined = chunks.join("\n");
      const errMatch = ERROR_LINE_RE.exec(joined);
      if (errMatch) {
        const errStart = errMatch.index;
        const stdout = joined
          .slice(0, errStart)
          .replace(/(^|\n)[^\n]*\n[^\n]*\^\s*$/, "");
        const error = friendlyCError(joined.slice(errStart));
        resolve({ stdout: stdout.trim(), error });
        return;
      }
      resolve({ stdout: joined, error: null });
    };

    const hardCap = setTimeout(() => {
      if (chunks.length === 0) {
        resolved = true;
        resolve({
          stdout: "",
          error:
            "Your program ran for too long (>2.5s). Check for an infinite loop or runaway recursion — the in-browser C interpreter has a small stack and doesn't do deep recursion.",
        });
      } else {
        finish();
      }
    }, RUNTIME_TIMEOUT_MS);

    try {
      picoc.runC(code, (s: string) => {
        chunks.push(s);
        if (settleTimer) clearTimeout(settleTimer);
        settleTimer = setTimeout(finish, SETTLE_DELAY_MS);
      });
    } catch (exc) {
      clearTimeout(hardCap);
      resolved = true;
      resolve({
        stdout: chunks.join("\n"),
        error: exc instanceof Error ? exc.message : String(exc),
      });
    }
  });
}

function friendlyCError(raw: string): string {
  return raw
    .split("\n")
    .map((line) => line.replace(/^file\.c:/, "line "))
    .join("\n")
    .trim();
}

/** Wipe the lazy picoc cache. Forces the next call to re-resolve. */
export function resetCRuntime(): void {
  picocPromise = null;
}
