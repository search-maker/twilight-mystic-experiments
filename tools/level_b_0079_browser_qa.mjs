import { readFileSync, unlinkSync, writeFileSync } from 'node:fs';

const baseUrl = new URL('./level_b_0079_browser_qa_base.mjs', import.meta.url);
const runtimeUrl = new URL('./.level_b_0079_browser_qa_runtime.mjs', import.meta.url);
const source = readFileSync(baseUrl, 'utf8');

const replacements = [
  {
    name: 'comparison-view-selector',
    oldText: "document.querySelector('#comparisonView')",
    newText: "document.querySelector('#threeStarComparisonView')",
  },
  {
    name: 'weekly-start-route',
    oldText: "  await page.evaluate(() => { const el = document.querySelector('#weeklyView'); if (el && !el.open) el.querySelector('summary')?.click(); });\n  await waitGlobal(page, 'weeklyResultsFinal === true && Array.isArray(weeklyResults) && weeklyResults.length === 7');",
    newText: "  await page.evaluate(() => { const el = document.querySelector('#weeklyView'); if (el) el.open = true; });\n  await page.waitForSelector('#calculateWeekly', { state: 'visible', timeout: 60000 });\n  assert(await page.isEnabled('#calculateWeekly'), `${engine}/weekly calculate button did not enable`);\n  await page.click('#calculateWeekly');\n  await waitGlobal(page, \"Array.isArray(weeklyResults) && weeklyResults.length === 7 && weeklyResults.every(row => !row?.pending) && document.querySelector('#calculateWeekly') && !document.querySelector('#calculateWeekly').disabled\");",
  },
];

let patched = source;
for (const replacement of replacements) {
  const count = patched.split(replacement.oldText).length - 1;
  if (count !== 1) {
    throw new Error(`Expected exactly one ${replacement.name} anchor, found ${count}`);
  }
  if (patched.includes(replacement.newText)) {
    throw new Error(`Base QA unexpectedly already contains ${replacement.name} fix`);
  }
  patched = patched.replace(replacement.oldText, replacement.newText);
}

writeFileSync(runtimeUrl, patched);
try {
  await import(`${runtimeUrl.href}?runner-fix-v2`);
} finally {
  try { unlinkSync(runtimeUrl); } catch (_) {}
}
