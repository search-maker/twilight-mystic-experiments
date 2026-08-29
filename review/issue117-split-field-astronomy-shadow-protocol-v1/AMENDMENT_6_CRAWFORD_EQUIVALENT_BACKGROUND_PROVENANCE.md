# Amendment 6 — Crawford/equivalent-background provenance gate before SF-A output

Status: **FROZEN BEFORE SF-A SKY-LUMINANCE / ADAPTATION-STATE / C2-C3-C4 OUTPUT**

This amendment records a source-level distinction that matters for interpreting the three surviving transient mappings. It does not inspect SF-A output, Taylor/Jerusalem data, a protected holdout, MYSTIC output, or any candidate residual.

## Primary-source chain

1. **Crawford (1947), Proc. R. Soc. B 134, 283–302, DOI 10.1098/rspb.1947.0015.** Visual adaptation was measured by liminal test threshold. Crawford's classical transformation represents a changing adaptive state by the steady adapting-field intensity that produces the same threshold. In the steady-background interaction experiment, a steady field did not affect recovery until the recovering state reached the adaptation level corresponding to that field, after which recovery stopped.
2. **Spillmann, Nowlan & Bernholz (1972), JOSA 62, 177–181, DOI 10.1364/josa.62.000177.** Under backgrounds declining by 7 log units in 3.5, 7, 14, or 21 min, transient thresholds lagged stationary-background thresholds by as much as 1.25 log units. The authors explicitly interpret the contrast-sensitivity deficit as the additive action of the real background plus an equivalent background associated with the pre-exposure state; temporary removal of the waning real background left a persistent threshold elevation.
3. **Thomas & Lamb (1999), J. Physiol. 518, 479–496, DOI 10.1111/j.1469-7793.1999.0479p.x.** Human rod dark-adaptation measurements were transformed to equivalent-background intensity by inverting the independently measured steady light-adaptation relation (a Crawford transformation), reinforcing the sequence `measured adaptive effect -> inverse steady-state relation -> equivalent-background intensity`.
4. **Pianta & Kalloniatis (2000), J. Physiol. 528, 591–608, DOI 10.1111/j.1469-7793.2000.00591.x.** Their cone model writes total experienced light as the sum of absolute dark light, equivalent light, and real light, but the paper explicitly treats this as a model whose validity depends on mechanism, spectral matching, and cone pathway; it is not a blanket mesopic rule.
5. **Rinalducci, Higgins & Cramer (1970), JOSA 60, 1518–1524, DOI 10.1364/josa.60.001518.** Photopic dark-adaptation experiments found nonequivalence for some target/chromatic conditions. Therefore classical equivalent-background success in scotopic work cannot be promoted automatically into a complete photopic/mesopic physiology for twilight.

## Frozen structural interpretation

The source chain materially distinguishes **provenance** from **astronomical performance**:

- A Crawford-style equivalent background is not obtained by subtracting two raw luminance-state coordinates merely because they have luminance units. It is obtained by taking the measured/represented adaptive effect in threshold space and **inverting the appropriate steady-state threshold-versus-background relation**.
- Where the equivalent-background hypothesis is applicable, the inferred equivalent component is then combined with the **real local background** as an additive light-like term. Spillmann et al. explicitly use this real-plus-equivalent interpretation for waning backgrounds.
- Therefore, among the already-frozen SF-A mappings, **C4 is the sole candidate whose construction matches both steps of the classical Crawford mechanism**: threshold-derived generalized inverse -> non-negative equivalent-background amount -> addition to local `B_d` -> local threshold evaluation.
- C2 remains a useful path-envelope control, but its direct `B_a,lagged - B_a,instant` debt is not a Crawford transformation.
- C3 remains a useful threshold-ratio control, but multiplicative transfer of an adaptation-field threshold ratio to local `B_d` is not the classical real-plus-equivalent-background construction.

This is a **mechanism-prior provenance ordering only**. It is frozen before SF-A values and may not be strengthened or weakened because of later Taylor/Jerusalem agreement or candidate effect size.

## Scope limitation

C4 is **not** promoted to production or declared a complete twilight physiology by this amendment. The bound SF-A photopic Crumey/Blackwell relation remains an achromatic structural baseline, the validated provider has no bound spectral runtime, the mesopic mapping remains unavailable, and no separate rod/cone ODE is authorized. The photopic nonequivalence evidence above is a positive reason to preserve that limitation.

Accordingly:

- `C4 = PRIMARY_EQUIVALENT_BACKGROUND_PROVENANCE_CANDIDATE`;
- `C2 = PATH_ENVELOPE_STRUCTURAL_CONTROL`;
- `C3 = THRESHOLD_RATIO_STRUCTURAL_CONTROL`;
- no candidate may be selected from SF-A astronomy output alone;
- the preregistered structural-failure tests still apply equally to all candidates;
- `TRANSIENT_VISIBILITY_NEGATIVE_PENALTY` remains fail-closed and authoritative;
- PR #116 remains non-final.

If C4 later fails a preregistered structural invariant, provenance does not rescue it. If C4 survives while C2/C3 also survive, independent dynamic/split-field human evidence remains necessary before a production physiological choice.