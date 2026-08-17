import { readFileSync, unlinkSync, writeFileSync } from 'node:fs';

const baseUrl = new URL('./level_b_0079_browser_qa_base.mjs', import.meta.url);
const runtimeUrl = new URL('./.level_b_0079_browser_qa_runtime.mjs', import.meta.url);
const source = readFileSync(baseUrl, 'utf8');
const oldSelector = "document.querySelector('#comparisonView')";
const exactSelector = "document.querySelector('#threeStarComparisonView')";
const occurrenceCount = source.split(oldSelector).length - 1;
if (occurrenceCount !== 1) {
  throw new Error(`Expected exactly one stale comparison-view selector, found ${occurrenceCount}`);
}
if (source.includes(exactSelector)) {
  throw new Error('Base QA unexpectedly already contains the corrected comparison selector');
}
const patched = source.replace(oldSelector, exactSelector);
writeFileSync(runtimeUrl, patched);
try {
  await import(`${runtimeUrl.href}?selector-fix-v1`);
} finally {
  try { unlinkSync(runtimeUrl); } catch (_) {}
}
