#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from pathlib import Path

import numpy as np

ROWS = list(range(18, 28))
PAIRS = list(range(1, 7))
LATE_PRECISION_ROWS = [23, 24, 25, 26]
T95_DF5 = 2.570581835636305
OMEGA = 1.532
THMAX = 65.0
NR = 8
NA = 8
NREF = 1.55
OMEGA_ARCSEC2 = (math.pi / (180.0 * 3600.0)) ** 2


def tables(path: Path):
    d = {}
    with path.open(newline='') as f:
        for r in csv.DictReader(f):
            if r['table'] == 'constants':
                continue
            d.setdefault(r['table'], []).append((float(r['x']), float(r['response'])))
    for k in d:
        d[k].sort()
    return d


def interp(points, x, left=0, right=0):
    return np.interp(x, np.array([p[0] for p in points]), np.array([p[1] for p in points]), left=left, right=right)


def quad(t):
    x, w = np.polynomial.legendre.leggauss(NR)
    mu0 = math.cos(math.radians(THMAX))
    mu = 0.5 * (1 - mu0) * x + 0.5 * (1 + mu0)
    ww = 0.5 * (1 - mu0) * w
    out = []
    for m, wm in zip(mu, ww):
        th = math.degrees(math.acos(float(m)))
        D = float(interp(t['sqm_original_angular_response_digitization'], np.array([th]), left=1, right=0)[0])
        for _ in range(NA):
            out.append((th, float(wm) * 2 * math.pi / NA * D / OMEGA))
    return out


def vega_qs(fits_path: Path, t):
    from astropy.io import fits
    with fits.open(fits_path) as hd:
        data = hd[1].data
        wl = np.asarray(data['WAVELENGTH'], float) / 10.0
        flux = np.asarray(data['FLUX'], float) * 10.0
    sel = (wl >= 380) & (wl <= 780)
    wl = wl[sel]; flux = flux[sel]
    C0 = interp(t['sqm_combined_onaxis_response_digitization'], wl, 0, 0)
    T0 = interp(t['hoya_cm500_1mm_transmittance'], wl, 0, 0)
    zenith_q = float(np.trapezoid((flux / OMEGA_ARCSEC2) * C0, wl))
    total = 0.0
    for th, w in quad(t):
        ratio = 1 / math.sqrt(1 - (math.sin(math.radians(th)) ** 2) / (NREF ** 2))
        af = np.where(T0 > 0, np.power(T0, ratio - 1), 0)
        total += w * float(np.trapezoid((flux / OMEGA_ARCSEC2) * C0 * af, wl))
    return total, zenith_q


def mag(q, q0):
    if not q > 0:
        raise RuntimeError(f'non-positive q={q}')
    return -2.5 * math.log10(q / q0)


def mean_sd_se(xs):
    xs = [float(x) for x in xs]
    if len(xs) < 2:
        raise RuntimeError('need at least two independent seeds')
    mean = statistics.fmean(xs)
    sd = statistics.stdev(xs)
    return mean, sd, sd / math.sqrt(len(xs))


def ci95(mean, se):
    h = T95_DF5 * se
    return mean - h, mean + h


def load_results(root: Path):
    found = {}
    for p in root.rglob('pair-result.json'):
        x = json.loads(p.read_text())
        if x.get('status') != 'COMPLETED':
            continue
        key = (int(x['row']), int(x['pair']))
        if key in found:
            raise RuntimeError(f'duplicate result {key}')
        found[key] = x
    expected = {(r, p) for r in ROWS for p in PAIRS}
    if set(found) != expected:
        raise RuntimeError(f'need exact 60 paired results; missing={sorted(expected-set(found))} extra={sorted(set(found)-expected)}')
    return found


def region_pair_values(found, q0, rows, metric):
    vals = []
    for pair in PAIRS:
        per_row = []
        for row in rows:
            x = found[(row, pair)]
            obs = float(x['observedSQM'])
            b = mag(x['baseline']['wideQ'], q0)
            p = mag(x['profile']['wideQ'], q0)
            if metric == 'delta_model':
                per_row.append(p - b)
            elif metric == 'delta_abs_residual':
                per_row.append(abs(obs - p) - abs(obs - b))
            else:
                raise ValueError(metric)
        vals.append(statistics.fmean(per_row))
    return vals


def classify_signed(mean, se, positive, negative):
    lo, hi = ci95(mean, se)
    if lo > 0:
        return positive
    if hi < 0:
        return negative
    return 'INDETERMINATE_AT_95PCT_MC_CI'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--results-root', type=Path, required=True)
    ap.add_argument('--response', type=Path, required=True)
    ap.add_argument('--vega', type=Path, required=True)
    ap.add_argument('--manifest', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    a.output.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(a.manifest.read_text())
    thresholds = manifest['precisionThresholdsMag']
    found = load_results(a.results_root)
    q0_wide, q0_zenith = vega_qs(a.vega, tables(a.response))

    rows = []
    per_pair_rows = []
    for row in ROWS:
        xs = [found[(row, p)] for p in PAIRS]
        observed = float(xs[0]['observedSQM']); utc = xs[0]['utc']; alt = float(xs[0]['sunAltGeometricDeg']); role = xs[0]['comparisonRole']
        for x in xs[1:]:
            if (x['utc'], float(x['observedSQM']), float(x['sunAltGeometricDeg']), x['comparisonRole']) != (utc, observed, alt, role):
                raise RuntimeError(f'row metadata drift row {row}')
        b = [mag(x['baseline']['wideQ'], q0_wide) for x in xs]
        p = [mag(x['profile']['wideQ'], q0_wide) for x in xs]
        bz = [mag(x['baseline']['zenithQ'], q0_zenith) for x in xs]
        pz = [mag(x['profile']['zenithQ'], q0_zenith) for x in xs]
        d = [pp - bb for pp, bb in zip(p, b)]
        db_abs = [abs(observed - pp) - abs(observed - bb) for pp, bb in zip(p, b)]
        k_b = [bb - zz for bb, zz in zip(b, bz)]
        k_p = [pp - zz for pp, zz in zip(p, pz)]
        bm, bsd, bse = mean_sd_se(b); pm, psd, pse = mean_sd_se(p); dm, dsd, dse = mean_sd_se(d)
        dam, dasd, dase = mean_sd_se(db_abs); kbm, kbsd, kbse = mean_sd_se(k_b); kpm, kpsd, kpse = mean_sd_se(k_p)
        d_lo, d_hi = ci95(dm, dse)
        rec = {
            'row': row, 'utc': utc, 'sun_alt_geometric_deg': alt, 'comparison_role': role,
            'observed_sqm_mag_arcsec2': observed,
            'baseline_mean_model_mag': bm, 'baseline_residual_observed_minus_model_mag': observed-bm,
            'baseline_between_seed_sd_mag': bsd, 'baseline_mean_se_mag': bse,
            'profile_mean_model_mag': pm, 'profile_residual_observed_minus_model_mag': observed-pm,
            'profile_between_seed_sd_mag': psd, 'profile_mean_se_mag': pse,
            'profile_minus_baseline_delta_mag': dm, 'paired_delta_sd_mag': dsd, 'paired_delta_se_mag': dse,
            'paired_delta_95ci_low_mag': d_lo, 'paired_delta_95ci_high_mag': d_hi,
            'delta_abs_taylor_residual_profile_minus_baseline_mag': dam,
            'delta_abs_taylor_residual_sd_mag': dasd, 'delta_abs_taylor_residual_se_mag': dase,
            'baseline_wide_minus_true_zenith_mag': kbm, 'baseline_angular_correction_sd_mag': kbsd, 'baseline_angular_correction_se_mag': kbse,
            'profile_wide_minus_true_zenith_mag': kpm, 'profile_angular_correction_sd_mag': kpsd, 'profile_angular_correction_se_mag': kpse,
            'paired_delta_numerically_distinguished_95pct': not (d_lo <= 0 <= d_hi),
        }
        rows.append(rec)
        for pair, bb, pp, zzb, zzp, dd, da in zip(PAIRS, b, p, bz, pz, d, db_abs):
            per_pair_rows.append({
                'row': row, 'pair': pair, 'sun_alt_geometric_deg': alt,
                'baseline_model_mag': bb, 'profile_model_mag': pp,
                'profile_minus_baseline_delta_mag': dd,
                'delta_abs_taylor_residual_profile_minus_baseline_mag': da,
                'baseline_true_zenith_mag': zzb, 'profile_true_zenith_mag': zzp,
                'baseline_wide_minus_zenith_mag': bb-zzb, 'profile_wide_minus_zenith_mag': pp-zzp,
            })

    convergence_rows = []
    for r in rows:
        if r['row'] in LATE_PRECISION_ROWS:
            ok = r['baseline_mean_se_mag'] <= thresholds['lateCaseMeanSeMax'] and r['profile_mean_se_mag'] <= thresholds['lateCaseMeanSeMax'] and r['paired_delta_se_mag'] <= thresholds['latePairedDeltaSeMax']
            convergence_rows.append({'row': r['row'], 'pass': ok})
    convergence_pass = all(x['pass'] for x in convergence_rows)

    early_rows = [20, 21, 22]
    late_rows = [24, 25, 26]
    e_dm, e_dsd, e_dse = mean_sd_se(region_pair_values(found, q0_wide, early_rows, 'delta_model'))
    l_dm, l_dsd, l_dse = mean_sd_se(region_pair_values(found, q0_wide, late_rows, 'delta_model'))
    e_am, e_asd, e_ase = mean_sd_se(region_pair_values(found, q0_wide, early_rows, 'delta_abs_residual'))
    l_am, l_asd, l_ase = mean_sd_se(region_pair_values(found, q0_wide, late_rows, 'delta_abs_residual'))

    koomen_pair_means = []
    for pair in PAIRS:
        vals = [next(x['baseline_wide_minus_zenith_mag'] for x in per_pair_rows if x['row'] == row and x['pair'] == pair) for row in ROWS]
        koomen_pair_means.append(statistics.fmean(vals))
    kmean, ksd, kse = mean_sd_se(koomen_pair_means)
    kfrac = abs(kmean) / 0.39
    kmeaningful = abs(kmean) >= float(manifest['koomenDiagnostic']['meaningfulAbsoluteCorrectionMag'])

    summary = {
        'schemaVersion': 1, 'stageId': manifest['stageId'], 'executionKey': manifest['executionKey'],
        'zeroPoint': {'system': 'Vega synthetic original-SQM response', 'calspec': a.vega.name, 'qVegaWideSurfaceBrightness0MagArcsec2': q0_wide, 'qVegaTrueZenithDirection0MagArcsec2': q0_zenith},
        'numericalConvergence': {'lateRows': LATE_PRECISION_ROWS, 'lateCaseMeanSeMaxMag': thresholds['lateCaseMeanSeMax'], 'latePairedDeltaSeMaxMag': thresholds['latePairedDeltaSeMax'], 'rows': convergence_rows, 'classification': 'PASS' if convergence_pass else 'CONTINUATION_REQUIRED'},
        'verticalProfileSensitivity': {
            'earlyRows20to22': {'profileMinusBaselineMeanDeltaMag': e_dm, 'betweenPairSdMag': e_dsd, 'seMag': e_dse, 'ci95Mag': list(ci95(e_dm,e_dse)), 'classification': classify_signed(e_dm,e_dse,'PROFILE_DARKER_THAN_BASELINE','PROFILE_BRIGHTER_THAN_BASELINE')},
            'lateRows24to26': {'profileMinusBaselineMeanDeltaMag': l_dm, 'betweenPairSdMag': l_dsd, 'seMag': l_dse, 'ci95Mag': list(ci95(l_dm,l_dse)), 'classification': classify_signed(l_dm,l_dse,'PROFILE_DARKER_THAN_BASELINE','PROFILE_BRIGHTER_THAN_BASELINE')},
        },
        'agreementWithTaylorNoFit': {
            'earlyRows20to22DeltaAbsoluteResidual': {'meanMag': e_am, 'sdMag': e_asd, 'seMag': e_ase, 'ci95Mag': list(ci95(e_am,e_ase)), 'classification': classify_signed(e_am,e_ase,'PROFILE_WORSE','PROFILE_BETTER')},
            'lateRows24to26DeltaAbsoluteResidual': {'meanMag': l_am, 'sdMag': l_asd, 'seMag': l_ase, 'ci95Mag': list(ci95(l_am,l_ase)), 'classification': classify_signed(l_am,l_ase,'PROFILE_WORSE','PROFILE_BETTER'), 'caveat': 'row26 is secondary_moon_background_sensitive; descriptive only for Taylor agreement'},
        },
        'koomenAngularFieldDiagnostic': {'definition': 'wide original-SQM synthetic magnitude minus true zenith-direction synthetic magnitude', 'meanAcrossRowsUsingSixIndependentPairMeansMag': kmean, 'sdAcrossPairMeansMag': ksd, 'seMag': kse, 'ci95Mag': list(ci95(kmean,kse)), 'absoluteFractionOf039Offset': kfrac, 'meaningfulThresholdMag': manifest['koomenDiagnostic']['meaningfulAbsoluteCorrectionMag'], 'meaningfulFractionByPreregisteredScale': kmeaningful, 'noOffsetWasFit': True},
        'scientificBoundary': {'profileClassification': 'independently retrieved proxy vertical extinction shape; not exact measured atmosphere', 'productionModelTuned': False, 'TaylorUsedToSelectProfile': False, 'levelBValidated': False},
    }

    with (a.output/'comparison.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    with (a.output/'per_pair_diagnostics.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(per_pair_rows[0].keys())); w.writeheader(); w.writerows(per_pair_rows)
    (a.output/'summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True,allow_nan=False)+'\n')

    import matplotlib.pyplot as plt
    x=np.array([r['sun_alt_geometric_deg'] for r in rows]); obs=np.array([r['observed_sqm_mag_arcsec2'] for r in rows]); bm=np.array([r['baseline_mean_model_mag'] for r in rows]); pm=np.array([r['profile_mean_model_mag'] for r in rows])
    bci=T95_DF5*np.array([r['baseline_mean_se_mag'] for r in rows]); pci=T95_DF5*np.array([r['profile_mean_se_mag'] for r in rows])
    fig,ax=plt.subplots(figsize=(9,5)); ax.plot(x,obs,'o-',label='Taylor observed SQM'); ax.errorbar(x,bm,yerr=bci,fmt='o-',capsize=2,label='Baseline MYSTIC mean (95% MC CI)'); ax.errorbar(x,pm,yerr=pci,fmt='o-',capsize=2,label='Proxy-profile MYSTIC mean (95% MC CI)'); ax.invert_xaxis(); ax.invert_yaxis(); ax.set_xlabel('Geometric topocentric Sun altitude (deg)'); ax.set_ylabel('mag/arcsec^2'); ax.grid(alpha=.25); ax.legend(); fig.tight_layout(); fig.savefig(a.output/'observed_vs_paired_mystic.png',dpi=180); plt.close(fig)
    br=obs-bm; pr=obs-pm
    fig,ax=plt.subplots(figsize=(9,5)); ax.errorbar(x,br,yerr=bci,fmt='o-',capsize=2,label='Observed - baseline (95% MC CI)'); ax.errorbar(x,pr,yerr=pci,fmt='o-',capsize=2,label='Observed - proxy profile (95% MC CI)'); ax.axhline(0,linewidth=1); ax.invert_xaxis(); ax.set_xlabel('Geometric topocentric Sun altitude (deg)'); ax.set_ylabel('Residual (mag)'); ax.grid(alpha=.25); ax.legend(); fig.tight_layout(); fig.savefig(a.output/'paired_residuals.png',dpi=180); plt.close(fig)
    kd=np.array([r['baseline_wide_minus_true_zenith_mag'] for r in rows]); kci=T95_DF5*np.array([r['baseline_angular_correction_se_mag'] for r in rows])
    fig,ax=plt.subplots(figsize=(9,5)); ax.errorbar(x,kd,yerr=kci,fmt='o-',capsize=2,label='Wide SQM - true zenith (baseline; 95% MC CI)'); ax.axhline(0,linewidth=1); ax.invert_xaxis(); ax.set_xlabel('Geometric topocentric Sun altitude (deg)'); ax.set_ylabel('Angular-field correction (mag)'); ax.grid(alpha=.25); ax.legend(); fig.tight_layout(); fig.savefig(a.output/'koomen_angular_field_correction.png',dpi=180); plt.close(fig)

    lines=['# Taylor high-photon paired MYSTIC result','', 'No offset, AOD, vertical profile, or other parameter was fit to Taylor. The second case is the pre-existing independently retrieved CAMS 532-nm vertical extinction **proxy**; it is not claimed to be the exact measured atmosphere.','', '## Numerical convergence','', f"Late-row preregistered precision gate (rows {LATE_PRECISION_ROWS}): **{summary['numericalConvergence']['classification']}**. Thresholds: case-mean SE <= {thresholds['lateCaseMeanSeMax']:.3f} mag and paired-delta SE <= {thresholds['latePairedDeltaSeMax']:.3f} mag.",'','## Vertical-profile sensitivity','', f"- -4 to -5 deg (rows 20-22): profile-minus-baseline = {e_dm:+.4f} +/- {T95_DF5*e_dse:.4f} mag (95% paired-MC CI); **{summary['verticalProfileSensitivity']['earlyRows20to22']['classification']}**.", f"- -5.5 to -6.3 deg (rows 24-26): profile-minus-baseline = {l_dm:+.4f} +/- {T95_DF5*l_dse:.4f} mag (95% paired-MC CI); **{summary['verticalProfileSensitivity']['lateRows24to26']['classification']}**.",'','## Agreement with Taylor (no fit)','', f"- -4 to -5 deg: change in |observed-model residual| = {e_am:+.4f} +/- {T95_DF5*e_ase:.4f} mag; **{summary['agreementWithTaylorNoFit']['earlyRows20to22DeltaAbsoluteResidual']['classification']}**.", f"- -5.5 to -6.3 deg: change in |observed-model residual| = {l_am:+.4f} +/- {T95_DF5*l_ase:.4f} mag; **{summary['agreementWithTaylorNoFit']['lateRows24to26DeltaAbsoluteResidual']['classification']}**. Row 26 is lunar/background-sensitive, so this is descriptive beyond row25.",'','## Koomen / wide-field operator diagnostic','', f"Baseline full-original-SQM minus true-zenith correction averaged over the frozen interval = {kmean:+.4f} +/- {T95_DF5*kse:.4f} mag (95% MC CI), |correction| / 0.39 = {kfrac:.3f}. Preregistered >= {manifest['koomenDiagnostic']['meaningfulAbsoluteCorrectionMag']:.2f} mag scale test: **{'MEANINGFUL_SCALE' if kmeaningful else 'SMALL_SCALE'}**. No offset was fit.",'','## Row table','', '|row|UTC|Sun alt|obs|baseline|profile|obs-baseline|obs-profile|base SD/SE|profile SD/SE|profile-baseline delta SD/SE|wide-zenith|','|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        lines.append(f"|{r['row']}|{r['utc']}|{r['sun_alt_geometric_deg']:.3f}|{r['observed_sqm_mag_arcsec2']:.3f}|{r['baseline_mean_model_mag']:.4f}|{r['profile_mean_model_mag']:.4f}|{r['baseline_residual_observed_minus_model_mag']:+.4f}|{r['profile_residual_observed_minus_model_mag']:+.4f}|{r['baseline_between_seed_sd_mag']:.4f}/{r['baseline_mean_se_mag']:.4f}|{r['profile_between_seed_sd_mag']:.4f}/{r['profile_mean_se_mag']:.4f}|{r['profile_minus_baseline_delta_mag']:+.4f} {r['paired_delta_sd_mag']:.4f}/{r['paired_delta_se_mag']:.4f}|{r['baseline_wide_minus_true_zenith_mag']:+.4f}|")
    lines += ['', 'Full CSVs, JSON provenance/statistics, and plots are retained in the workflow artifact.']
    report='\n'.join(lines)+'\n'; (a.output/'report.md').write_text(report)

    issue_lines=['## Issue #828 paired high-photon result','', f"Execution `{manifest['executionKey']}`; exact frozen rows 18-27; six independent CRN pairs; 200k photons/ray/case; 64-ray original-SQM 380-780 nm operator. No fitting.",'', f"**Numerical convergence:** {summary['numericalConvergence']['classification']} under the preregistered late-row SE gate.", f"**-4 to -5 deg profile effect:** {e_dm:+.4f} +/- {T95_DF5*e_dse:.4f} mag (95% paired-MC CI); Taylor |residual| change {e_am:+.4f} +/- {T95_DF5*e_ase:.4f} mag -> {summary['agreementWithTaylorNoFit']['earlyRows20to22DeltaAbsoluteResidual']['classification']}.", f"**-5.5 to -6.3 deg profile effect:** {l_dm:+.4f} +/- {T95_DF5*l_dse:.4f} mag; Taylor |residual| change {l_am:+.4f} +/- {T95_DF5*l_ase:.4f} mag -> {summary['agreementWithTaylorNoFit']['lateRows24to26DeltaAbsoluteResidual']['classification']} (row26 descriptive: lunar/background-sensitive).", f"**Koomen operator diagnostic:** full original-SQM minus true zenith = {kmean:+.4f} +/- {T95_DF5*kse:.4f} mag over the frozen interval; |correction|/0.39 = {kfrac:.3f}; no offset fit.",'', 'The profile case remains an independently retrieved CAMS vertical-extinction proxy, **not** the exact measured same-cycle atmosphere. This result does not tune production or validate Level-B/first-seeing.','', '<details><summary>Compact row table</summary>','', '|row|Sun alt|obs|baseline|profile|delta profile-baseline|delta SE|','|---:|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        issue_lines.append(f"|{r['row']}|{r['sun_alt_geometric_deg']:.3f}|{r['observed_sqm_mag_arcsec2']:.3f}|{r['baseline_mean_model_mag']:.4f}|{r['profile_mean_model_mag']:.4f}|{r['profile_minus_baseline_delta_mag']:+.4f}|{r['paired_delta_se_mag']:.4f}|")
    issue_lines += ['', '</details>', '']; (a.output/'issue-summary.md').write_text('\n'.join(issue_lines)); print(report)


if __name__ == '__main__':
    main()
