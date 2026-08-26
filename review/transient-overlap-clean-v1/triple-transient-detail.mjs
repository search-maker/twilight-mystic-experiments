import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const CASES = {
  'tishrei-transient-overlap': {
    civilDate: '2025-09-23',
    sunsetMs: 1758641660932,
    equilibriumEventTimeMs: 1758642904994.5,
    keys: ['HR 6134', 'HR 6556', 'HR 7796'],
  },
  'tammuz-transient-overlap': {
    civilDate: '2026-06-16',
    sunsetMs: 1781628380546,
    equilibriumEventTimeMs: 1781629701483.5,
    keys: ['HR 5191', 'HR 4905', 'HR 3982'],
  },
};
const label = process.env.CASE_LABEL;
const frozen = CASES[label];
if (!frozen) throw new Error(`unknown CASE_LABEL ${label}`);
const spec = Object.freeze({
  label,
  ...frozen,
  latitudeDeg: 31.778,
  longitudeDeg: 35.235,
  observerElevationM: 800,
  timeZone: 'Asia/Jerusalem',
  engineMode: 'level-b-v3-crumey-blackwell-transient-experimental',
});

const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage();
  const browserConsole = [];
  page.on('console', m => browserConsole.push(`[${m.type()}] ${m.text()}`));
  page.on('pageerror', e => browserConsole.push(`[pageerror] ${e.stack || e.message}`));
  await page.goto('http://127.0.0.1:4173/work-in-progress/', { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForSelector('#visibilityEngineMode', { timeout: 120000 });

  const audit = await page.evaluate(async spec => {
    const catalog = globalThis.__STARS_BUILT_IN_STARS__;
    if (!Array.isArray(catalog) || catalog.length !== 9090) throw new Error(`catalog count ${catalog?.length}`);
    const catalogId = row => {
      if (row?.hip != null && row.hip !== '') return `HIP ${row.hip}`;
      if (row?.hr != null && row.hr !== '') return `HR ${row.hr}`;
      if (row?.hd != null && row.hd !== '') return `HD ${row.hd}`;
      return row?.name ?? row?.id ?? 'target';
    };
    const byKey = new Map(catalog.map(row => [catalogId(row), row]));
    const rows = spec.keys.map(key => {
      const row = byKey.get(key);
      if (!row) throw new Error(`missing ${key}`);
      return { ...row };
    });
    const hooks = eval('__levelBSitewideGeometryHooks')({
      latitudeDeg: spec.latitudeDeg,
      longitudeDeg: spec.longitudeDeg,
      observerElevationM: spec.observerElevationM,
      date: spec.civilDate,
      timeZone: spec.timeZone,
    }, spec.sunsetMs);
    const engine = await import('/scientific-tools/visibility-v3/level-b-sitewide-engine.mjs');
    const evaluation = await engine.evaluateSitewideRows({
      rows,
      latitudeDeg: spec.latitudeDeg,
      longitudeDeg: spec.longitudeDeg,
      observerElevationM: spec.observerElevationM,
      sunsetMs: spec.sunsetMs,
      sunDepressionAtSunsetDeg: hooks.sunDepressionAtSunsetDeg,
      geometryAtSunDepression: hooks.geometryAtSunDepression,
      timeAtSunDepression: hooks.timeAtSunDepression,
      engineMode: spec.engineMode,
      fetchImpl: globalThis.fetch,
    });
    if (evaluation.status !== 'COMPLETE') throw new Error(`evaluation ${evaluation.status}`);
    const detailed = evaluation.results.map(entry => ({
      key: catalogId(entry.row),
      name: entry.row?.name ?? null,
      status: entry.result?.status ?? null,
      reason: entry.result?.reason ?? null,
      detail: entry.result?.detail ?? null,
      firstVisibleTimeMs: entry.result?.firstVisibleTimeMs ?? null,
      minutesAfterSunset: entry.result?.minutesAfterSunset ?? null,
      sunDepressionDeg: entry.result?.sunDepressionDeg ?? null,
      transientAdaptationPenaltyMag: entry.result?.transientAdaptationPenaltyMag ?? null,
      transientTauSeconds: entry.result?.transientTauSeconds ?? null,
      transientAdaptationValidationTier: entry.result?.transientAdaptationValidationTier ?? null,
      transientAdaptationHistoryStartMs: entry.result?.transientAdaptationHistoryStartMs ?? null,
      transientAdaptationHistoryStartSunDepressionDeg: entry.result?.transientAdaptationHistoryStartSunDepressionDeg ?? null,
      transientAdaptationPrehistoryProvenance: entry.result?.transientAdaptationPrehistoryProvenance ?? null,
      transientSupportAudit: entry.result?.transientSupportAudit ?? null,
      timeline: entry.result?.timeline ?? null,
      intervalsMs: entry.intervalsMs,
    }));
    const reasonCounts = {};
    for (const row of detailed) reasonCounts[row.reason ?? 'NULL'] = (reasonCounts[row.reason ?? 'NULL'] ?? 0) + 1;
    return {
      applicationSunsetSunDepressionDeg: Number(hooks.sunDepressionAtSunsetDeg),
      atmosphereResolution: evaluation.atmosphereResolution,
      detailed,
      reasonCounts,
    };
  }, spec);

  const oldErrors = audit.detailed.filter(row => row.reason === 'TRANSIENT_SUNSET_PREHISTORY_REJECTED' || String(row.reason).includes('SUNSET_PREHISTORY'));
  if (oldErrors.length) throw new Error(`old prehistory rejection remains: ${JSON.stringify(oldErrors)}`);
  if (!(audit.applicationSunsetSunDepressionDeg > 0.82 && audit.applicationSunsetSunDepressionDeg < 0.85)) throw new Error(`unexpected sunset depth ${audit.applicationSunsetSunDepressionDeg}`);
  for (const row of audit.detailed) {
    const prov = row.transientAdaptationPrehistoryProvenance;
    if (prov) {
      if (Math.abs(prov.applicationSunsetSunDepressionDeg - audit.applicationSunsetSunDepressionDeg) > 1e-9) throw new Error(`${row.key} provenance sunset depth mismatch`);
      if (prov.levelBSkyEvaluatedBelowSupport !== false || prov.mysticV3ExtrapolatedBelowSupport !== false) throw new Error(`${row.key} below-support boundary violated`);
    }
  }

  const outDir = path.join(process.env.RUNNER_TEMP, 'transient-triple-detail');
  fs.mkdirSync(outDir, { recursive: true });
  fs.writeFileSync(path.join(outDir, `${label}.json`), JSON.stringify({
    schemaVersion: 1,
    status: 'PR111_THREE_STAR_TRANSIENT_DETAIL_PASS',
    applicationSha: process.env.APPLICATION_SHA,
    spec,
    audit,
    claimBoundary: { diagnosticOnly: true, rawCatalogIdentityNotBindingForTammuz: true, noTuning: true, F314Unchanged: true, tauUnchanged: true, noMYSTIC: true },
    browserConsole,
  }, null, 2) + '\n');
  console.log('TRANSIENT_TRIPLE_DETAIL=' + JSON.stringify({ label, sunsetDepressionDeg: audit.applicationSunsetSunDepressionDeg, reasonCounts: audit.reasonCounts, detailed: audit.detailed }));
} finally {
  await browser.close();
}
