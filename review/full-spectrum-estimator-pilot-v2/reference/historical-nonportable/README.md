# Historical preparation utilities

These files are preserved only to document how earlier frozen review artifacts were created before PR #109.
They are NOT the active review surface and MUST NOT be run as current builders.
Some intentionally depend on the original worker workspace under `/mnt/data` or on preparation inputs that are not part of this repository review package.

Current frozen artifacts are verified by the repository-relative `verify_full_spectrum_estimator_pilot_*_v4.py` tools in the package root. Any future fresh seed/run/identity collision audit must be performed by a separately reviewed preauthorization transport against live GitHub state; it must not be reconstructed from these historical scripts.
