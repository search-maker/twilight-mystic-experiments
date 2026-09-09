# ARM ENA/SWS query-only -> E0 successor case freeze v1

## Purpose

This is a result-blind, zero-ARM-runtime preregistration boundary between the already-authorized one-shot query-only availability discovery and any later E0 successor proposal. It exists so the case used by a future E0 attempt is selected mechanically by the pre-frozen rule **first positive case in the ordered 25-case manifest**, rather than being chosen or retuned after query metadata are seen.

The tool does not contact ARM, download/open native files, inspect SWS/SASZE radiance, authorize Stage B, run MYSTIC/science, or authorize production. A successful freeze is only metadata/provenance evidence for a later separately reviewed E0 successor package.

## Frozen upstream identities

- query purpose: `ARM_ENA_SWS_V1_E0_SUCCESSOR_QUERY_ONLY_AVAILABILITY_DISCOVERY`
- datastream: `enaswsC1.b1`
- ordered manifest SHA-256: `8a0756be59dac59cd8ad4fab77e499ec19069e24d2d2a636fa4352713b550def`
- ordered case count: 25
- authorized query-only Coordinator comment: `5592250337`
- authorized dispatch ref: `refs/heads/main`
- authorized exact main: `5f3e3de7395ce20d79a210066d0836515d35996f`
- required query attempt: exactly `1`

The stress receipt must attest `EXACT_EXECUTABLE_STRESS_PASS` under `workflow_dispatch` on that exact ref/SHA and must retain every network/download/opening/science authority flag as false.

## Frozen E0 semantics carried forward, not re-authorized

A successful metadata freeze records the immutable source identities that a later E0 successor must preserve unless a separate review explicitly changes them:

- frozen E0 source ref: `review/arm-ena-sws-v1-stage0`
- frozen E0 source head: `b8671665a2bf8fe9972b8cb48492abcfa6765140`
- frozen 906-event universe SHA-256: `87933189ff56322ce2b5d2821a1c2ab8094d0a472ef6c690cfbd90cd0451fa41`
- frozen E0 protocol: `ARM_ENA_SWS_V1_STAGE0_E0_RESULT_BLIND_V2`
- frozen E0 control comment: `5487647692`

This freeze does **not** authorize reuse of the old hard-pinned `2017-06-16_dusk` portable wrapper or old postartifact verifier for a different selected case. If the query resolves another case, a future separately reviewed successor must bind that selected case while preserving the frozen E0 scientific logic and must use a case-bound strict postartifact verifier.

## Inputs and provenance requirements

The freeze command consumes:

1. extracted sanitized `query-only-receipt.json`;
2. extracted zero-runtime `stress-receipt.json` from the same workflow run;
3. the exact frozen `ordered_25_cases.json` bytes;
4. externally verified GitHub workflow run ID and `run_attempt=1`;
5. externally verified GitHub artifact IDs and `sha256:<digest>` values for both the query and stress artifacts.

The tool hashes both extracted receipts and records those hashes together with the externally supplied run/artifact identities. Supplying those command-line identities is not by itself proof that GitHub reported them; the operator/reviewer must obtain them from the GitHub control plane before invoking the freeze and preserve that readback as audit evidence.

## Admission rule

Only `FIRST_NATIVE_FILENAME_RESOLVED` is admissible. The receipt must prove:

- the exact ordered manifest identity and 25-case count;
- checked cases follow the frozen order from ordinal 1 without gaps;
- every earlier checked case has `match_count=0`;
- the final checked case has `match_count>0`;
- `first_match` is exactly that final case/date/ordinal;
- filenames are unique sorted basenames matching `enaswsC1.b1.<selected YYYYMMDD>...(.nc|.cdf)`;
- no query error exists;
- no native download/opening or protected-value/science/production flag is true.

`EXHAUSTED_25_NO_NATIVE_FILENAME_RESOLVED`, `QUERY_ERROR_FAIL_CLOSED`, non-attempt-1 runs, exact-main/ref drift, manifest drift, receipt widening, or provenance-field drift are refused and produce no E0 successor freeze.

## Output

A successful output is a closed metadata manifest with status `E0_SUCCESSOR_CASE_FROZEN`. It binds the selected ordinal/case/date/native basenames, both extracted receipt hashes, both GitHub artifact identities/digests, workflow run/attempt, query executable/workflow hashes from the stress receipt, and the frozen E0 source identities above.

The output permanently states false for:

- E0 scientific-semantics change authorization;
- native-file download/opening authorization;
- protected SWS/SASZE value reading;
- held-out radiance opening authorization;
- Stage B authorization;
- MYSTIC/science authorization;
- production authorization.

A freeze is therefore a preregistered successor-selection receipt only. Any actual native acquisition, E0 execution, protected opening, Stage B, MYSTIC/science, or production transition remains separately gated.
