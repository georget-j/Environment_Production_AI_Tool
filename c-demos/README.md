# c-demos — pre-compiled C-to-WASM demos for the Quant track

These C programs back the quant track's `cwasm` lessons — read-only
worked examples a learner reads, then clicks Run to execute compiled
(real `-O3`) WASM and see the output. Unlike the editable `cscript`
lessons (which use the picoc interpreter and don't represent real
performance), these are the lessons where the timing numbers matter.

## Building

```bash
# one-time: install emsdk (see https://emscripten.org)
git clone https://github.com/emscripten-core/emsdk ~/.emsdk
cd ~/.emsdk && ./emsdk install latest && ./emsdk activate latest

# every build:
source ~/.emsdk/emsdk_env.sh
cd c-demos
make            # writes .js + .wasm into ../apps/web/public/wasm/quant/
make clean
```

Both the `.js` and `.wasm` artefacts under `apps/web/public/wasm/quant/`
are committed so the deploy is self-contained — emsdk is **not** a
runtime dependency, only a build-time one.

## Demos

| Slug                    | Teaches                                  | Used by lesson |
| ----------------------- | ---------------------------------------- | -------------- |
| `ring_buffer`           | wrap-around indices, full/empty          | 45             |
| `struct_layout`         | sizeof + padding (cache-line economics)  | 42             |
| `lob_node`              | sorted linked list, top-of-book          | 37, 45         |
| `cache_locality`        | row-major vs column-major sum timing     | 8 (Stage 1)    |
| `manual_vs_libc_strlen` | hand-rolled loop vs SIMD-vectorised libc | 46             |
| `printf_internals`      | format specifiers (%d %f %x %p, widths)  | predict drills |

Each is small, self-contained, and prints its result via `printf` so
the JS-side runner can pick it up via `Module.print`.

## Why pre-compiled WASM + a separate `cscript` runtime?

- **`cscript`** (in-browser picoc interpreter) lets learners _write_
  C — supports `printf`, structs, pointers, malloc/free — but it's
  interpreted, so it can't honestly demonstrate the "compiled is
  fast" story.
- **`cwasm`** (these demos) lets learners _read + run_ the C that
  matters for performance lessons; the timings reported are real.

Together they cover both pedagogical needs without shipping a full
in-browser C compiler.
