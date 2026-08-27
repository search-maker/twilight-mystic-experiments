import { writeFile, mkdir } from 'node:fs/promises';
import { resolve, join } from 'node:path';
import { pathToFileURL } from 'node:url';

const APP_SHA = '80110c8cb4575c7be3c91b4817be5126c40b2b15';
const MILLILAMBERT_TO_CD_M2 = 3.183;
const START_ML = 325;
const END_ML = 3.25e-5;
const START_CD_M2 = START_ML * MILLILAMBERT_TO_CD_M2;
const END_CD_M2 = END_ML * MILLILAMBERT_TO_CD_M2;
const DURATIONS_MIN = Object.freeze([3.5, 7, 14, 21]);
const TAUS = Object.freeze([20, 30, 45, 60]);
const DT_SECONDS = 1;

function parseArgs(argv) {
  const out = { appRoot: null, output: 'diagnostic-output/transient-adaptation-spillmann-audit-v1.json' };
  for (let i = 2; i < argv.length; i += 1) {
    if (argv[i] === '--app-root') out.appRoot = argv[++i];
    else if (argv[i] === '--output') out.output = argv[++i];
    else throw new Error(`unknown arg ${argv[i]}`);
  }
  if (!out.appRoot) throw new Error('--app-root required');
  return out;
}

function logRampValue(t, durationSeconds) {
  const f = Math.max(0, Math.min(1, t / durationSeconds));
  return 10 ** (Math.log10(START_CD_M2) + f * (Math.log10(END_CD_M2) - Math.log10(START_CD_M2)));
}

function samplesFor(durationMinutes) {
  const durationSeconds = durationMinutes * 60;
  const samples = [];
  for (let t = 0; t <= durationSeconds + 1e-9; t += DT_SECONDS) {
    samples.push(Object.freeze({
      timestampMs: t * 1000,
      adaptationFieldLuminanceCdM2: logRampValue(t, durationSeconds),
      detectionBackgroundLuminanceCdM2: logRampValue(t, durationSeconds),
    }));
  }
  return samples;
}

const args = parseArgs(process.argv);
const appRoot = resolve(args.appRoot);
const v3 = join(appRoot, 'scientific-tools', 'visibility-v3');
const [adaptation, threshold] = await Promise.all([
  import(pathToFileURL(join(v3, 'transient-adaptation.mjs')).href),
  import(pathToFileURL(join(v3, 'human-threshold.mjs')).href),
]);

if (adaptation.DEFAULT_TRANSIENT_ADAPTATION_TAU_SECONDS !== 30) throw new Error('default tau drift');
if (JSON.stringify([...adaptation.TRANSIENT_ADAPTATION_SENSITIVITY_TAU_SECONDS]) !== JSON.stringify(TAUS)) throw new Error('tau sensitivity set drift');

const rows = [];
for (const durationMinutes of DURATIONS_MIN) {
  const inputSamples = samplesFor(durationMinutes);
  for (const tauSeconds of TAUS) {
    const timeline = adaptation.buildTransientAdaptationTimeline(inputSamples, { tauSeconds });
    const dynamic = timeline.states.map((state, i) => {
      const physical = inputSamples[i].adaptationFieldLuminanceCdM2;
      const effective = state.effectiveThresholdBackgroundCdM2;
      const steadyThresholdLux = threshold.crumeyBasePointSourceThresholdLux(physical);
      const transientThresholdLux = threshold.crumeyBasePointSourceThresholdLux(effective);
      return Object.freeze({
        tSeconds: inputSamples[i].timestampMs / 1000,
        physicalBackgroundCdM2: physical,
        effectiveThresholdBackgroundCdM2: effective,
        equivalentAdaptationDebtCdM2: state.equivalentAdaptationDebtCdM2,
        adaptedLog10Luminance: state.adaptedLog10Luminance,
        backgroundLagLog10: Math.log10(state.effectiveAdaptationBackgroundCdM2 / physical),
        thresholdElevationLog10: Math.log10(transientThresholdLux / steadyThresholdLux),
        thresholdPenaltyMagEquivalent: 2.5 * Math.log10(transientThresholdLux / steadyThresholdLux),
      });
    });
    const maxRow = dynamic.reduce((a, b) => b.thresholdElevationLog10 > a.thresholdElevationLog10 ? b : a);
    const end = dynamic.at(-1);
    const atHalf = dynamic[Math.round((durationMinutes * 60 / 2) / DT_SECONDS)];
    rows.push(Object.freeze({
      durationMinutes,
      tauSeconds,
      maxThresholdElevationLog10: maxRow.thresholdElevationLog10,
      maxThresholdElevationTimeSeconds: maxRow.tSeconds,
      maxThresholdPenaltyMagEquivalent: maxRow.thresholdPenaltyMagEquivalent,
      thresholdElevationAtRampEndLog10: end.thresholdElevationLog10,
      thresholdPenaltyAtRampEndMagEquivalent: end.thresholdPenaltyMagEquivalent,
      backgroundLagAtRampEndLog10: end.backgroundLagLog10,
      thresholdElevationAtHalfRampLog10: atHalf.thresholdElevationLog10,
      dynamic,
    }));
  }
}

const byDuration = DURATIONS_MIN.map(durationMinutes => {
  const subset = rows.filter(r => r.durationMinutes === durationMinutes);
  return Object.freeze({
    durationMinutes,
    tauRangeSeconds: [Math.min(...TAUS), Math.max(...TAUS)],
    maxThresholdElevationAcrossTauRangeLog10: [
      Math.min(...subset.map(r => r.maxThresholdElevationLog10)),
      Math.max(...subset.map(r => r.maxThresholdElevationLog10)),
    ],
    endThresholdElevationAcrossTauRangeLog10: [
      Math.min(...subset.map(r => r.thresholdElevationAtRampEndLog10)),
      Math.max(...subset.map(r => r.thresholdElevationAtRampEndLog10)),
    ],
  });
});

const result = Object.freeze({
  schemaVersion: 1,
  status: 'TRANSIENT_ADAPTATION_SPILLMANN_RAMP_AUDIT_COMPLETE',
  applicationSha: APP_SHA,
  modelId: adaptation.TRANSIENT_ADAPTATION_MODEL_ID,
  modelValidationTier: adaptation.TRANSIENT_ADAPTATION_VALIDATION_TIER,
  defaultTauSeconds: adaptation.DEFAULT_TRANSIENT_ADAPTATION_TAU_SECONDS,
  tauSensitivitySeconds: [...adaptation.TRANSIENT_ADAPTATION_SENSITIVITY_TAU_SECONDS],
  sourceExperiment: Object.freeze({
    citation: 'Spillmann, Nowlan & Bernholz, JOSA 62 (1972) 177-181',
    doi: '10.1364/JOSA.62.000177',
    backgroundStartMillilambert: START_ML,
    backgroundEndMillilambert: END_ML,
    luminanceChangeLog10: Math.log10(START_ML / END_ML),
    durationsMinutes: DURATIONS_MIN,
    publishedSummaryConstraints: Object.freeze({
      steepPreexposedMaximumThresholdElevationLog10Approx: 1.25,
      slow21MinLowBackgroundThresholdElevationLog10Approx: 0.2,
      steepNoPreexposureMaximumThresholdElevationLog10Approx: 0.4,
    }),
  }),
  unitConversion: Object.freeze({ millilambertToCdM2: MILLILAMBERT_TO_CD_M2, startCdM2: START_CD_M2, endCdM2: END_CD_M2 }),
  currentModelComparisonScope: Object.freeze({
    modelsPreexposedEquilibriumAtFirstSampleOnly: true,
    modelsPublishedNoPreexposureCondition: false,
    reasonNoPreexposureUnsupported: 'Current waning-only v0 refuses an initial adapted state darker than the first adapting field and contains no independent bleach/equivalent-background state.',
    fitTauToPublishedResult: false,
    sourceCurveDigitizedOrFitted: false,
    comparisonIsScaleAndShapeAuditOnly: true,
  }),
  byDuration,
  rows,
  claimBoundary: Object.freeze({
    literatureAuditOnly: true,
    tauCalibrated: false,
    naturalTwilightValidated: false,
    humanFirstSeeingValidated: false,
    productionAuthorized: false,
    noParameterChange: true,
    noMystic: true,
  }),
});

await mkdir(resolve(args.output, '..'), { recursive: true });
await writeFile(resolve(args.output), JSON.stringify(result, null, 2) + '\n');
console.log(JSON.stringify({ status: result.status, byDuration: result.byDuration, defaultTau: rows.filter(r => r.tauSeconds === 30).map(r => ({ durationMinutes: r.durationMinutes, max: r.maxThresholdElevationLog10, end: r.thresholdElevationAtRampEndLog10 })) }, null, 2));
