# Taylor Issue #828 — high-photon paired MYSTIC closure

Status: **CLOSED NUMERICALLY / REVIEW-ONLY HANDOFF**  
Date: **2026-09-01**

This record updates the Taylor direct-MYSTIC closure after the preregistered high-photon paired profile experiment and its single preregistered precision continuation. It does **not** change production parameters, Level-B support, human-visibility validation, or any atmosphere selection rule.

## 1. Question answered

Aster Taylor's numerical criticism was tested directly: are the apparent differences between the frozen Taylor baseline/default aerosol vertical profile and the independently constrained CAMS vertical-profile proxy genuine profile sensitivity, or only broadband MYSTIC Monte Carlo noise?

The experiment also quantified the forward-operator mismatch between:

- a true zenith-direction synthetic sky brightness; and
- the angularly integrated original wide-field Unihedron SQM synthetic measurement.

No SQM offset, AOD, vertical profile, provider/cycle, clock offset, or other parameter was fit to Taylor.

## 2. Frozen physical comparison

Exactly two physical cases were compared:

1. the frozen Taylor baseline/default aerosol vertical profile;
2. the pre-existing independently retrieved CAMS 532-nm vertical-extinction **proxy** from PR #508.

Proxy provenance:

- retrieval run: `33039911540`;
- artifact: `taylor-cams-priorcycle-split-extinction532-v2` / artifact ID `9633502319`;
- artifact digest: `sha256:354d880865ae71234504599ba5fa223a55d805d4d466e8294352dde669d543fe`;
- profile SHA-256: `6c3a3041b6718db415300323f23da0277752b6c9fc6c806e5eff7c493b060359`.

This proxy was independently retrieved before this comparison. It was **not selected because it fits Taylor**, and it must **not** be described as the exact measured same-cycle atmosphere. PR #536's atmosphere-provenance boundary remains controlling.

Held fixed between the two cases:

- total AOD550 at each row;
- Sun/observer geometry;
- surface pressure;
- surface albedo = 0.15;
- AFGL-US atmosphere family;
- `aerosol_default` spectral/phase optical-property family;
- 380–780 nm ALIS forward calculation with `mc_spectral_is 550`;
- exact original-wide-SQM 64-ray angular integration;
- Vega calibration.

Only the normalized vertical aerosol optical-depth allocation differed.

## 3. Primary high-photon experiment — ordinal47

Frozen interval: rows 18–27, geometric Sun altitude `-3.492°` through `-6.460°`.

Numerics:

- 6 independent common-random-number seed pairs per row;
- 200,000 photons/ray/case;
- 64 wide-SQM rays per case plus a true-zenith diagnostic ray;
- 60 row×pair jobs;
- 7,800 solver calls;
- 1.56 billion configured photon histories.

Exact science evidence:

- execution key: `taylor-paired-profile-crn-v1:scientific:47`;
- science head: `2426335c652adacf442122c3a1bcdf9489a10298`;
- science run: `33543818095`, attempt 1;
- final solver-free analysis run: `33545920403`, attempt 1;
- final ordinal47 analysis artifact: `9815468437`;
- artifact digest: `sha256:0d376c504f70b792a0393636d885094159bc10a0696dd49643fadf1fffb2e5c4`.

The preregistered late-row numerical gate required rows 23–26 to have all three SE values `<= 0.030 mag`: baseline mean, proxy mean, and paired profile-minus-baseline delta.

Rows 23–25 passed. Row26 alone narrowly failed only the paired-delta criterion (`0.0312712632 mag`); both case means already passed. This forced a fresh continuation identity rather than interpreting the noisy row as physical.

## 4. Preregistered row26-only precision continuation — ordinal48

The continuation target was chosen **only** by the frozen numerical gate above.

Preregistered before new results:

- row26 only;
- 4 fresh CRN pairs, labels 7–10;
- seed bases `1531000000`, `1532000000`, `1533000000`, `1534000000`;
- unchanged 200,000 photons/ray/case and frozen physics/operator;
- exactly 520 fresh solver calls / 104,000,000 configured histories;
- final row26 estimate combines immutable ordinal47 pairs 1–6 with fresh pairs 7–10, giving `n=10`;
- the regional six-pair tests and Koomen diagnostic were frozen unchanged and **not selectively reweighted** after the continuation.

Exact continuation evidence:

- preregistration head: `57155e84d6d687cdb5bbe64f4fb813a78f2513d5`;
- preregistration Issue #828 comment: `5499113547`;
- marker/science head: `c214b6ad45d88adf0d23acac89b823ca0dcfc90d`;
- PR: #834;
- continuation execution key: `taylor-paired-profile-crn-v1:scientific:48-continuation1`;
- continuation run: `33548572011`, attempt 1, SUCCESS;
- 4/4 fresh pair jobs: SUCCESS;
- generic exact-head contract run: `33548572005`, SUCCESS;
- final analysis artifact: `9816641987`;
- artifact digest: `sha256:cf5f79a48789e218a1d957a47419a3e2dc0f0bf5045578d6bc9b56f8ea358c13`.

### Final row26 numerical precision

With all ten independent pairs:

- baseline mean = `12.9340005904 mag/arcsec²`;
- baseline SD = `0.0315478048 mag`;
- baseline SE = `0.0099762918 mag`;
- proxy mean = `13.0644681335 mag/arcsec²`;
- proxy SD = `0.0553166542 mag`;
- proxy SE = `0.0174926620 mag`;
- proxy-minus-baseline delta = `+0.1304675431 mag`;
- paired-delta SD = `0.0605427555 mag`;
- paired-delta SE = `0.0191453003 mag`;
- 95% Student-t CI = `[+0.0871578649, +0.1737772213] mag`.

**Final numerical convergence classification: PASS.** All preregistered late-row precision requirements are now met.

## 5. Final compact row table

Rows other than row26 retain the balanced six-pair ordinal47 estimate. Row26 alone uses the preregistered ten-pair precision closure.

| Row | Sun alt (deg) | Taylor SQM | Pairs | Baseline mean | Proxy mean | Proxy − baseline | Paired delta SE |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 18 | -3.492 | 9.750 | 6 | 9.8357 | 9.9344 | +0.0987 | 0.0040 |
| 19 | -3.826 | 10.160 | 6 | 10.2084 | 10.3044 | +0.0960 | 0.0037 |
| 20 | -4.159 | 10.570 | 6 | 10.5795 | 10.6769 | +0.0974 | 0.0134 |
| 21 | -4.491 | 10.970 | 6 | 10.9723 | 11.0697 | +0.0974 | 0.0081 |
| 22 | -4.821 | 11.370 | 6 | 11.3583 | 11.4634 | +0.1051 | 0.0068 |
| 23 | -5.151 | 11.850 | 6 | 11.7513 | 11.8864 | +0.1352 | 0.0086 |
| 24 | -5.480 | 12.300 | 6 | 12.1625 | 12.2863 | +0.1239 | 0.0126 |
| 25 | -5.808 | 12.720 | 6 | 12.5435 | 12.6809 | +0.1374 | 0.0158 |
| 26 | -6.134 | 13.120 | 10 | 12.9340 | 13.0645 | +0.1305 | 0.0191 |
| 27 | -6.460 | 13.570 | 6 | 13.2618 | 13.5008 | +0.2391 | 0.0543 |

Rows 26–27 are lunar/background-sensitive in the existing Taylor classification; their absolute Taylor residuals are descriptive rather than clean solar-only validation points.

## 6. Separate scientific conclusions

### A. Numerical convergence

**PASS.** The apparent profile differences in the preregistered key intervals are not an artifact of the previously inadequate low-photon/single-seed MYSTIC realizations.

The final difficult row26 paired profile effect also remains clearly nonzero after the independent continuation: `+0.13047 mag`, 95% CI `[+0.08716,+0.17378]`.

### B. Vertical-profile sensitivity

The primary region questions remain the preregistered balanced six-pair comparisons.

**Around -4° to -5° (rows20–22):**

- mean proxy-minus-baseline effect = `+0.09995233 mag`;
- SE = `0.00478376 mag`;
- 95% CI = `[+0.08765529,+0.11224938]`.

The proxy profile makes the modeled sky about `0.10 mag` darker than the baseline here. The interval excludes zero comfortably: the worsening seen in the earlier low-photon profile curve is numerically/physically real under these two frozen profile cases, not MC scatter.

**Around -5.5° to -6.3° (rows24–26):**

- mean proxy-minus-baseline effect = `+0.13487188 mag`;
- SE = `0.01180108 mag`;
- 95% CI = `[+0.10453623,+0.16520752]`.

Again the profile effect is resolved well beyond paired MC noise.

### C. Agreement with Taylor — no fit

This is deliberately separate from the sensitivity conclusion.

**Rows20–22 (~-4° to -5°):** change in absolute Taylor residual, proxy minus baseline:

- mean `+0.08399410 mag`;
- 95% CI `[+0.07237966,+0.09560854]`.

Therefore the proxy profile **worsens** agreement with Taylor in this interval.

**Rows24–26 (~-5.5° to -6.3°):**

- mean `-0.11859241 mag`;
- 95% CI `[-0.13574623,-0.10143859]`.

Therefore the proxy profile **improves** agreement in the no-fit diagnostic at late twilight. Row26's absolute-agreement contribution remains descriptive because it is background/lunar-sensitive.

The important conclusion is not that the proxy is the true atmosphere. It is that plausible independently constrained vertical structure has a real, sign-changing impact on the Taylor residual pattern large compared with paired MC noise.

## 7. Koomen / original-wide-SQM angular-field correction

Frozen balanced six-pair result:

- quantity: `full original-wide-SQM synthetic magnitude − true zenith-direction synthetic magnitude`;
- mean over the frozen interval = `-0.28259454 mag`;
- SE = `0.03026800 mag`;
- 95% CI = `[-0.36040091,-0.20478816]`;
- absolute magnitude relative to `0.39 mag` = `0.7246`.

Thus the wide-field original SQM sees an angularly integrated twilight sky that is about `0.28 mag` brighter (numerically smaller magnitude) than the true zenith-direction synthetic brightness over this interval.

**Interpretation:** comparing Taylor's original wide-field SQM directly to a zenith-only Koomen interpolation can create an offset of a scientifically meaningful scale — roughly 72% of `0.39 mag` in absolute size in this MYSTIC calculation. This was calculated with no fitted offset. It does not prove that this operator mismatch is the sole cause of Taylor's ~0.39-mag Koomen offset; the sign must be compared to the exact convention used in that external comparison, and atmospheric/model differences remain separate contributors.

## 8. Taylor-facing concise handoff

A defensible short summary is:

> We repeated the comparison as a paired high-photon MYSTIC experiment rather than relying on the earlier single-seed curves. With six common-random-number pairs at 200k photons per ray, plus a preregistered four-pair continuation for the one marginal late point, the numerical precision criterion is now satisfied. The alternative independently retrieved CAMS vertical-profile proxy changes the modeled twilight brightness by about 0.10 mag at Sun depths 4–5°, where it makes agreement with your SQM data worse, and by about 0.135 mag around 5.5–6.3°, where it improves the no-fit agreement. Both effects are much larger than the paired Monte Carlo uncertainty. The proxy is not claimed to be the exact atmosphere on your observing night. Separately, the original wide-field SQM forward operator differs from a true zenith-only synthetic brightness by about -0.283 mag over this interval, so a direct comparison of the wide-field SQM with a zenith-only Koomen interpolation can itself create a substantial absolute offset. No offset or atmosphere parameter was fitted to your observations.

## 9. Scientific boundary after Issue #828

This closure supports:

- numerical convergence of the paired direct-MYSTIC profile comparison;
- a real sensitivity of twilight radiance to the tested aerosol vertical-profile shape;
- a material original-wide-SQM versus zenith-only angular-field correction.

It does **not** establish:

- that the CAMS proxy is the exact atmosphere during Taylor's observations;
- that the proxy should be selected for production because it improves some Taylor rows;
- a universal SQM/Koomen offset correction;
- Level-B validation;
- human first-seeing validation;
- production model promotion.

The independent-atmosphere acquisition lane remains necessary for a stronger real-atmosphere Taylor validation.
