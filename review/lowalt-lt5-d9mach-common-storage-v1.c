#include <stdint.h>

/*
 * PRE-RESULT ABI STORAGE SHIM ONLY.
 *
 * Authoritative libRadtran 2.0.6 d1mach.f declares:
 *   INTEGER CRAY1(38)
 *   COMMON /D9MACH/ CRAY1
 *
 * The selected Flang wasm32 object leaves the COMMON storage symbol
 * `d9mach_` undefined at final WebAssembly link.  This translation unit
 * materializes exactly 38 default-Fortran-INTEGER-sized (32-bit on the
 * frozen wasm32 ABI) storage cells under that external symbol.  It does
 * not implement D1MACH, initialize machine constants, call T, or produce
 * any scientific result.  Numerical/semantic admissibility remains
 * conditional on the separately frozen exact-source comparator C.
 */
int32_t d9mach_[38];
