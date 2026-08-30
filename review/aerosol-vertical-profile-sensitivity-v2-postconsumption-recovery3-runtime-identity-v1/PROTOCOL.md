# AVPS v2 recovery3 ordinal-44 runtime-identity mechanical gate

Status: **ZERO-RUNTIME REVIEW ONLY**. Controlling defect: Issue #60 comment `5470658421`.

The package on main `e9f79772f07e2a90974979f187be137606c3dfea` is `NOT_ADMISSIBLE` for dispatch because its science workflow calls executor blob `bb1e4276d6383127a6b7e820fc2568d87d5de4b0` and aggregator blob `ef24a0d30af3dfb46a6b764f3e426465da870fbe`, whose identity guards are frozen to ordinal 41. Publisher run `33329476520` attempt 1 is immutable failure evidence and must never be rerun.

This gate does not change the scientific experiment. It preserves exactly 360 cases, 72 CRN groups, five profile states, 20,000,000 photon histories per case, the existing spectra/geometry/estimator/thresholds, the already-reviewed recovery3 seed set, and Draft authorization PR #718 head `dd3a4c692af505389e9feb1e5f5480fa389110a3`. It creates no dispatch/consumed marker, runs no libRadtran/MYSTIC/uvspec, opens no result or holdout, uses no Taylor/Jerusalem residual or invalidated low-alt evidence, and authorizes no richer Level-B mapping.

`generate.py` produces three deterministic runtime wrappers. They bind the already-reviewed executor, aggregator and adapter mechanics to the exact recovery3 ordinal-44 stage/guard/authorization/seed/branch identities while leaving underlying rendering, one-syntax/one-solver execution, raw-spectrum/channel derivation, and closed-aggregate algorithms unchanged. The recovery3 adapter reconstructs the already-reviewed 72 seeds deterministically from the frozen namespace and verifies the frozen seed and row canonical hashes; freshness remains separately enforced by the existing pre-solver repository-global guard.

The executable review must prove all of the following before any publication successor is allowed:

1. exact PR #718 recovery3 authorization is accepted and an ordinal-41 authorization is refused;
2. exact recovery3 guard status, authorization head/PR, ordinal 44, execution key, seed hash, authorization branch and dispatch branch are enforced, and the old ordinal-41 guard is refused;
3. the authorized universe is exactly 360 cases / 72 CRN groups / five states per group with one shared seed per CRN group;
4. the unchanged closed-aggregate accounting accepts an exact synthetic 360-case universe, yields 24 analysis cells and closed-result statuses, and refuses 359 cases;
5. review mode refuses before solver execution; no runtime, result opening, Level-B admission, protected holdout or production transition occurs.

After this gate passes and is independently reviewed, the next step is a **separate fresh publication/trigger identity** that publishes exact reviewed wrapper bytes and updates the recovery3 science workflow to pin/use those bytes. The old current execution package remains `DO NOT USE` until that later publication is reviewed. No dispatch is authorized by this gate.
