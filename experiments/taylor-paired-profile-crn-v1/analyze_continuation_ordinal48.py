#!/usr/bin/env python3
from __future__ import annotations
import argparse
import csv
import json
import math
import shutil
import statistics
from pathlib import Path

OLD_KEY = 'taylor-paired-profile-crn-v1:scientific:47'
NEW_KEY = 'taylor-paired-profile-crn-v1:scientific:48-continuation1'
PROFILE_SHA = '6c3a3041b6718db415300323f23da0277752b6c9fc6c806e5eff7c493b060359'
T95_DF5 = 2.570581835636305
T95_DF9 = 2.2621571627409915
THRESH = 0.03


def mag(q, q0):
    q = float(q)
    if not q > 0:
        raise RuntimeError(f'non-positive q={q}')
    return -2.5 * math.log10(q / q0)


def mean_sd_se(xs):
    xs = [float(x) for x in xs]
    if len(xs) < 2:
        raise RuntimeError('need at least two independent pairs')
    mean = statistics.fmean(xs)
    sd = statistics.stdev(xs)
    return mean, sd, sd / math.sqrt(len(xs))


def load_pair_results(root: Path, expected_key: str, expected_pairs):
    found = {}
    for p in root.rglob('pair-result.json'):
        x = json.loads(p.read_text())
        if x.get('status') != 'COMPLETED':
            continue
        if int(x.get('row', -1)) != 26:
            raise RuntimeError(f'unexpected row in continuation analysis: {x.get("row")}')
        pair = int(x['pair'])
        if pair in found:
            raise RuntimeError(f'duplicate pair {pair}')
        if x.get('executionKey') != expected_key:
            raise RuntimeError(f'execution key drift pair {pair}: {x.get("executionKey")}')
        if int(x['photonsPerRayPerCase']) != 200000 or int(x['rayCountWideSQM']) != 64 or x['commonRandomNumbers'] is not True:
            raise RuntimeError(f'physics/numerics contract drift pair {pair}')
        if x['camsProfileProvenance']['profileSha256'] != PROFILE_SHA:
            raise RuntimeError(f'profile provenance drift pair {pair}')
        found[pair] = x
    if set(found) != set(expected_pairs):
        raise RuntimeError(f'pair universe mismatch expected={sorted(expected_pairs)} got={sorted(found)}')
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--old-results-root', type=Path, required=True)
    ap.add_argument('--new-results-root', type=Path, required=True)
    ap.add_argument('--old-analysis-root', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    a.output.mkdir(parents=True, exist_ok=True)

    old_summary = json.loads(next(a.old_analysis_root.rglob('summary.json')).read_text())
    old_comparison_path = next(a.old_analysis_root.rglob('comparison.csv'))
    old_rows = list(csv.DictReader(old_comparison_path.open(newline='')))
    if [int(r['row']) for r in old_rows] != list(range(18, 28)):
        raise RuntimeError('ordinal47 comparison row universe drift')
    conv = old_summary['numericalConvergence']
    state = {int(x['row']): bool(x['pass']) for x in conv['rows']}
    if state != {23: True, 24: True, 25: True, 26: False}:
        raise RuntimeError(f'continuation target no longer matches frozen gate: {state}')
    old26 = next(r for r in old_rows if int(r['row']) == 26)
    if not (float(old26['baseline_mean_se_mag']) <= THRESH and float(old26['profile_mean_se_mag']) <= THRESH and float(old26['paired_delta_se_mag']) > THRESH):
        raise RuntimeError('row26 frozen failure mode does not match preregistration')

    old = load_pair_results(a.old_results_root, OLD_KEY, range(1, 7))
    new = load_pair_results(a.new_results_root, NEW_KEY, range(7, 11))
    all_pairs = {**old, **new}
    if set(all_pairs) != set(range(1, 11)):
        raise RuntimeError('combined ten-pair universe mismatch')

    q0 = float(old_summary['zeroPoint']['qVegaWideSurfaceBrightness0MagArcsec2'])
    obs = float(old26['observed_sqm_mag_arcsec2'])
    b = [mag(all_pairs[p]['baseline']['wideQ'], q0) for p in range(1, 11)]
    pr = [mag(all_pairs[p]['profile']['wideQ'], q0) for p in range(1, 11)]
    d = [pp - bb for pp, bb in zip(pr, b)]
    da = [abs(obs - pp) - abs(obs - bb) for pp, bb in zip(pr, b)]
    bm, bsd, bse = mean_sd_se(b)
    pm, psd, pse = mean_sd_se(pr)
    dm, dsd, dse = mean_sd_se(d)
    dam, dasd, dase = mean_sd_se(da)
    dlo, dhi = dm - T95_DF9*dse, dm + T95_DF9*dse
    row26_pass = bse <= THRESH and pse <= THRESH and dse <= THRESH
    overall_pass = row26_pass and all(state[r] for r in (23,24,25))

    final_rows = []
    for r in old_rows:
        rr = dict(r)
        rr['pair_count'] = '6'
        if int(rr['row']) == 26:
            rr['pair_count'] = '10'
            rr['baseline_mean_model_mag'] = repr(bm)
            rr['baseline_residual_observed_minus_model_mag'] = repr(obs-bm)
            rr['baseline_between_seed_sd_mag'] = repr(bsd)
            rr['baseline_mean_se_mag'] = repr(bse)
            rr['profile_mean_model_mag'] = repr(pm)
            rr['profile_residual_observed_minus_model_mag'] = repr(obs-pm)
            rr['profile_between_seed_sd_mag'] = repr(psd)
            rr['profile_mean_se_mag'] = repr(pse)
            rr['profile_minus_baseline_delta_mag'] = repr(dm)
            rr['paired_delta_sd_mag'] = repr(dsd)
            rr['paired_delta_se_mag'] = repr(dse)
            rr['paired_delta_95ci_low_mag'] = repr(dlo)
            rr['paired_delta_95ci_high_mag'] = repr(dhi)
            rr['delta_abs_taylor_residual_profile_minus_baseline_mag'] = repr(dam)
            rr['delta_abs_taylor_residual_sd_mag'] = repr(dasd)
            rr['delta_abs_taylor_residual_se_mag'] = repr(dase)
            rr['paired_delta_numerically_distinguished_95pct'] = str(not (dlo <= 0 <= dhi))
        final_rows.append(rr)

    fields = list(final_rows[0].keys())
    if 'pair_count' in fields:
        fields.remove('pair_count')
    fields.insert(5, 'pair_count')
    with (a.output/'final-comparison.csv').open('w',newline='') as f:
        w=csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(final_rows)

    with (a.output/'row26-ten-pair.csv').open('w',newline='') as f:
        fields2=['pair','source','baseline_model_mag','profile_model_mag','profile_minus_baseline_delta_mag','delta_abs_taylor_residual_mag']
        w=csv.DictWriter(f,fieldnames=fields2); w.writeheader()
        for p,bb,pp,dd,aa in zip(range(1,11),b,pr,d,da):
            w.writerow({'pair':p,'source':'ordinal47' if p<=6 else 'continuation48','baseline_model_mag':bb,'profile_model_mag':pp,'profile_minus_baseline_delta_mag':dd,'delta_abs_taylor_residual_mag':aa})

    summary = {
        'schemaVersion': 1,
        'executionKey': NEW_KEY,
        'continuationOf': {'executionKey': OLD_KEY, 'scienceRunId':33543818095, 'analysisRunId':33545920403},
        'newScienceBudget': {'row':26,'newPairs':[7,8,9,10],'photonsPerRayPerCase':200000,'solverCalls':520,'configuredPhotonHistories':104000000},
        'numericalConvergence': {
            'thresholdMag': THRESH,
            'inheritedPassRows': [23,24,25],
            'row26': {'nPairs':10,'baselineMeanMag':bm,'baselineSdMag':bsd,'baselineSeMag':bse,'profileMeanMag':pm,'profileSdMag':psd,'profileSeMag':pse,'profileMinusBaselineDeltaMag':dm,'pairedDeltaSdMag':dsd,'pairedDeltaSeMag':dse,'pairedDelta95CiMag':[dlo,dhi],'pass':row26_pass},
            'classification': 'PASS' if overall_pass else 'CONTINUATION_REQUIRED'
        },
        'verticalProfileSensitivityBalancedSixPairPrimary': old_summary['verticalProfileSensitivity'],
        'agreementWithTaylorNoFitBalancedSixPairPrimary': old_summary['agreementWithTaylorNoFit'],
        'koomenAngularFieldDiagnosticBalancedSixPairPrimary': old_summary['koomenAngularFieldDiagnostic'],
        'row26TaylorAgreementDescriptiveOnly': {'deltaAbsoluteResidualMeanMagTenPairs':dam,'sdMag':dasd,'seMag':dase,'caveat':'row26 is secondary_moon_background_sensitive; not used as an absolute Taylor validation point'},
        'scientificBoundary': old_summary['scientificBoundary'] | {'regionalAndKoomenResultsReweightedAfterContinuation': False, 'productionModelTuned': False, 'levelBValidated': False}
    }
    (a.output/'continuation-summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True,allow_nan=False)+'\n')

    import matplotlib.pyplot as plt
    x=[float(r['sun_alt_geometric_deg']) for r in final_rows]
    o=[float(r['observed_sqm_mag_arcsec2']) for r in final_rows]
    bb=[float(r['baseline_mean_model_mag']) for r in final_rows]
    pp=[float(r['profile_mean_model_mag']) for r in final_rows]
    bse_all=[float(r['baseline_mean_se_mag']) for r in final_rows]
    pse_all=[float(r['profile_mean_se_mag']) for r in final_rows]
    crit=[T95_DF9 if int(r['row'])==26 else T95_DF5 for r in final_rows]
    bci=[c*s for c,s in zip(crit,bse_all)]; pci=[c*s for c,s in zip(crit,pse_all)]
    fig,ax=plt.subplots(figsize=(9,5)); ax.plot(x,o,'o-',label='Taylor observed SQM'); ax.errorbar(x,bb,yerr=bci,fmt='o-',capsize=2,label='Baseline MYSTIC mean (95% MC CI)'); ax.errorbar(x,pp,yerr=pci,fmt='o-',capsize=2,label='Proxy-profile MYSTIC mean (95% MC CI)'); ax.invert_xaxis(); ax.invert_yaxis(); ax.set_xlabel('Geometric topocentric Sun altitude (deg)'); ax.set_ylabel('mag/arcsec^2'); ax.legend(); ax.grid(alpha=.25); fig.tight_layout(); fig.savefig(a.output/'final_observed_vs_paired_mystic.png',dpi=180); plt.close(fig)
    rb=[oo-v for oo,v in zip(o,bb)]; rp=[oo-v for oo,v in zip(o,pp)]
    fig,ax=plt.subplots(figsize=(9,5)); ax.errorbar(x,rb,yerr=bci,fmt='o-',capsize=2,label='Taylor - baseline'); ax.errorbar(x,rp,yerr=pci,fmt='o-',capsize=2,label='Taylor - proxy profile'); ax.axhline(0,linewidth=1); ax.invert_xaxis(); ax.set_xlabel('Geometric topocentric Sun altitude (deg)'); ax.set_ylabel('Residual (mag)'); ax.legend(); ax.grid(alpha=.25); fig.tight_layout(); fig.savefig(a.output/'final_paired_residuals.png',dpi=180); plt.close(fig)
    old_koomen = next(a.old_analysis_root.rglob('koomen_angular_field_correction.png'))
    shutil.copy2(old_koomen, a.output/'koomen_angular_field_correction_balanced6_unchanged.png')

    early=old_summary['verticalProfileSensitivity']['earlyRows20to22']
    late=old_summary['verticalProfileSensitivity']['lateRows24to26']
    ae=old_summary['agreementWithTaylorNoFit']['earlyRows20to22DeltaAbsoluteResidual']
    al=old_summary['agreementWithTaylorNoFit']['lateRows24to26DeltaAbsoluteResidual']
    k=old_summary['koomenAngularFieldDiagnostic']
    report=f'''# Taylor Issue #828 final continuation result

## Numerical convergence

**{summary['numericalConvergence']['classification']}** under the preregistered 0.03-mag late-row SE gate. Rows 23-25 remain immutable PASS from ordinal47. Row26 now uses all ten independent CRN pairs (six immutable + four fresh): baseline SE {bse:.5f} mag, proxy SE {pse:.5f} mag, paired-delta SE {dse:.5f} mag.

## Vertical-profile sensitivity (balanced six-pair primary, unchanged)

- -4 to -5 deg (rows20-22): profile-minus-baseline {early['profileMinusBaselineMeanDeltaMag']:+.4f} mag, 95% paired-MC CI [{early['ci95Mag'][0]:+.4f}, {early['ci95Mag'][1]:+.4f}]. This is numerically real and makes Taylor agreement worse; change in |residual| {ae['meanMag']:+.4f} mag, CI [{ae['ci95Mag'][0]:+.4f}, {ae['ci95Mag'][1]:+.4f}].
- -5.5 to -6.3 deg (rows24-26): profile-minus-baseline {late['profileMinusBaselineMeanDeltaMag']:+.4f} mag, CI [{late['ci95Mag'][0]:+.4f}, {late['ci95Mag'][1]:+.4f}]. This is numerically real and improves Taylor agreement in the no-fit diagnostic; change in |residual| {al['meanMag']:+.4f} mag, CI [{al['ci95Mag'][0]:+.4f}, {al['ci95Mag'][1]:+.4f}]. Row26 remains background/lunar-sensitive and descriptive for absolute agreement.

## Koomen / angular-field question (unchanged balanced six-pair primary)

Full original-wide-SQM minus true zenith = {k['meanAcrossRowsUsingSixIndependentPairMeansMag']:+.4f} mag, 95% MC CI [{k['ci95Mag'][0]:+.4f}, {k['ci95Mag'][1]:+.4f}]. Its absolute size is {k['absoluteFractionOf039Offset']:.3f} of 0.39 mag. No offset was fit. This shows the wide-field-vs-zenith operator difference can account for a meaningful fraction of the Koomen comparison offset, but not that it is the only cause.

## Scientific boundary

The alternate profile remains the independently retrieved CAMS 532-nm vertical-extinction proxy from PR #508, not the exact measured same-cycle atmosphere. No SQM offset, AOD, profile, or other parameter was fit to Taylor. No production, Level-B, or first-seeing validation follows.
'''
    (a.output/'report.md').write_text(report)
    issue=f'''## Issue #828 final numerical closure

**Numerical convergence: {summary['numericalConvergence']['classification']}** after the preregistered row26-only continuation. Row26 combined n=10: baseline SE `{bse:.5f}`, profile SE `{pse:.5f}`, paired-delta SE `{dse:.5f}` mag (threshold `<=0.030`).

Balanced six-pair scientific conclusions are intentionally unchanged:
- **-4 to -5 deg:** profile effect `{early['profileMinusBaselineMeanDeltaMag']:+.4f}` mag, 95% CI `[{early['ci95Mag'][0]:+.4f}, {early['ci95Mag'][1]:+.4f}]`; Taylor agreement **worse**.
- **-5.5 to -6.3 deg:** profile effect `{late['profileMinusBaselineMeanDeltaMag']:+.4f}` mag, 95% CI `[{late['ci95Mag'][0]:+.4f}, {late['ci95Mag'][1]:+.4f}]`; Taylor agreement **better** in the no-fit diagnostic (row26 absolute agreement remains background/lunar-sensitive).
- **Koomen angular-field diagnostic:** wide SQM minus true zenith `{k['meanAcrossRowsUsingSixIndependentPairMeansMag']:+.4f}` mag, 95% CI `[{k['ci95Mag'][0]:+.4f}, {k['ci95Mag'][1]:+.4f}]`, about `{k['absoluteFractionOf039Offset']:.3f}` of `0.39` in absolute size; no offset fit.

Proxy profile provenance and anti-fitting boundaries are unchanged; no production/Level-B/first-seeing claim.
'''
    (a.output/'issue-summary.md').write_text(issue)
    print(report)


if __name__ == '__main__':
    main()
