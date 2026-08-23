import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

import {
  AFPF_LEVEL_B_CONTRASTS,
  AFPF_FIELD_FACTOR,
  AFPF_STATE_IDS,
  replicateLevelBContrasts,
  summarizeLevelBThreeReplicates,
} from '../level_b_analysis.mjs';

const EXPECTED_HUMAN_THRESHOLD_GIT_BLOB = 'bb4cd0ff02159ecffe276022cec9d292c7a434a3';
const EXPECTED_STATUS = 'COMPLETE_EXACT_360_LEVEL_B_INPUT_AFTER_AGGREGATE_VERIFICATION';

function die(message) {
  throw new Error(message);
}

function gitBlobSha1(filePath) {
  const data = fs.readFileSync(filePath);
  const header = Buffer.from(`blob ${data.length}\0`, 'utf8');
  return crypto.createHash('sha1').update(header).update(data).digest('hex');
}

function parseArgs(argv) {
  const out = {};
  for (let i = 2; i < argv.length; i += 2) {
    const key = argv[i];
    const value = argv[i + 1];
    if (!key?.startsWith('--') || value === undefined) die(`invalid argument sequence near ${key}`);
    out[key.slice(2)] = value;
  }
  for (const key of ['input', 'human-threshold', 'output']) {
    if (!out[key]) die(`missing --${key}`);
  }
  return out;
}

function exactStateUniverse(recordsByState) {
  const got = Object.keys(recordsByState ?? {}).sort();
  const expected = [...AFPF_STATE_IDS].sort();
  return JSON.stringify(got) === JSON.stringify(expected);
}

const args = parseArgs(process.argv);
const inputPath = path.resolve(args.input);
const humanPath = path.resolve(args['human-threshold']);
const outputPath = path.resolve(args.output);

if (gitBlobSha1(humanPath) !== EXPECTED_HUMAN_THRESHOLD_GIT_BLOB) {
  die('bound human-threshold.mjs Git blob drift');
}
const human = await import(pathToFileURL(humanPath).href);
if (typeof human.limitingVMagnitude !== 'function') {
  die('bound human-threshold.mjs does not export limitingVMagnitude');
}

const input = JSON.parse(fs.readFileSync(inputPath, 'utf8'));
if (input?.stageId !== 'aerosol-full-phase-function-sensitivity-v1-level-b-input') die('Level-B input stage drift');
if (input?.status !== EXPECTED_STATUS) die('Level-B input status drift');
if (input?.caseCount !== 360 || input?.groupCount !== 72 || input?.analysisCellCount !== 24) die('Level-B input cardinality drift');
if (input?.statesPerGroup !== 5 || input?.contrastCountPerCell !== 7) die('Level-B state/contrast cardinality drift');
if (input?.sourceAcquisitionStatus !== 'COMPLETE_EXACT_360_CASE_ARTIFACT_UNIVERSE' || input?.sourceCaseArtifactCount !== 360) {
  die('Level-B input was not produced after exact-360 aggregate acquisition success');
}
if (input?.resultOpeningBeforeAggregatePermitted !== false || input?.epsilonSubstitutionPermitted !== false) {
  die('Level-B input numeric/result-opening boundary drift');
}
if (!Array.isArray(input?.cells) || input.cells.length !== 24) die('Level-B requires exactly 24 cells');

const seenCells = new Set();
const cells = [];
for (const cell of input.cells) {
  const cellId = String(cell?.analysisCellId ?? '');
  if (!cellId || seenCells.has(cellId)) die(`Level-B duplicate/missing cell identity: ${cellId}`);
  seenCells.add(cellId);
  if (!Array.isArray(cell?.replicates) || cell.replicates.length !== 3) die(`${cellId}: exactly three replicates required`);
  const reps = [];
  for (let index = 0; index < 3; index += 1) {
    const row = cell.replicates[index];
    if (row?.replicate !== index + 1) die(`${cellId}: replicate ordering/identity drift`);
    if (!exactStateUniverse(row.recordsByState)) die(`${cellId}: exact five-state Level-B universe required`);
    reps.push(replicateLevelBContrasts(row.recordsByState, human.limitingVMagnitude, AFPF_FIELD_FACTOR));
  }
  const summary = summarizeLevelBThreeReplicates(reps);
  if (summary?.status !== 'COMPLETED_PREREGISTERED_AFPF_LEVEL_B_SUMMARY') die(`${cellId}: Level-B summary status drift`);
  if (summary?.contrastCount !== 7 || summary?.priorityShapeContrast !== 'desert_spheroids_vs_desert') {
    die(`${cellId}: Level-B contrast contract drift`);
  }
  if (Object.keys(summary.contrasts ?? {}).sort().join('|') !== AFPF_LEVEL_B_CONTRASTS.map(row => row.contrastId).sort().join('|')) {
    die(`${cellId}: Level-B contrast universe drift`);
  }
  cells.push({
    analysisCellId: cellId,
    sunDepressionDeg: cell.sunDepressionDeg,
    geometryId: cell.geometryId,
    geometryTag: cell.geometryTag,
    targetAltitudeDeg: cell.targetAltitudeDeg,
    relativeAzimuthDeg: cell.relativeAzimuthDeg,
    aod550: cell.aod550,
    summary,
  });
}

const output = {
  schemaVersion: 1,
  stageId: 'aerosol-full-phase-function-sensitivity-v1-level-b-analysis',
  status: 'COMPLETED_PREREGISTERED_AFPF_V1_LEVEL_B',
  workflowRunId: input.workflowRunId,
  scientificOrdinal: input.scientificOrdinal,
  caseCount: 360,
  groupCount: 72,
  analysisCellCount: 24,
  statesPerGroup: 5,
  contrastCountPerCell: 7,
  priorityShapeContrast: 'desert_spheroids_vs_desert',
  fieldFactor: AFPF_FIELD_FACTOR,
  humanThresholdGitBlobSha1: EXPECTED_HUMAN_THRESHOLD_GIT_BLOB,
  humanThresholdModel: 'Crumey 2014 eq.34 full branch',
  designCanonicalSha256: input.designCanonicalSha256,
  pValuesPermitted: false,
  confidenceIntervalsPermitted: false,
  epsilonSubstitutionPermitted: false,
  universalSunDepressionToMinutesConversionPermitted: false,
  cells,
};

fs.writeFileSync(outputPath, `${JSON.stringify(output, null, 2)}\n`, 'utf8');
