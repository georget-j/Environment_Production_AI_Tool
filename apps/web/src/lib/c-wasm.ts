/**
 * Runner for pre-compiled C-to-WASM demos under /wasm/quant/{name}.{js,wasm}.
 *
 * Each demo is a self-contained Emscripten module: importing the .js side
 * exports a factory; calling the factory loads the .wasm, runs `main`, and
 * resolves. We hook `print` / `printErr` to capture stdout. The .wasm is
 * fetched relative to the .js URL automatically by the Emscripten runtime.
 *
 * Pre-built artefacts live under apps/web/public/wasm/quant/. Source lives
 * under c-demos/ and is rebuilt with `cd c-demos && make` (requires emsdk).
 */

const KNOWN_DEMOS = [
  "ring_buffer",
  "struct_layout",
  "lob_node",
  "cache_locality",
  "manual_vs_libc_strlen",
  "printf_internals",
] as const;

export type CWasmDemoSlug = (typeof KNOWN_DEMOS)[number];

type EmModuleFactory = (opts: {
  print?: (s: string) => void;
  printErr?: (s: string) => void;
}) => Promise<unknown>;

export function isCWasmDemo(slug: string): slug is CWasmDemoSlug {
  return (KNOWN_DEMOS as readonly string[]).includes(slug);
}

export async function runCWasmDemo(slug: CWasmDemoSlug): Promise<{
  stdout: string;
  error: string | null;
}> {
  const out: string[] = [];
  const errOut: string[] = [];
  try {
    // Vite/webpack can't statically follow `/wasm/quant/...` so use a
    // dynamic import. Next.js serves it from public/ at this URL.
    const url = `/wasm/quant/${slug}.js`;
    const mod = (await import(/* webpackIgnore: true */ url)) as {
      default: EmModuleFactory;
    };
    await mod.default({
      print: (s: string) => out.push(s),
      printErr: (s: string) => errOut.push(s),
    });
    const stdout = out.join("\n");
    const errs = errOut.join("\n").trim();
    return { stdout, error: errs || null };
  } catch (exc) {
    return {
      stdout: out.join("\n"),
      error: exc instanceof Error ? exc.message : String(exc),
    };
  }
}
