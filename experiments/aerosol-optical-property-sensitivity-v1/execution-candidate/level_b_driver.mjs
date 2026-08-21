import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { replicateLevelBContrasts, summarizeLevelBThreeReplicates } from '../level_b_analysis.mjs';

const EXPECTED_HUMAN_BLOB = 'bb4cd0ff02159ecffe276022cec9d292c7a434a3';
const EXPECTED_STARSVISIBILITY_MAIN = 'a422afe5fc4197ab15323bafb15512001e061454';
const EXPECTED_STATES = new Set(['native-rural-ss','ssa085-g060','ssa085-g080','ssa098-g060','ssa098-g080']);

function refuse(message) { throw new Error(message); }

function walk(root) {
  const out = [];
  for (const entry of fs.readdirSync(root, { withFileTypes: true })) {
    const p = path.join(root, entry.name);
    if (entry.isDirectory()) out.push(...walk(p));
    else if (entry.isFile()) out.push(p);
  }
  return out;
}

export async function buildLevelB({ artifactRoot, humanModulePath, humanGitBlobSha1, starsvisibilityMainSha }) {
  if (humanGitBlobSha1 !== EXPECTED_HUMAN_BLOB) refuse('human-threshold Git blob binding drift');
  if (starsvisibilityMainSha !== EXPECTED_STARSVISIBILITY_MAIN) refuse('starsvisibility main binding drift');
  const human = await import(pathToFileURL(path.resolve(humanModulePath)).href);
  if (typeof human.limitingVMagnitude !== 'function') refuse('bound human threshold module lacks limitingVMagnitude');
  const files = walk(artifactRoot).filter(p => path.basename(p) === 'case-result.json').sort();
  if (files.length !== 360) refuse(`expected exactly 360 case-result.json files, got ${files.length}`);
  const rows = files.map(p => JSON.parse(fs.readFileSync(p, 'utf8')));
  if (new Set(rows.map(r => r.caseId)).size !== 360) refuse('duplicate caseId in Level-B universe');
  if (rows.some(r => r.stageId !== 'aerosol-optical-property-sensitivity-v1' || r.status !== 'COMPLETED')) refuse('Level-B universe includes non-completed AOPS result');
  const byCell = new Map();
  for (const row of rows) {
    if (!byCell.has(row.analysisCellId)) byCell.set(row.analysisCellId, []);
    byCell.get(row.analysisCellId).push(row);
  }
  if (byCell.size !== 24) refuse(`expected 24 analysis cells, got ${byCell.size}`);
  const cells = [];
  for (const cellId of [...byCell.keys()].sort()) {
    const cellRows = byCell.get(cellId);
    if (cellRows.length !== 15) refuse(`${cellId}: expected 15 cases`);
    const replicateResults = [];
    for (const rep of [1,2,3]) {
      const repRows = cellRows.filter(r => Number(r.replicate) === rep);
      if (repRows.length !== 5) refuse(`${cellId}: replicate ${rep} not five states`);
      if (new Set(repRows.map(r => r.seed)).size !== 1) refuse(`${cellId}: replicate ${rep} CRN seed drift`);
      const states = new Set(repRows.map(r => r.stateId));
      if (states.size !== EXPECTED_STATES.size || [...EXPECTED_STATES].some(s => !states.has(s))) refuse(`${cellId}: replicate ${rep} state universe drift`);
      const records = Object.fromEntries(repRows.map(r => [r.stateId, { photopicLuminanceCdM2: r.channels?.photopicLuminanceCdM2 }]));
      replicateResults.push(replicateLevelBContrasts(records, human.limitingVMagnitude));
    }
    const sample = cellRows[0];
    cells.push({
      analysisCellId: cellId,
      sunDepressionDeg: sample.sunDepressionDeg,
      geometryId: sample.geometryId,
      geometryTag: sample.geometryTag,
      targetAltitudeDeg: sample.targetAltitudeDeg,
      relativeAzimuthDeg: sample.relativeAzimuthDeg,
      aod550: sample.aod550,
      summary: summarizeLevelBThreeReplicates(replicateResults),
    });
  }
  return {
    schemaVersion: 1,
    stageId: 'aerosol-optical-property-sensitivity-v1-level-b',
    status: 'COMPLETED_PREREGISTERED_AOPS_V1_LEVEL_B',
    caseCount: 360,
    analysisCellCount: 24,
    statesPerGroup: 5,
    replicateCountPerCell: 3,
    contrastCountPerCell: 9,
    starsvisibilityMainSha: EXPECTED_STARSVISIBILITY_MAIN,
    humanThresholdGitBlobSha1: EXPECTED_HUMAN_BLOB,
    humanModel: 'Crumey 2014 eq.34 full branch',
    fieldFactor: 2.4,
    pValuesPermitted: false,
    confidenceIntervalsPermitted: false,
    epsilonSubstitutionPermitted: false,
    universalSunDepressionToMinutesConversionPermitted: false,
    cells,
  };
}

async function main() {
  const [artifactRoot, humanModulePath, output] = process.argv.slice(2);
  if (!artifactRoot || !humanModulePath || !output) refuse('usage: node level_b_driver.mjs <artifact-root> <human-module> <output>');
  const value = await buildLevelB({ artifactRoot, humanModulePath, humanGitBlobSha1: EXPECTED_HUMAN_BLOB, starsvisibilityMainSha: EXPECTED_STARSVISIBILITY_MAIN });
  fs.writeFileSync(output, JSON.stringify(value, null, 2) + '\n');
}

if (import.meta.url === pathToFileURL(path.resolve(process.argv[1] ?? '')).href) {
  main().catch(err => { console.error(err); process.exit(2); });
}
