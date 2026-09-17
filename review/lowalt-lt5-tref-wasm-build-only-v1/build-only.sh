#!/usr/bin/env bash
set -euo pipefail

SRC="${1:?source dir required}"
OUT="${2:?output dir required}"
OBJ="$OUT/object"
DIST="$OUT/generated"
rm -rf "$OUT"
mkdir -p "$OBJ" "$DIST"

for file in geofast_exact.f direct_ref_full.f DISORT.MXD; do
  test -f "$SRC/$file"
done
(
  cd "$SRC"
  echo 'a3d177f64a44f77227aa3a6774fc4ea744da1b9cc88a0059632b598bd4c8a1ac  geofast_exact.f' | sha256sum -c -
  echo '4f172445b795f8e3cb60f41f2c74835a4dd5978673d57b3c1f5aa82c78f7574c  direct_ref_full.f' | sha256sum -c -
  echo '9cf3f04bac9703b302a13b29eb1df11ea3200a992bc50ab3fa947d1d83c71f69  DISORT.MXD' | sha256sum -c -
)

if [[ -f /opt/emsdk/emsdk_env.sh ]]; then
  # shellcheck disable=SC1091
  source /opt/emsdk/emsdk_env.sh >/dev/null
fi
FLANG="$(command -v flang-new || command -v flang || true)"
if [[ -z "$FLANG" && -x /opt/flang/host/bin/flang ]]; then FLANG=/opt/flang/host/bin/flang; fi
if [[ -z "$FLANG" && -x /opt/flang/host/bin/flang-new ]]; then FLANG=/opt/flang/host/bin/flang-new; fi
EMCC="$(command -v emcc || true)"
if [[ -z "$EMCC" && -x /opt/emsdk/upstream/emscripten/emcc ]]; then EMCC=/opt/emsdk/upstream/emscripten/emcc; fi
[[ -n "$FLANG" ]] || { echo 'refusal: flang unavailable' >&2; exit 42; }
[[ -n "$EMCC" ]] || { echo 'refusal: emcc unavailable' >&2; exit 43; }

"$FLANG" --version > "$DIST/flang-version.txt" 2>&1
"$EMCC" --version > "$DIST/emcc-version.txt" 2>&1
"$FLANG" -c -O3 --target=wasm32-unknown-emscripten -I"$SRC" -o "$OBJ/geofast_exact.o" "$SRC/geofast_exact.f"
"$FLANG" -c -O3 --target=wasm32-unknown-emscripten -I"$SRC" -o "$OBJ/direct_ref_full.o" "$SRC/direct_ref_full.f"

# Prefer the wasm-aware LLVM utilities shipped by the exact Emscripten toolchain.
# A host llvm-nm can reject wasm32 object files even though compilation itself succeeded.
NM=""
if [[ -x /opt/emsdk/upstream/bin/llvm-nm ]]; then
  NM=/opt/emsdk/upstream/bin/llvm-nm
elif command -v emnm >/dev/null 2>&1; then
  NM="$(command -v emnm)"
elif command -v llvm-nm >/dev/null 2>&1; then
  NM="$(command -v llvm-nm)"
elif command -v nm >/dev/null 2>&1; then
  NM="$(command -v nm)"
fi
[[ -n "$NM" ]] || { echo 'refusal: wasm-capable nm unavailable' >&2; exit 44; }
printf '%s\n' "$NM" > "$DIST/nm-tool.txt"
"$NM" "$OBJ/direct_ref_full.o" > "$DIST/direct-ref-symbols.txt"
DIRECT_SYMBOL="$(awk '$NF ~ /direct_ref_full/ && $2 ~ /[Tt]/ {print $NF; exit}' "$DIST/direct-ref-symbols.txt")"
if [[ -z "$DIRECT_SYMBOL" ]]; then DIRECT_SYMBOL="$(awk '$NF ~ /direct_ref_full/ {print $NF; exit}' "$DIST/direct-ref-symbols.txt")"; fi
[[ -n "$DIRECT_SYMBOL" ]] || { echo 'refusal: direct_ref_full symbol not found' >&2; exit 45; }
[[ "$DIRECT_SYMBOL" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || { echo "refusal: unsupported symbol $DIRECT_SYMBOL" >&2; exit 46; }

cat > "$OBJ/wasm_export.c" <<EOF
#include <stdint.h>
#include <emscripten/emscripten.h>
extern void ${DIRECT_SYMBOL}(int32_t*, double*, double*, double*, double*, double*, int32_t*, int32_t*, double*, double*, double*, double*);
EMSCRIPTEN_KEEPALIVE
void lt5_tref_direct_ref_full(int32_t *nlyr, double *dtauc, double *zd, double *vn, double *umu0, double *radius,
                              int32_t *nfacout, int32_t *nfac2out, double *facout, double *fac2out,
                              double *chpout, double *chout) {
  ${DIRECT_SYMBOL}(nlyr, dtauc, zd, vn, umu0, radius, nfacout, nfac2out, facout, fac2out, chpout, chout);
}
EOF
"$EMCC" -c -O3 -o "$OBJ/wasm_export.o" "$OBJ/wasm_export.c"

RUNTIME_LIB="$(find /opt/flang -path '*wasm*' -name libFortranRuntime.a -print -quit)"
if [[ -z "$RUNTIME_LIB" ]]; then RUNTIME_LIB="$(find /opt/flang -name libFortranRuntime.a -print -quit)"; fi
[[ -n "$RUNTIME_LIB" ]] || { echo 'refusal: Fortran runtime unavailable' >&2; exit 47; }
RUNTIME_DIR="$(dirname "$RUNTIME_LIB")"
mapfile -t RUNTIME_LIBS < <(find "$RUNTIME_DIR" -maxdepth 1 -name '*.a' -print | sort)
[[ ${#RUNTIME_LIBS[@]} -gt 0 ]] || { echo 'refusal: no runtime libraries' >&2; exit 48; }
printf '%s\n' "${RUNTIME_LIBS[@]}" > "$DIST/fortran-runtime-libraries.txt"

"$EMCC" "$OBJ/geofast_exact.o" "$OBJ/direct_ref_full.o" "$OBJ/wasm_export.o" "${RUNTIME_LIBS[@]}" \
  -O3 -s MODULARIZE=1 -s EXPORT_NAME=Lt5TRefModule -s EXPORT_ES6=1 -s ALLOW_MEMORY_GROWTH=1 \
  -s 'EXPORTED_FUNCTIONS=["_lt5_tref_direct_ref_full","_malloc","_free"]' \
  -s ERROR_ON_UNDEFINED_SYMBOLS=1 -o "$DIST/lt5-tref.mjs"

# PRE-RESULT BUILD-ONLY. Do not instantiate or invoke generated WebAssembly.
sha256sum "$SRC/geofast_exact.f" "$SRC/direct_ref_full.f" "$SRC/DISORT.MXD" \
  "$OBJ/geofast_exact.o" "$OBJ/direct_ref_full.o" "$OBJ/wasm_export.c" "$OBJ/wasm_export.o" \
  "$DIST/lt5-tref.mjs" "$DIST/lt5-tref.wasm" > "$DIST/sha256sums.txt"

python3 - "$DIST/build-receipt.json" "$DIRECT_SYMBOL" <<'PY'
import json, os, pathlib, sys
out, sym = sys.argv[1:]
receipt = {
  'schemaVersion': 1,
  'classification': 'PRE_RESULT_BUILD_ONLY_T_REFERENCE_WASM_FEASIBILITY',
  'sourceHead': os.environ.get('GITHUB_SHA'),
  'runId': os.environ.get('GITHUB_RUN_ID'),
  'runAttempt': os.environ.get('GITHUB_RUN_ATTEMPT'),
  'directRefFullLinkSymbol': sym,
  'wasmInstantiated': False,
  'wasmExecuted': False,
  'solverExecuted': False,
  'lt5SpectrumConstructed': False,
  'comparatorExecuted': False,
  'benchmarkExecuted': False,
  'bSelected': False,
  'productionAuthorized': False,
}
pathlib.Path(out).write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n')
PY
sha256sum "$DIST/build-receipt.json" >> "$DIST/sha256sums.txt"

tar -C "$OUT" -czf "$OUT/lt5-tref-wasm-build-only-v1.tar.gz" generated
base64 -w0 "$OUT/lt5-tref-wasm-build-only-v1.tar.gz" > "$OUT/lt5-tref-wasm-build-only-v1.tar.gz.b64
sha256sum "$OUT/lt5-tref-wasm-build-only-v1.tar.gz" "$OUT/lt5-tref-wasm-build-only-v1.tar.gz.b64" > "$OUT/bundle-sha256.txt"
echo PRE_RESULT_BUILD_ONLY_SUCCESS
