# AVPS v2 disabled control package review v1

Status: **REVIEW ONLY / DISABLED PACKAGE / NO ORDINAL / NO AUTHORIZATION / NO SOLVER**

## Purpose

Freeze the exact non-executing control/package bytes that will later support a separately reviewed AVPS v2 authorization and execution-transport layer. This stage exists so ordinal 41 is not allocated before the corrected four-species case surface, runtime staging boundary, seed application boundary and profile-byte checks are independently reviewable.

## Scientific design is already frozen elsewhere

This PR must not change the #597 science:

- stage `aerosol-vertical-profile-sensitivity-v2`;
- 360 cases / 72 CRN groups / 5 states per group;
- AOD550 0.10 and 0.30;
- sun depression 2, 4, 6, 8 deg;
- three frozen geometries;
- three replicates;
- 20,000,000 photons per case;
- fixed OPAC `continental_average` optical family;
- exact explicit profile surface `INSO WASO SOOT SUSO`;
- no `aerosol_file tau`;
- no Taylor/Jerusalem fitting.

## Exact predecessor evidence

- frozen main `99ade7798627e67921139697ba1a004fa8a304bb`
- #596 renderer head `8adfd4fafa4c039394d12e6f6aff1795b750f4d2`; renderer blob `99f61e1daa03cecef055a3773544574738d65082`; run `33193123594`; contract `33193123597`; artifact `9694613680`; digest `sha256:5e6942d879326ffc2dc8805d7649086cae32ad2e16aeec19a62cd3b0a89e3e27`
- #597 prereg head `2bba54c6e78ed99d169887eef51d0c88d812b6f1`; run `33193778176`; contract `33193778174`; artifact `9694863701`; digest `sha256:7de79aa4d8d9b51ad8ca4b1bdaceedae7ee5df17b3dd79c43c21cdaf9ae9a171`; skeleton canonical `a8d2d8f59aec01d82d8d98672152d00c11261660b0a69a59e2716c2edabd2b02`
- #598 seed head `64e7d68bd876a99aa5af49d97bcb53718238b39b`; run `33194319669`; contract `33194319698`; artifact `9695260362`; digest `sha256:fb4613d654121098c9d247d6ed8b0f0788b26a179b5ff103dc01ed7d50c9f0db`; seed canonical `02f624d582e9b2caba6b920d65a5e8a8bc8fc1a2693623bc2f73abf5d3f706d2`; rows canonical `41f70d6a0381db6b569d3f4e17d74bb38b05cf212c2f2e432455a502f73dc670`
- #599 preauthorization head `a4e4700babddf0924135f5cc6ec6bfd21d8c9ec2`; run `33203372878`; contract `33203372798`; artifact `9699064164`; digest `sha256:b1125375bae24638375853d3724c1c96ba1572dc02e1619eff37d9fdca70b92e`; report SHA `31db5d10eeff3a18f6d41af3a665818b0b53b1d6187d93263f5988c4229385cd`

#599 proved only that 40 remains latest consumed/max authoritative and 41 is next available. It did not allocate or reserve 41.

## Exact bytes bound in this review

- #597 protocol blob `d790fb3fa2d214d1f430f4417b17212a8e5038a8`
- #597 skeleton builder blob `b4a4ab6917ad28f08d4980194f7b68f3961d5d59`
- #598 deterministic seed-ledger blob `c757507b05074340507df1ca6e76d35b44cf6090`
- #598 tracked-tree scanner blob `3aa311db5c49c5dcf2bd12446f5e96b347080e96`
- #596 renderer blob `99f61e1daa03cecef055a3773544574738d65082`
- #595 OPAC/RH staging helper blob `095ff86f12a79dc312a51f734b0a03bd318f2337`
- frozen wavelength grid blob `3bb3db96580d555ef758f57cabd6cac55b61cebb`

## Exact profile hashes

- continental average `ceed598f7681951cd0e6208b267beb5b41a52ab10311f37ce76f925700caff3d`
- maritime clean `487b67bd7dbe89d12d032fdf2b33cab545e16a2e0697170648317f1a76362a67`
- desert `2b4d2e03c6ae3143d9bb05d2da49f57f75172dc1f24d34f7d4a4939bf9952fef`
- arctic `98f2fa5428c830764252fd0a2662b0f5c957fc027ffcb7bdc0a5e500dfd7d3d6`
- antarctic `ee063c6dca68cf9a31d8bb9d993f1fed5cb34c8bb056ac180c97171b5d6b4f19`

## Review requirements

The dedicated review must prove without installing/running libRadtran:

1. exact predecessor PR/run/contract/artifact identities remain PASS and Draft/open/unmerged;
2. vendored prerequisite bytes are exact Git-blob matches;
3. the disabled package is exactly 360 cases / 72 groups / 5 states and contains no seed values, ordinal, authorization or executable solver permission;
4. every case keeps the fresh `avps-v2-` identity and exact pre-seed science surface;
5. every case has exactly one four-species `aerosol_species_file` and no `aerosol_file` directive;
6. candidate seed derivation still has the exact 72-count/canonical hashes, but review output must never serialize or print the 72 values;
7. a fresh tracked-tree candidate literal scan over this exact head finds zero candidate seed literals;
8. the adapter refuses any missing/malformed authorization and only applies group seeds in memory after a future authorization document passes exact binding checks;
9. runtime staging is bound to the frozen archive, uvspec, AFGL, pre-alias and four-alias data-tree identities, but this review does not download the archive or run any solver;
10. no active authorization, dispatch or scientific execution workflow is added here.

## PASS meaning

PASS means only that the disabled v2 package/adapter/runtime-staging surface is safe to use as an input to a later, separate execution-transport/authorization review.

PASS does not allocate ordinal 41, does not apply candidate seeds to cases, and does not authorize solver execution.

## Hard prohibitions

- no branch beginning `authorization/` or `dispatch/` from this review;
- no ordinal-41 Issue marker;
- no actual candidate seed values tracked or emitted in review artifacts;
- no `uvspec`, NULL, DISORT or MYSTIC;
- no active science workflow;
- no `aerosol_file tau`;
- no v1 case IDs, v1 seed namespace or ordinal-40 identity reuse;
- no Taylor/Jerusalem scoring;
- no Level-B/production action;
- no GitHub Re-run if a review/control defect is found.
