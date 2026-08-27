import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

import {
  AVPS_LEVEL_B_CONTRASTS,
  AVPS_FIELD_FACTOR,
  AVPS_STATE_IDS,
  replicateLevelBContrasts,
  summarizeLevelBThreeReplicates,
} from './level_b_analysis.mjs';

const EXPECTED_HUMAN_THRESHOLD_GIT_BLOB = 'bb4cd0ff02159ecffe276022cec9d292c7a434a3';
const EXPECTED_STATUS = 'COMPLETE_EXACT_360_ANALYSIS_INPUT_AFTER_AGGREGATE_VERIFICATION';

function die(message) {
  throw new Error(message);
}

function sha256File(filePath) {
  return crypto.createHash('sha256').update(fs.readFileSync(filePath)).digest('hex');
}

function gitBlobSha1(filePath) {
  const data = fs.readFileSync(filePath);
  const header = Buffer.from(`blob ${data.length}\0`, 'utf8');
  return crypto.createHash('sha1').update(header).update(data).digest('hex');
}

function canonicalSha256(value) {
  return crypto.createHash('sha256').update(JSON.stringify(sortObject(value))).digest('hex');
}

function sortObject(value) {
  if (Array.isArray(value)) return value.map(sortObject);
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.keys(value).sort().map(key => [key, sortObject(value[key])]));
  }
  return value;
}

function parseArgs(argv) {
  const out = {};
  for (let i = 2; i < argv.length; i += 2) {
    const key = argv[i];
    const value = argv[i + 1];
    if (!key?.startsWith('--') || value === undefined) die(`invalid argument sequence near ${key}`);
    out[key.slice(2)] = value;
  }
  for (const key of ['input', 'input-sha256', 'human-threshold', 'output']) {
    if (!out[key]) die(`missing --${key}`);
  }
  return out;
}

function exactStateUniverse(recordsByState) {
  const got = Object.keys(recordsByState ?? {}).sort();
  const expected = [...AVPS_STATE_IDS].sort();
  return JSON.stringify(got) === JSON.stringify(expected);
}

const args = parseArgs(process.argv);
const inputPath = path.resolve(args.input);
const humanPath = path.resolve(args['human-threshold']);
const outputPath = path.resolve(args.output);
if (!/^[0-9a-f]{64}$/.test(args['input-sha256'])) die('input SHA-256 argument malformed');
if (sha256File(inputPath) !== args['input-sha256']) die('Level-B input raw file SHA-256 drift');

if (gitBlobSha1(humanPath) !== EXPECTED_HUMAN_THRESHOLD_GIT_BLOB) {
  die('bound human-threshold.mjs Git blob drift');
}
const human = await import(pathToFileURL(humanPath).href);
if (typeof human.limitingVMagnitude !== 'function') {
  die('bound human-threshold.mjs does not export limitingVMagnitude');
}

const input = JSON.parse(fs.readFileSync(inputPath, 'utf8'));
if (input?.stageId !== 'aerosol-vertical-profile-sensitivity-v1-verified-analysis-input') die('Level-B input stage drift');
if (input?.status !== EXPECTED_STATUS) die('Level-B input status drift');
if (input?.caseCount !== 360 || input?.groupCount !== 72 || input?.analysisCellCount !== 24) die('Level-B input cardinality drift');
if (input?.statesPerGroup !== 5 || input?.primaryContrastCountPerCell !== 4) die('Level-B state/contrast cardinality drift');
if (input?.sourceAcquisitionStatus !== 'COMPLETE_EXACT_360_CASE_ARTIFACT_UNIVERSE_RESULTS_STILL_CLOSED') {
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
    reps.push(replicateLevelBContrasts(row.recordsByState, human.limitingVMagnitude, AVPS_FIELD_FACTOR));
  }
  const summary = summarizeLevelBThreeReplicates(reps);
  if (summary?.status !== 'COMPLETED_PREREGISTERED_AVPS_LEVEL_B_SUMMARY') die(`${cellId}: Level-B summary status drift`);
  if (summary?.fieldFactor !== 3.14) die(`${cellId}: F drift`);
  if (Object.keys(summary.contrasts ?? {}).sort().join('|') !== [...AVPS_LEVEL_B_CONTRASTS].sort().join('|')) {
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
  stageId: 'aerosol-vertical-profile-sensitivity-v1-level-b-analysis',
  status: 'COMPLETED_PREREGISTERED_AVPS_V1_LEVEL_B_AFTER_EXACT_360_GATE',
  workflowRunId: input.workflowRunId,
  scientificOrdinal: input.scientificOrdinal,
  caseCount: 360,
  groupCount: 72,
  analysisCellCount: 24,
  statesPerGroup: 5,
  primaryContrastCountPerCell: 4,
  fieldFactor: AVPS_FIELD_FACTOR,
  humanThresholdGitBlobSha1: EXPECTED_HUMAN_THRESHOLD_GIT_BLOB,
  humanThresholdModel: 'Crumey 2014 eq.34 full branch',
  executionDesignCanonicalSha256: input.executionDesignCanonicalSha256,
  sourceAnalysisInputRawSha256: args['input-sha256'],
  sourceAnalysisInputContentSha256: input.contentSha256,
  pValuesPermitted: false,
  confidenceIntervalsPermitted: false,
  epsilonSubstitutionPermitted: false,
  universalSunDepressionToMinutesConversionPermitted: false,
  timeConversionRequiresActualDateLocationSolarDepressionRate: true,
  taylorOrJerusalemScoringPerformed: false,
  cells,
};
output.contentSha256 = canonicalSha256(output);
fs.writeFileSync(outputPath, `${JSON.stringify(output, null, 2)}\n`, 'utf8');
