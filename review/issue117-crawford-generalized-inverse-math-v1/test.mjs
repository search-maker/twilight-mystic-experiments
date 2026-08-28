import assert from 'node:assert/strict';
import fs from 'node:fs';
import { pathToFileURL } from 'node:url';
import {
  anchoredPathEnvelopeThreshold,
  thresholdDerivedEquivalentBackground,
  candidate4Threshold,
  CRUMEY_EQ34_LOCAL_MAX_B,
} from './candidate4.mjs';

const appPath = process.env.APP_HUMAN_THRESHOLD;
const reportPath = process.env.REPORT_PATH;
if (!appPath || !reportPath) throw new Error('APP_HUMAN_THRESHOLD and REPORT_PATH required');
const human = await import(pathToFileURL(appPath).href);
const T = B => human.thresholdLux({ backgroundLuminanceCdM2: B, fieldFactor: 3.14, branch: 'full' });
const mag = ratio => 2.5 * Math.log10(ratio);
const close = (a,b,rtol=1e-10,msg='close') => assert.ok(Math.abs(a-b) <= Math.max(1e-20, Math.abs(b)*rtol), `${msg}: ${a} vs ${b}`);

const report = {
  schemaVersion: 1,
  diagnosticId: 'issue117-crawford-generalized-inverse-math-v1',
  applicationSha: 'e0da52eb0a2d5bac333da6572f51df52ea7e676e',
  candidateProtocolHead: 'd31b44f7d4b67ad3adf4c5386517f625bf56d8da',
  fieldFactor: 3.14,
  productionActivationAuthorized: false,
  semanticChangePerformed: false,
};

// Current same-field identity: Candidate 4 must collapse to Candidate 2 path envelope.
let sameFieldProbes = 0;
let sameFieldMaxRelativeError = 0;
for (let i=0;i<=80;i++) {
  const Ba = 10 ** (-3 + i*(3/80));
  for (let j=0;j<=80;j++) {
    const factor = 1 + j*(4/80);
    const Blag = Ba*factor;
    const c2 = anchoredPathEnvelopeThreshold({anchorB:Ba,endB:Blag,thresholdLux:T});
    const c4 = candidate4Threshold({adaptationFieldB:Ba,laggedAdaptationB:Blag,physicalDetectionB:Ba,thresholdLux:T});
    const rel = Math.abs(c4.thresholdIlluminanceLux-c2)/c2;
    sameFieldMaxRelativeError = Math.max(sameFieldMaxRelativeError,rel);
    close(c4.thresholdIlluminanceLux,c2,8e-11,'same-field C4=C2');
    assert.ok(c4.equivalentBackgroundCdM2 >= -1e-16);
    close(c4.inverseForwardThresholdLux,c4.adaptationThresholdLux,8e-11,'inverse forward');
    sameFieldProbes++;
  }
}
report.sameFieldIdentity = { probes:sameFieldProbes, maxRelativeError:sameFieldMaxRelativeError };

// Frozen topology witness demonstrates threshold-derived B_eq need not equal photometric lag.
const topo = thresholdDerivedEquivalentBackground({adaptationFieldB:0.015,laggedAdaptationB:0.060,thresholdLux:T});
assert.ok(Math.abs(topo.inferredTotalAdaptationBackgroundCdM2-CRUMEY_EQ34_LOCAL_MAX_B) < 1e-9,
  `left generalized inverse should land at local maximum onset: ${topo.inferredTotalAdaptationBackgroundCdM2}`);
assert.ok(topo.equivalentBackgroundCdM2 < 0.010, 'threshold-derived equivalent background should be much smaller than direct 0.045 photometric lag in plateau witness');
report.topologyWitness = {
  adaptationFieldB:0.015,
  laggedAdaptationB:0.060,
  directPhotometricLagCdM2:0.045,
  inferredTotalAdaptationBackgroundCdM2:topo.inferredTotalAdaptationBackgroundCdM2,
  thresholdDerivedEquivalentBackgroundCdM2:topo.equivalentBackgroundCdM2,
  ratioEquivalentToDirectLag:topo.equivalentBackgroundCdM2/0.045,
  adaptationThresholdLux:topo.adaptationThresholdLux,
};

// Equilibrium identity for split detection fields.
const detectionGrid=[0.003,0.01,0.03,0.08,0.3];
const adaptationGrid=[0.004,0.015,0.04,0.1];
for (const Ba of adaptationGrid) for (const Bd of detectionGrid) {
  const c4=candidate4Threshold({adaptationFieldB:Ba,laggedAdaptationB:Ba,physicalDetectionB:Bd,thresholdLux:T});
  close(c4.thresholdIlluminanceLux,T(Bd),1e-12,'split-field equilibrium identity');
  assert.equal(c4.equivalentBackgroundCdM2,0);
}

// Split-field no-benefit + debt monotonicity grid.
let splitProbes=0, splitBeneficialViolations=0, splitMonotonicityViolations=0;
let maxEquivalentFractionOfDirectLag=0;
let minEquivalentFractionOfDirectLag=Infinity;
for (const Ba of adaptationGrid) {
  for (const Bd of detectionGrid) {
    let previous=null;
    for (let j=0;j<=100;j++) {
      const factor=1+j*(5/100);
      const Blag=Ba*factor;
      const c4=candidate4Threshold({adaptationFieldB:Ba,laggedAdaptationB:Blag,physicalDetectionB:Bd,thresholdLux:T});
      const eq=T(Bd);
      if (c4.thresholdIlluminanceLux < eq*(1-1e-10)) splitBeneficialViolations++;
      if (previous!==null && c4.thresholdIlluminanceLux < previous*(1-1e-10)) splitMonotonicityViolations++;
      previous=c4.thresholdIlluminanceLux;
      const direct=Blag-Ba;
      if (direct>0) {
        const ratio=c4.equivalentBackgroundCdM2/direct;
        maxEquivalentFractionOfDirectLag=Math.max(maxEquivalentFractionOfDirectLag,ratio);
        minEquivalentFractionOfDirectLag=Math.min(minEquivalentFractionOfDirectLag,ratio);
      }
      splitProbes++;
    }
  }
}
assert.equal(splitBeneficialViolations,0,'Candidate4 better-than-equilibrium violation');
assert.equal(splitMonotonicityViolations,0,'Candidate4 debt monotonicity violation');
report.splitFieldSyntheticGrid={
  probes:splitProbes,
  beneficialViolations:splitBeneficialViolations,
  debtMonotonicityViolations:splitMonotonicityViolations,
  minThresholdDerivedEquivalentFractionOfDirectPhotometricLag:Number.isFinite(minEquivalentFractionOfDirectLag)?minEquivalentFractionOfDirectLag:null,
  maxThresholdDerivedEquivalentFractionOfDirectPhotometricLag:maxEquivalentFractionOfDirectLag,
};

// Demonstrate Candidate 4 and threshold-ratio structure can differ when Ba != Bd.
const splitWitness={Ba:0.015,Blag:0.060,Bd:0.08};
const c4= candidate4Threshold({adaptationFieldB:splitWitness.Ba,laggedAdaptationB:splitWitness.Blag,physicalDetectionB:splitWitness.Bd,thresholdLux:T});
const adaptationEnvelope=anchoredPathEnvelopeThreshold({anchorB:splitWitness.Ba,endB:splitWitness.Blag,thresholdLux:T});
const ratioCandidate = T(splitWitness.Bd) * (adaptationEnvelope/T(splitWitness.Ba));
assert.ok(Math.abs(c4.thresholdIlluminanceLux-ratioCandidate) > Math.max(1e-20,ratioCandidate*1e-5), 'split-field C4 should be distinguishable from threshold-ratio witness');
report.splitFieldCandidateDifference={
  ...splitWitness,
  candidate4ThresholdLux:c4.thresholdIlluminanceLux,
  thresholdRatioCandidateLux:ratioCandidate,
  candidate4OverRatioCandidate:c4.thresholdIlluminanceLux/ratioCandidate,
  magnitudeDifference:mag(c4.thresholdIlluminanceLux/ratioCandidate),
  thresholdDerivedEquivalentBackgroundCdM2:c4.equivalentBackgroundCdM2,
};

fs.writeFileSync(reportPath,JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));
