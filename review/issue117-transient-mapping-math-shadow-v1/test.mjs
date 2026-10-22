import assert from 'node:assert/strict';
import fs from 'node:fs';
import { pathToFileURL } from 'node:url';
import {
  currentDirectDebtThreshold,
  endpointFloorThreshold,
  pathEnvelopeThreshold,
  adaptationThresholdRatio,
  ISSUE117_MAPPING_CONSTANTS,
} from './candidate_mappings.mjs';

const appPath = process.env.APP_HUMAN_THRESHOLD;
if (!appPath) throw new Error('APP_HUMAN_THRESHOLD required');
const human = await import(pathToFileURL(appPath).href);
const threshold = B => human.thresholdLux({ backgroundLuminanceCdM2: B, fieldFactor: 3.14, branch: 'full' });
const magDeltaForThresholdRatio = ratio => 2.5 * Math.log10(ratio);
const approx = (a,b,tol=1e-12,msg='value') => assert.ok(Number.isFinite(a) && Math.abs(a-b)<=tol, `${msg}: ${a} vs ${b}`);

const localMaxB = ISSUE117_MAPPING_CONSTANTS.localMaximumBackgroundCdM2;
const report = {
  schemaVersion: 1,
  diagnosticId: 'issue117-transient-mapping-math-shadow-v1',
  applicationSha: 'e0da52eb0a2d5bac333da6572f51df52ea7e676e',
  fieldFactor: 3.14,
  localMaximumBackgroundCdM2: localMaxB,
  candidates: ['current-direct-debt','endpoint-floor','path-envelope','adaptation-threshold-ratio'],
  productionActivationAuthorized: false,
  transientSemanticChangePerformed: false,
};

// Equilibrium identity over a wide positive B grid.
const bGrid = Array.from({length: 161}, (_,i) => 10 ** (-4 + i * (7/160)));
for (const B of bGrid) {
  const eq = threshold(B);
  approx(endpointFloorThreshold({physicalDetectionB:B,effectiveB:B,thresholdLux:threshold}),eq,1e-22,'C1 equilibrium');
  approx(pathEnvelopeThreshold({physicalDetectionB:B,effectiveB:B,thresholdLux:threshold}),eq,1e-22,'C2 equilibrium');
  approx(adaptationThresholdRatio({adaptationFieldB:B,laggedAdaptationB:B,physicalDetectionB:B,thresholdLux:threshold}),eq,1e-22,'C3 equilibrium');
}

// Frozen current-mapping topology witness.
const currentWitness = {
  B: 0.03,
  Beff: 0.04,
  equilibrium: threshold(0.03),
  current: currentDirectDebtThreshold({physicalDetectionB:0.03,effectiveB:0.04,thresholdLux:threshold}),
};
assert.ok(currentWitness.current < currentWitness.equilibrium, 'current mapping must reproduce known beneficial-debt topology witness');
currentWitness.formalBeneficialMagnitude = -magDeltaForThresholdRatio(currentWitness.equilibrium/currentWitness.current);
report.currentTopologyWitness = currentWitness;

// Candidate 1 and 2 are provably distinct for a path crossing the local maximum.
const B0 = 0.015, B1 = 0.060;
const c1 = endpointFloorThreshold({physicalDetectionB:B0,effectiveB:B1,thresholdLux:threshold});
const c2 = pathEnvelopeThreshold({physicalDetectionB:B0,effectiveB:B1,thresholdLux:threshold});
const localMaxT = threshold(localMaxB);
assert.ok(c2 > c1, 'path envelope must exceed endpoint floor on frozen interior-maximum witness');
approx(c2, localMaxT, 1e-22, 'C2 local-max envelope');
report.endpointVsEnvelopeWitness = {
  physicalB: B0, effectiveB: B1, endpointFloorThresholdLux: c1, pathEnvelopeThresholdLux: c2,
  ratio: c2/c1, stricterMagnitude: magDeltaForThresholdRatio(c2/c1),
};

// Candidate 1 fails debt monotonicity, while Candidate 2 retains the crossed worst point.
const Dpeak = localMaxB - B0;
const c1AtPeak = endpointFloorThreshold({physicalDetectionB:B0,effectiveB:B0+Dpeak,thresholdLux:threshold});
const c1After = endpointFloorThreshold({physicalDetectionB:B0,effectiveB:B1,thresholdLux:threshold});
assert.ok(c1After < c1AtPeak, 'Candidate 1 expected debt-monotonicity violation absent');
const c2AtPeak = pathEnvelopeThreshold({physicalDetectionB:B0,effectiveB:B0+Dpeak,thresholdLux:threshold});
const c2After = pathEnvelopeThreshold({physicalDetectionB:B0,effectiveB:B1,thresholdLux:threshold});
approx(c2After,c2AtPeak,1e-22,'Candidate 2 must retain crossed interior maximum');
report.candidate1DebtMonotonicityCounterexample = {
  physicalB:B0, smallerDebt:Dpeak, largerDebt:B1-B0,
  thresholdAtSmallerDebt:c1AtPeak, thresholdAtLargerDebt:c1After,
  largerDebtThresholdRatio:c1After/c1AtPeak,
  easierByMagnitude: magDeltaForThresholdRatio(c1AtPeak/c1After),
};

// Dense synthetic increasing-debt probes. Candidate 1 is allowed to fail; C2/C3 must not.
const physicalGrid = Array.from({length:121}, (_,i)=>10**(-3 + i*(3/120))); // 0.001..1 cd/m2
let candidate1MonotonicViolations=0, candidate2MonotonicViolations=0, candidate3MonotonicViolations=0;
let candidate1BeneficialViolations=0, candidate2BeneficialViolations=0, candidate3BeneficialViolations=0;
let probes=0;
for (const Bd of physicalGrid) {
  const eq = threshold(Bd);
  let prev1=null, prev2=null, prev3=null;
  for (let j=0;j<=160;j++) {
    const factor = 1 + j*(4/160); // effective/adaptation-lag factor 1..5
    const Beff = Bd*factor;
    const v1=endpointFloorThreshold({physicalDetectionB:Bd,effectiveB:Beff,thresholdLux:threshold});
    const v2=pathEnvelopeThreshold({physicalDetectionB:Bd,effectiveB:Beff,thresholdLux:threshold});
    const v3=adaptationThresholdRatio({adaptationFieldB:Bd,laggedAdaptationB:Beff,physicalDetectionB:Bd,thresholdLux:threshold});
    probes++;
    if (v1 < eq*(1-1e-12)) candidate1BeneficialViolations++;
    if (v2 < eq*(1-1e-12)) candidate2BeneficialViolations++;
    if (v3 < eq*(1-1e-12)) candidate3BeneficialViolations++;
    if (prev1!==null && v1 < prev1*(1-1e-12)) candidate1MonotonicViolations++;
    if (prev2!==null && v2 < prev2*(1-1e-12)) candidate2MonotonicViolations++;
    if (prev3!==null && v3 < prev3*(1-1e-12)) candidate3MonotonicViolations++;
    prev1=v1; prev2=v2; prev3=v3;
    // Under current-main equal adaptation/detection B, C3 is algebraically C2.
    approx(v3,v2,Math.max(1e-22,Math.abs(v2)*1e-12),'C3=C2 when Ba=Bd');
  }
}
assert.equal(candidate1BeneficialViolations,0);
assert.equal(candidate2BeneficialViolations,0);
assert.equal(candidate3BeneficialViolations,0);
assert.ok(candidate1MonotonicViolations>0,'Candidate 1 should fail stronger debt monotonicity on synthetic grid');
assert.equal(candidate2MonotonicViolations,0,'Candidate 2 debt monotonicity');
assert.equal(candidate3MonotonicViolations,0,'Candidate 3 debt monotonicity');
report.syntheticGrid = {probes,candidate1BeneficialViolations,candidate2BeneficialViolations,candidate3BeneficialViolations,candidate1MonotonicViolations,candidate2MonotonicViolations,candidate3MonotonicViolations};

// On known monotone-increasing intervals, path-envelope must equal current endpoint mapping.
for (const [lo,hi] of [[0.001,0.02],[0.05,0.1],[0.08,1.0]]) {
  const direct=threshold(hi);
  const env=pathEnvelopeThreshold({physicalDetectionB:lo,effectiveB:hi,thresholdLux:threshold});
  approx(env,direct,Math.max(1e-22,Math.abs(direct)*1e-12),`monotone interval ${lo}-${hi}`);
}

// Candidate 3 keeps adaptation field separate from local detection B and remains >= local equilibrium.
const splitCases = [
  {Ba:0.015,Blag:0.06,Bd:0.006},
  {Ba:0.03,Blag:0.04,Bd:0.08},
  {Ba:0.006,Blag:0.02,Bd:0.03},
  {Ba:0.05,Blag:0.12,Bd:0.015},
];
report.splitFieldCases=[];
for (const s of splitCases) {
  const out=adaptationThresholdRatio({adaptationFieldB:s.Ba,laggedAdaptationB:s.Blag,physicalDetectionB:s.Bd,thresholdLux:threshold});
  const eq=threshold(s.Bd);
  assert.ok(out>=eq*(1-1e-12));
  report.splitFieldCases.push({...s,equilibriumThresholdLux:eq,candidate3ThresholdLux:out,ratio:out/eq});
}

const outPath=process.env.REPORT_PATH;
if (!outPath) throw new Error('REPORT_PATH required');
fs.writeFileSync(outPath,JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));
