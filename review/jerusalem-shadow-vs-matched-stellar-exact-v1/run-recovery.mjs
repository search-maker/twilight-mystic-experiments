import { writeFile } from 'node:fs/promises';
import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';

const SOURCE_COMMIT = '168f93d579949dd0eede3e944e086d83673011bc';
const SOURCE_PATH = 'review/jerusalem-shadow-vs-matched-stellar-exact-v1/run.mjs';
const sourceUrl = `https://raw.githubusercontent.com/search-maker/twilight-mystic-experiments/${SOURCE_COMMIT}/${SOURCE_PATH}`;
const response = await fetch(sourceUrl);
if (!response.ok) throw new Error(`failed to load exact source harness ${response.status}`);
let source = await response.text();

const oldBlock = "  if (bvCandidates.length !== 1) throw new Error(`could not uniquely infer B-V catalog key: ${bvCandidates.join(',')}`);\n  if (spCandidates.length !== 1) throw new Error(`could not uniquely infer spectral-type catalog key: ${spCandidates.join(',')}`);\n  return Object.freeze({ bvKey: bvCandidates[0], spectralTypeKey: spCandidates[0] });";
const newBlock = "  if (bvCandidates.length !== 1) throw new Error(`could not uniquely infer B-V catalog key: ${bvCandidates.join(',')}`);\n  const spectralTypeKey = spCandidates.includes('spectralType') ? 'spectralType' : (spCandidates.length === 1 ? spCandidates[0] : null);\n  if (!spectralTypeKey) throw new Error(`could not select spectral-type catalog key: ${spCandidates.join(',')}`);\n  return Object.freeze({ bvKey: bvCandidates[0], spectralTypeKey });";
if (!source.includes(oldBlock)) throw new Error('exact harness patch target not found');
source = source.replace(oldBlock, newBlock);

const patchedPath = resolve('review/jerusalem-shadow-vs-matched-stellar-exact-v1/.run-recovery-patched.mjs');
await writeFile(patchedPath, source, 'utf8');
await import(pathToFileURL(patchedPath).href);
