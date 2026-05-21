# Build the read-only "cwasm" lesson demos with Emscripten.
#
# emsdk must be sourced before invoking make:
#   source ~/.emsdk/emsdk_env.sh
#   make            # build everything into apps/web/public/wasm/quant/
#   make clean
#
# Each demo compiles to a single ES-module JS file + a sibling .wasm.
# The web app's c-wasm runner does `import(...)` against the .js, sets
# `Module.print` to capture stdout, and the demo's main() runs as part
# of module load. -O3 keeps the demos honest about the perf story we're
# telling in the curriculum.

OUT     := ../apps/web/public/wasm/quant
DEMOS   := ring_buffer struct_layout lob_node cache_locality manual_vs_libc_strlen printf_internals

EMCC_FLAGS := \
  -O3 \
  -s ENVIRONMENT=web \
  -s MODULARIZE=1 \
  -s EXPORT_ES6=1 \
  -s EXPORTED_RUNTIME_METHODS='["print","printErr"]' \
  -s ALLOW_MEMORY_GROWTH=1 \
  -s SINGLE_FILE=0

.PHONY: all clean
all: $(addprefix $(OUT)/, $(addsuffix .js, $(DEMOS)))

$(OUT)/%.js: %.c | $(OUT)
	emcc $< $(EMCC_FLAGS) -s EXPORT_NAME='create_$*' -o $@

$(OUT):
	mkdir -p $(OUT)

clean:
	rm -f $(OUT)/*.js $(OUT)/*.wasm
