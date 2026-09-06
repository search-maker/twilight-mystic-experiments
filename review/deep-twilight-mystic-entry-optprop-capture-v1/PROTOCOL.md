# Deep-twilight exact MYSTIC-entry optical-state capture v1

Status: **POST_V1 / NONBLOCKING / ZERO-SCIENCE CAPABILITY STAGE**.

This stage exists only to recover the lossless optical state presented by the exact pinned libRadtran runtime to MYSTIC for the historical bare-Shettle atmosphere. It does not execute the MYSTIC body, trace a photon, allocate or consume a science identity/seed/ordinal, open any protected result, change Level-B, or authorize an independent renderer.

## Frozen runtime and atmosphere

- base commit: `fe6e063c568394ae7b4e90222de270d3f2460455`
- exact package: `rubin-libradtran=2.0.6=py312pl5321he9373c2_1`
- exact `uvspec` SHA-256: `2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3`
- AFGL-US atmosphere; no OPAC/species override
- aerosol directives: exactly `aerosol_default` plus `aerosol_set_tau_at_wvl 550 0.150000`
- diagnostic wavelength: 550 nm
- setup-only geometry: `sza 80`, `albedo 0.15`; it has no deep-twilight interpretation

The input deliberately matches the unamplified `f1` state preregistered by the earlier bare-Shettle NULL capability work. No 100x/10000x amplification is used.

## Exact-runtime route

The governing source archive remains byte-unrecovered. Instead, use the already-demonstrated exact-pinned debugger boundary method: install and hash the exact package, locate the `mystic` symbol in that exact `uvspec`, break at the function entry, capture the incoming ABI state, and kill the inferior **before the first MYSTIC instruction executes**.

The public 2.0.6-family source mirror is used only to preregister the candidate ABI contract, never as byte-equivalent governing source. Its MYSTIC prototype begins with:

`nlyr*`, `n_caoth`, `dt_s**`, `om_s**`, `g1_s**`, `g2_s**`.

On x86-64 SysV these first six integer-class arguments are expected in `rdi,rsi,rdx,rcx,r8,r9`. The exact pinned binary must independently prove that a `mystic` symbol exists; if symbol/ABI shape or pointer plausibility does not match, the stage fails closed rather than guessing offsets.

## Lossless capture and claim boundary

Capture, without decimal formatting:

- exact `nlyr` and `n_caoth` values;
- the raw pointer table for each of `dt_s`, `om_s`, `g1_s`, `g2_s`;
- for every component row, exactly `nlyr` native `float32` words as raw little-endian bytes/hex plus a decoded value only for audit convenience;
- exact input/runtime/package/hash provenance and the `mystic` symbol evidence.

No printed verbose zero is promoted to a physical zero. A zero is called exact only when its captured native word is exactly `0x00000000` (or signed-zero bit pattern recorded explicitly); all native bits are retained. No epsilon substitution is permitted.

This first capability stage intentionally captures **all component rows without semantically relabeling them**. Aerosol-row mapping, layer-boundary capture (`zprof`), phase-function payloads, AOD/SSA/g translation, and independent-renderer parity remain separate gates. A successful capture proves only that the exact final pre-MYSTIC optical arrays are losslessly accessible without running MYSTIC.

## Fail-closed rules

Fail if any of these occur: wrong package/hash/architecture/ref/attempt; no unique exact `mystic` symbol; breakpoint not hit; MYSTIC body executes; `nlyr` or `n_caoth` is implausible; any row pointer is null/unreadable; raw byte lengths differ from `4*nlyr`; or evidence cannot be serialized without altering the raw words.

Never GitHub Re-run/retry/resume this attempt. A defect requires a fresh successor identity and fresh preregistration. This stage is independent of Taylor/Jerusalem and of the V1 CRS<->REPTRAN campaign.