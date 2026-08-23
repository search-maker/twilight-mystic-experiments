# Official OPAC optical-properties source audit — review v2

Status: **REVIEW ONLY — NO SCIENTIFIC EXECUTION OR STATE FREEZE**

Source-audit v1 successfully acquired the official libRadtran `optprop_v2.1.tar.gz` and fixed its downloaded-byte identity:

- source run: `32654796582`, attempt 1;
- source artifact: `9497157886`;
- archive size: `743391266` bytes;
- archive SHA-256: `11daa1f1f4be0fd4ddf7e881ec2005498049674a1540d37b4b1e8f5e16052c7e`;
- archive member count: `28`;
- no uvspec, syntax check, solver, scientific runtime, ordinal, or result opening.

The v1 matcher expected basenames such as `INSO.nc`; the authoritative archive uses method-qualified NetCDF names. The compact v1 member listing shows all required assets are present under these exact paths:

- `data/aerosol/OPAC/optprop/inso.mie.cdf`
- `data/aerosol/OPAC/optprop/waso.mie.cdf`
- `data/aerosol/OPAC/optprop/soot.mie.cdf`
- `data/aerosol/OPAC/optprop/ssam.mie.cdf`
- `data/aerosol/OPAC/optprop/sscm.mie.cdf`
- `data/aerosol/OPAC/optprop/minm.mie.cdf`
- `data/aerosol/OPAC/optprop/miam.mie.cdf`
- `data/aerosol/OPAC/optprop/micm.mie.cdf`
- `data/aerosol/OPAC/optprop/mitr.mie.cdf`
- `data/aerosol/OPAC/optprop/suso.mie.cdf`
- `data/aerosol/OPAC/optprop/minm_spheroids.tmatrix.cdf`
- `data/aerosol/OPAC/optprop/miam_spheroids.tmatrix.cdf`
- `data/aerosol/OPAC/optprop/micm_spheroids.tmatrix.cdf`

The archive additionally contains `data/aerosol/OPAC/optprop/mitr_spheroids.tmatrix.cdf`; it is recorded as an extra asset but is not required by this gate.

## v2 gate

The companion audit must freshly download the same official URL, require **exactly** the v1-observed archive size and SHA-256, require all exact paths above, and stream a SHA-256 for each required member. The archive must be deleted before compact evidence upload.

A PASS proves only that the official external optical-properties source has now been byte-bound and contains the documented spherical and desert-spheroid OPAC assets. It does not prove that the conda runtime resolves them, does not authorize a solver call, and does not freeze a scientific aerosol state set.

After PASS, the next separate review stage is an exact-runtime overlay audit: combine the already frozen conda runtime with this exact archive, verify deterministic placement/data-tree identity and OPAC mixture dependency resolution, while remaining no-science. A scientific preregistration comes only after that overlay review.
