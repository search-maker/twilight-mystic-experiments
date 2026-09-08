# ARM Stage-A source-file/datastream binding v1

Status: **result-blind / control-plane only / non-science**.

This verifier is a narrow downstream companion to the merged `arm_stagea_time_continuity_contract_v1`. It closes one provenance ambiguity in the future timing-only `stageA_actual_time_continuity_v2.csv` handoff: a row that declares a permitted stream must not silently name native files from another ARM datastream.

It does **not** replace or weaken the decoded-time continuity verifier. Run the merged continuity contract first; a PASS here means only that the source-file names are structurally bound to the row's declared stream.

## Exact source bindings

Each `source_files` entry must be a basename-only ARM native `.nc` filename whose exact prefix matches the canonical row stream:

- `sasze_filterbands` -> `sgpsaszefilterbandsC1.a1.`
- `hsrl` -> `sgphsrlC1.a1.`
- `rlprofbe` -> `sgprlprofbeC1.c1.`
- `arscl` -> `sgparsclkazr1kolliasC1.c0.`
- `ceil` -> `sgpceilC1.b1.`

The aliases already accepted by the merged continuity verifier remain accepted for the row's `stream` field, but the named native files must still use the corresponding exact datastream prefix.

This deliberately prevents a row labelled `sasze_filterbands` from naming full SASZE spectral files, SWS files, or any other held-out-radiance/native datastream. It also rejects absolute/relative paths so a timing-only handoff does not persist local/user-specific source paths.

The verifier requires the same 20-case x 5-stream = 100-row matrix shape. It does not open the named native files, validate or expose their values, acquire data, inspect credentials, or infer that the upstream decoded-time continuity gate passed.

## Receipt boundary

A zero exit code means only `source_file_binding_valid=true`. The receipt hard-keeps:

- `upstream_continuity_contract_pass_inferred=false`
- `scientific_pass_inferred=false`
- `missing_native_data_counts_as_pass=false`
- `protected_results_opened=false`
- `heldout_sws_sasze_radiance_opened=false`
- `heldout_radiance_opening_authorized=false`
- `stage_b_authorized=false`
- `science_execution_authorized=false`
- `production_authorized=false`

No authenticated ARM query/download, protected radiance opening, Stage B, full/live25, MYSTIC, identity/seed/ordinal allocation, or production action is performed or authorized by this tool.
