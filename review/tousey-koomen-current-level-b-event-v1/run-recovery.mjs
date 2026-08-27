import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const sourcePath = resolve('review/tousey-koomen-current-level-b-event-v1/run.mjs');
let source = await readFile(sourcePath, 'utf8');

const oldTarget = `function targetFrom(star, raw) {
  const bv = finite(raw.bv, \`\${star.object} B-V\`);
  const spectralType = String(raw.spectralType ?? '').trim();
  if (!spectralType) throw new Error(\`\${star.object}: spectralType missing\`);
  const mag = finite(star.catalogMagnitudeV, \`\${star.object} V\`);
  return Object.freeze({
    name: star.object,
    catalogId: \`HR \${HR_BY_OBJECT[star.object]}\`,
    magOriginal: mag,
    magUsed: mag,
    magSource: 'Tousey-Koomen Table III catalog V',
    catalogSource: 'Tousey-Koomen Table III V with current BSC color/type only',
    bv,
    spectralType,
  });
}`;

const newTarget = `function targetFrom(star, raw) {
  const bv = finite(raw.bv, \`\${star.object} B-V\`);
  const spectralType = String(raw.spectralType ?? '').trim();
  if (!spectralType) throw new Error(\`\${star.object}: spectralType missing\`);
  const magnitudeKeys = ['mag', 'vmag', 'vMag', 'magnitude', 'catalogMagnitudeV'];
  const magnitudeKey = magnitudeKeys.find(key => Number.isFinite(Number(raw[key])));
  if (!magnitudeKey) throw new Error(\`\${star.object}: current catalog V key unresolved\`);
  const mag = finite(raw[magnitudeKey], \`\${star.object} current catalog V\`);
  return Object.freeze({
    name: star.object,
    catalogId: \`HR \${HR_BY_OBJECT[star.object]}\`,
    magOriginal: mag,
    magUsed: mag,
    magSource: 'Johnson V',
    catalogSource: 'BSC5/Yale Bright Star processed local catalog',
    bv,
    spectralType,
    __diagnosticMagnitudeKey: magnitudeKey,
  });
}`;

if (!source.includes(oldTarget)) throw new Error('targetFrom patch target not found');
source = source.replace(oldTarget, newTarget);

const oldOutput = `    sourceCatalogMagnitudeV: star.catalogMagnitudeV,
    currentCatalogColorAndType: { bv: target.bv, spectralType: target.spectralType },`;
const newOutput = `    sourceCatalogMagnitudeV: star.catalogMagnitudeV,
    currentRuntimeCatalogMagnitudeV: target.magOriginal,
    currentRuntimeMagnitudeKey: target.__diagnosticMagnitudeKey,
    sourceMinusCurrentCatalogMagnitudeV: star.catalogMagnitudeV - target.magOriginal,
    currentCatalogColorAndType: { bv: target.bv, spectralType: target.spectralType },`;
if (!source.includes(oldOutput)) throw new Error('output patch target not found');
source = source.replace(oldOutput, newOutput);

const oldBoundary = `    sourcePaperSeaLevelPlusOneMagCorrectionNotUsed: true,
    currentPhysicalStellarTransportUsedInstead: true,`;
const newBoundary = `    sourcePaperSeaLevelPlusOneMagCorrectionNotUsed: true,
    sourceTableCatalogMagnitudeUsedAsEvidenceOnly: true,
    currentRuntimeCatalogMagnitudeUsedForModelEvaluation: true,
    currentPhysicalStellarTransportUsedInstead: true,`;
if (!source.includes(oldBoundary)) throw new Error('boundary patch target not found');
source = source.replace(oldBoundary, newBoundary);

const patchedPath = resolve('review/tousey-koomen-current-level-b-event-v1/.run-recovery-patched.mjs');
await writeFile(patchedPath, source, 'utf8');
await import(pathToFileURL(patchedPath).href);
