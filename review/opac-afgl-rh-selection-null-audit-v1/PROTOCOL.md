# AFGL-US OPAC relative-humidity selection / NULL-solver audit v1

Status: **DIAGNOSTIC / REVIEW ONLY / NULL SOLVER / NO SCIENTIFIC ORDINAL**

## Purpose

PR #592 proved four-species explicit transport for `INSO WASO SOOT SUSO`. PR #593 froze the exact 550-nm optical-property source values at every official OPAC RH node. The remaining representation question is which humidity state the locked libRadtran runtime associates with each AFGL-US altitude when OPAC humidity-dependent species are used.

This audit asks the runtime directly for the AFGL-US relative-humidity profile and preserves the verbose 550-nm optical-property setup of the locked `continental_average` mixture.

## Why `rte_solver null`

The libRadtran user guide defines the NULL solver as a mode that **does not solve the radiative transfer equation**; it only sets up optical properties and post-processing and is explicitly useful for inspecting optical properties with `verbose`.

Therefore this is not a scientific radiance experiment, does not consume a scientific ordinal, and does not enter the scientific seed namespace.

## Frozen inputs and predecessor evidence

- frozen main `99ade7798627e67921139697ba1a004fa8a304bb`;
- locked AFGL-US SHA-256 `dab26290ed81c762ed0c607e5dc2d53393c1462a0c3a528bc5e3f5935191cfb5`;
- exact `continental_average.dat` SHA-256 `fc39fda0f8ada2d0a0a872b8b62d684cfccd74f7b0655b5af2dcdec51115e469`;
- OPAC archive SHA-256 `11daa1f1f4be0fd4ddf7e881ec2005498049674a1540d37b4b1e8f5e16052c7e`, 743391266 bytes, 28 members;
- trace/v5/#592 proven no-extension aliases for INSO/WASO/SOOT/SUSO;
- PR #593 final exact head `223b592208d3dda24217dabcfca9fd27333e4b84`;
- #593 generic source audit run `33190220721`, artifact `9693427186`, digest `sha256:ee80b71e8bdb0cd9aaacc29890162fb903f89f6ef6c5ace615094fe94ac60a36`;
- #593 exact-550 audit run `33190220896`, artifact `9693440701`, digest `sha256:7d8fa290b74f4e15538cd6ff2609f5491caad63258d0aefb8be689f1ce5f8e33`;
- #593 exact-values content SHA-256 `7ade25bf8be7c906a5a520fb1c2a13f974ac8ea0fd01e02e35560f2fb1b79a98`;
- #593 repository contract `33190220864` attempt 1 SUCCESS.

Official RH coordinate set for humidity-dependent OPAC members, frozen by #593:

`0, 50, 70, 80, 90, 95, 98, 99 %`

## Exact diagnostic

Two monochromatic 550-nm NULL-solver inputs share the same AFGL-US atmosphere, source, wavelength grid, SZA and surface albedo.

1. `rh-only`: no aerosol; `zout atm_levels`; `output_user zout rh`.
2. `continental-null-verbose`: the exact same atmosphere plus the locked standard `continental_average` OPAC mixture, four trace-proven no-extension aliases, `zout atm_levels`, `output_user zout rh`, and `verbose`.

The runtime-reported RH profile must be identical between the two inputs. For each reported RH value, the audit records the mathematically nearest member of the frozen OPAC RH coordinate set; an exact nearest-node tie is a hard failure rather than an invented tie-break rule.

The complete verbose stderr of the `continental_average` NULL-solver setup is preserved byte-for-byte for later optical-profile parsing. This first audit does not guess its text format.

## PASS

PASS requires:

- exact frozen runtime/archive/AFGL/continental-average/source-asset identities;
- four byte-identical no-extension aliases and no historical `.nc` workaround;
- syntax checks for both inputs;
- successful actual execution with `rte_solver null` only;
- one finite RH value for every AFGL-US atmosphere level;
- identical RH profile with and without `continental_average` aerosol enabled;
- unambiguous nearest OPAC RH node at every level;
- non-empty verbose optical-property evidence preserved.

## Interpretation boundary

A PASS freezes the runtime AFGL-US RH profile and an explicit nearest-node mapping to the already frozen OPAC RH coordinate set. It does not yet prove that the internal optical-property reader uses that same nearest-node rule; the preserved verbose optical profile may be parsed/compared in a subsequent review if required.

## Hard boundaries

- no DISORT, MYSTIC or other scientific RTE solver;
- no radiance/irradiance scientific result;
- no scientific ordinal; ordinal 41 remains unallocated;
- no scientific seeds;
- no Taylor/Jerusalem residual use;
- no modification of the five preregistered AVPS vertical templates;
- no Level-B or production mutation;
- no mass-to-tau renderer authorization from this audit alone.
