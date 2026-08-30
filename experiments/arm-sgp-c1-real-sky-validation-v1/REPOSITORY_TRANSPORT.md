# Repository transport note

The frozen scientific package was produced outside the repository with the raw file `fex-profile-shapes.csv` (93,646 bytes; SHA-256 `6c2db68e7ecf15f65860338c946cc0f5456f012b3a46eb8b111809b2184ffdd2`).

To keep the review branch small and deterministic, that raw CSV is transported as `fex-profile-shapes.csv.zlib.b64`. `materialize_profile.py` decodes and decompresses it, refuses any byte-count or SHA-256 drift, and writes the exact raw file before package-manifest verification or preflight rendering.

This transport representation changes no scientific value, profile node, case identity, or preregistration rule. The raw file is a generated review-time materialization and is not a separate scientific source.
