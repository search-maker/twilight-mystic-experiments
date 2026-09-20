# Deep-twilight bare-Shettle serializer ABI capability v1

Status: **zero-RTE / zero-radiance capability inventory only**. This stage exists because the fixed `aerosol_set_tau_at_wvl` amplification route was rejected by run `33344214351` / artifact `9741463658`: for bare historical `aerosol_default`, changing AOD changes the internally inferred visibility and redistributes the aerosol profile, so amplified runs are not higher-precision observations of the same optical state.

This stage does not run `uvspec`, MYSTIC, Eradiate, or any radiative-transfer solver. It allocates no scientific ordinal or seed and opens no deep-twilight value.

## Frozen objective

Determine, before designing or executing a serializer, whether the exact installed `rubin-libradtran=2.0.6=py312pl5321he9373c2_1` package exposes enough headers and library symbols to build an **external diagnostic helper** against the already-installed runtime libraries, rather than rebuilding or modifying the locked production `uvspec` executable.

The desired future serializer state is the final **unamplified**, post-aerosol-setup/post-redistribution aerosol optical state for bare `aerosol_default` at the historical atmosphere/AOD configuration. This ABI inventory does not access that state yet.

## Frozen runtime identity

- package: `rubin-libradtran=2.0.6=py312pl5321he9373c2_1`
- locked `uvspec` SHA-256: `2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3`
- locked libRadtran data-tree SHA-256: `ad30b49177e9c84e46497d69faf0c75e466996b0d0003f1de210289ae9f847d7`
- conda-forge recipe source: official `libRadtran-2.0.6.tar.gz`, source SHA-256 `999e47f4af4b5df6f85a6887fc105fc8f6e1a7cee89a3124f69ac8d8912c8e85`

The current conda-forge recipe contains no source patch files; its build script configures, builds, tests, and runs `make install`. The package recipe explicitly tests for installed `libRadtran_c.a` and `libRadtran_f.a`. This provenance is a feasibility premise only, not proof that the required high-level setup/state symbols are externally callable.

## Exact inventory

A single GitHub-hosted job may install the exact package and then perform **filesystem/symbol inspection only**:

1. verify locked runtime/data hashes with the existing no-solver runtime probe;
2. enumerate `$CONDA_PREFIX/include/libRadtran` and relevant `$CONDA_PREFIX/include` headers;
3. enumerate `$CONDA_PREFIX/lib/libRadtran*` libraries and hashes;
4. record global defined symbols from `libRadtran_c.a`, `libRadtran_f.a`, and, if present, `libRadtran.so`;
5. record the non-debug symbol table of the installed `uvspec` executable without executing it;
6. search the installed headers and symbol inventories using the preregistered strings `aerosol`, `optprop`, `optical`, `redistrib`, `setup_aer`, `uvspec`, `input_struct`, and `output_struct`;
7. record exact package metadata from `$CONDA_PREFIX/conda-meta/rubin-libradtran-2.0.6-py312pl5321he9373c2_1.json`.

No adaptive second search vocabulary is permitted in this capability run. The full raw header/file/symbol inventories are preserved so later source design can be audited without rerunning this identity.

## Classification

After the artifact is terminal, classify manually from the frozen inventory only:

- `EXTERNAL_HELPER_PATH_PLAUSIBLE`: installed headers plus installed libraries expose a plausible supported route to instantiate/setup the needed structures and read the final aerosol optical state without modifying `uvspec`;
- `INSTRUMENTED_SOURCE_PATH_REQUIRED`: the required state/setup interfaces are internal/not exported, so the serializer must instead use a separately frozen diagnostic source-instrumentation route;
- `ABI_CAPABILITY_UNRESOLVED`: inventory is incomplete or package identity differs.

This inventory itself cannot authorize compilation of a serializer. Whichever path is selected must get a separate preregistration that freezes output schema, hook location/API, numerical precision, unamplified atmosphere/AOD inputs, state-timing assertion (after redistribution, before RTE), and a no-RTE execution proof before values.

## Future serializer minimum schema

Before a serializer is executed, its schema must at minimum freeze: wavelength; layer index and exact layer boundaries/altitudes; aerosol extinction optical depth per layer; aerosol single-scattering albedo per layer; the actual phase representation consumed by scalar MYSTIC for the historical configuration (at minimum `g` if the runtime state is exactly Henyey-Greenstein, otherwise the full represented moments/phase data); aggregate AOD checks; runtime/source/library hashes; and explicit `rteSolverExecuted=false`, `mysticExecuted=false`, `scientificOrdinalAllocated=false` claim-boundary fields. Values must be serialized in binary64/hex-float or equivalent lossless precision, not the rounded verbose table.

## Boundaries

No amplified Shettle values may be used to reconstruct the unamplified state. No Taylor/Jerusalem or desired application residual enters this stage. No invalidated low-alt evidence from correction `5468736357` is used. Level-B v1 remains exactly 2.0-10.5 deg. Eradiate remains only a candidate pending successful source-to-renderer optical-property parity and the separately frozen shallow true-spherical benchmark.
