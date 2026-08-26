#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

function arg(name) {
  const i = process.argv.indexOf(name);
  if (i < 0 || i + 1 >= process.argv.length) throw new Error(`missing ${name}`);
  return process.argv[i + 1];
}

const comparisonPath = arg('--comparison');
const evidencePath = arg('--evidence');
const humanThresholdPath = arg('--human-threshold');
const outputPath = arg('--output');
const comparison = JSON.parse(fs.readFileSync(comparisonPath, 'utf8'));
const evidence = JSON.parse(fs.readFileSync(evidencePath, 'utf8'));
const human = await import(pathToFileURL(path.resolve(humanThresholdPath)).href);
const evidenceById = new Map(evidence.stars.map(s => [s.catalogId, s]));

const perGeometry = comparison.perGeometry.map(row => {
  const frozen = evidenceById.get(row.catalogId);
  if (!frozen) throw new Error(`missing evidence ${row.catalogId}`);
  const backgroundLuminanceCdM2 = Number(row.directALIS.meanChannels.photopicLuminanceCdM2);
  const apparentVMagAtEye = Number(frozen.stellar.apparentVMagAtEye);
  if (!(backgroundLuminanceCdM2 > 0) || !Number.isFinite(apparentVMagAtEye)) throw new Error(`invalid input ${row.catalogId}`);
  const direct = human.evaluatePointSourceVisibility({
    backgroundLuminanceCdM2,
    starTopOfAtmosphereVMag: apparentVMagAtEye,
    extinctionMagV: 0,
    colorSignalOffsetMag: 0,
    fieldFactor: 3.14,
    branch: 'full',
  });
  const frozenLimiting = Number(frozen.visibility.limitingVMagnitude);
  const frozenMargin = Number(frozen.visibility.visibilityMarginMag);
  return {
    catalogId: row.catalogId,
    name: row.name,
    frozenLevelB: {
      backgroundLuminanceCdM2: Number(frozen.skyChannels.photopic.value),
      apparentVMagAtEye,
      limitingVMagnitude: frozenLimiting,
      visibilityMarginMag: frozenMargin,
    },
    directMysticSkyOnly: direct,
    delta: {
      limitingVMagnitude: direct.limitingVMagnitude - frozenLimiting,
      visibilityMarginMag: direct.visibilityMarginMag - frozenMargin,
    },
  };
});

const result = {
  schemaVersion: 1,
  status: 'DIRECT_MYSTIC_SKY_ONLY_VISIBILITY_COMPLETE',
  scientificPurpose: 'jerusalem-tishrei-direct-mystic-v1',
  fieldFactor: 3.14,
  branch: 'full',
  stellarTreatment: 'frozen Level-B apparent V held fixed; direct MYSTIC changes sky photopic luminance only',
  perGeometry,
  claimBoundary: {
    computationalDiagnosticOnly: true,
    noStellarExtinctionSubstitution: true,
    noFieldFactorChange: true,
    noParameterTuning: true,
    transientAdaptationApplied: false,
    productionAuthorized: false,
    humanFirstSeeingValidated: false,
  },
};
fs.mkdirSync(path.dirname(outputPath), { recursive: true });
fs.writeFileSync(outputPath, JSON.stringify(result, null, 2) + '\n');
console.log(JSON.stringify({status: result.status, fieldFactor: result.fieldFactor, perGeometry: result.perGeometry.map(x => ({catalogId:x.catalogId, delta:x.delta, visible:x.directMysticSkyOnly.visible}))}));
