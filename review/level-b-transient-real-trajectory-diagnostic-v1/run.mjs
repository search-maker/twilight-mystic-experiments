import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const APPLICATION_SHA = 'e0da52eb0a2d5bac333da6572f51df52ea7e676e';
const EXPECTED_ROWS = 7653;
const TAUS = [20, 30, 45, 60];
const STEP_DEG = 0.10;
const NEGATIVE_INTERVAL = [0.021567318651181808, 0.04705255275868123];
const NIGHT_SPECS = [
  { id: 'jerusalem-tishrei-2025-09-23', latitudeDeg: 31.778, longitudeDeg: 35.235, observerElevationM: 800, date: '2025-09-23', timeZone: 'Asia/Jerusalem', sunsetMs: 1758641660932, priorProjectAod550Reference: 0.22 },
  { id: 'jerusalem-tammuz-2026-06-16', latitudeDeg: 31.778, longitudeDeg: 35.235, observerElevationM: 800, date: '2026-06-16', timeZone: 'Asia/Jerusalem', sunsetMs: 1781628380546, priorProjectAod550Reference: 0.18 },
];

const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage();
  await page.goto('http://127.0.0.1:4173/work-in-progress/', { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForSelector('#visibilityEngineMode', { timeout: 120000 });
  const result = await page.evaluate(async ({ applicationSha, expectedRows, taus, stepDeg, negativeInterval, nights }) => {
    const q = (values, p) => {
      if (!values.length) return null;
      const sorted = [...values].sort((a, b) => a - b);
      const x = (sorted.length - 1) * p;
      const lo = Math.floor(x), hi = Math.ceil(x);
      return sorted[lo] + (sorted[hi] - sorted[lo]) * (x - lo);
    };
    const summary = values => {
      const v = values.filter(Number.isFinite);
      if (!v.length) return { count: 0, min: null, p10: null, p50: null, p90: null, p99: null, max: null, mean: null };
      return {
        count: v.length,
        min: Math.min(...v),
        p10: q(v, 0.10), p50: q(v, 0.50), p90: q(v, 0.90), p99: q(v, 0.99),
        max: Math.max(...v), mean: v.reduce((a, b) => a + b, 0) / v.length,
      };
    };
    const set = (id, value) => {
      const e = document.getElementById(id);
      if (!e) throw new Error(`missing input ${id}`);
      e.value = String(value);
      e.dispatchEvent(new Event('input', { bubbles: true }));
      e.dispatchEvent(new Event('change', { bubbles: true }));
    };
    const inNeg = B => Number.isFinite(B) && B >= negativeInterval[0] && B <= negativeInterval[1];
    const upsertWitness = (list, row, limit = 40) => {
      list.push(row);
      list.sort((a, b) => a.rawPenaltyMag - b.rawPenaltyMag || a.hr - b.hr || a.sunDepressionDeg - b.sunDepressionDeg);
      if (list.length > limit) list.length = limit;
    };

    const adapter = await import('/scientific-tools/visibility-v3/level-b-current-main-adapter.mjs');
    const resolver = await import('/scientific-tools/visibility-v3/level-b-preview-atmosphere-resolver.mjs');
    const engine = await import('/scientific-tools/visibility-v3/level-b-sitewide-engine.mjs');
    const transientSupport = await import('/scientific-tools/visibility-v3/level-b-transient-contiguous-support.mjs');
    const prehistory = await import('/scientific-tools/visibility-v3/sunset-adaptation-prehistory.mjs');
    const adaptation = await import('/scientific-tools/visibility-v3/transient-adaptation.mjs');
    const human = await import('/scientific-tools/visibility-v3/human-threshold.mjs');
    const runtimeData = await adapter.loadValidatedV3RuntimeData({ fetchImpl: globalThis.fetch });
    let zenithExtensionRuntimeData = null;
    try { zenithExtensionRuntimeData = await adapter.loadValidatedV3ZenithExtensionRuntimeData({ fetchImpl: globalThis.fetch }); } catch {}
    const partition = transientSupport.__TRANSIENT_CONTIGUOUS_SUPPORT_TEST_API__.partitionChronologicalSupportRows;

    const reports = [];
    for (const spec of nights) {
      localStorage.clear();
      set('calculatorFeature', 'three-star'); set('lat', spec.latitudeDeg); set('lon', spec.longitudeDeg);
      set('date', spec.date); set('timezone', spec.timeZone); set('observerElevationM', spec.observerElevationM);
      set('visibilityEngineMode', 'level-b-v3-crumey-blackwell-equilibrium'); set('threeStarCount', 3);
      set('threeStarMagnitudeBasis', 'effective'); set('threeStarMagnitudeThreshold', 1.7);
      globalThis.__STAR_VISIBILITY_ENGINE_MODE__ = 'level-b-v3-crumey-blackwell-equilibrium';
      globalThis.__SKY_MAP_REQUEST__ = false;
      if (typeof eval('ensureBuiltInCatalogReady') === 'function') await eval('ensureBuiltInCatalogReady()');
      const hooks = eval('__levelBSitewideGeometryHooks')({ latitudeDeg: spec.latitudeDeg, longitudeDeg: spec.longitudeDeg, observerElevationM: spec.observerElevationM, date: spec.date, timeZone: spec.timeZone }, spec.sunsetMs);
      delete globalThis.__DIAG_LEVEL_B_DIRECT_CATALOG_ROWS__;
      await eval('__levelBSitewideRunUsingLegacyScaffold(globalThis.__STAR_VISIBILITY_ENGINE_MODE__)');
      const rows = globalThis.__DIAG_LEVEL_B_DIRECT_CATALOG_ROWS__;
      if (!Array.isArray(rows) || rows.length !== expectedRows) throw new Error(`${spec.id}: transformed rows ${rows?.length}`);
      const atmosphereResolution = await resolver.resolvePreviewLevelBAtmosphere({
        latitudeDeg: spec.latitudeDeg, longitudeDeg: spec.longitudeDeg, observerElevationM: spec.observerElevationM,
        validTimeMs: hooks.timeAtSunDepression(6), fetchImpl: globalThis.fetch,
      });
      if (atmosphereResolution.status !== 'RESOLVED') throw new Error(`${spec.id}: atmosphere ${atmosphereResolution.status}`);
      const point = engine.createSitewidePointEvaluator({ runtimeData, zenithExtensionRuntimeData, atmosphereResolution, geometryAtSunDepression: hooks.geometryAtSunDepression });
      const sunsetDep = -Number(eval('sunAltitude')(spec.sunsetMs, spec.latitudeDeg, spec.longitudeDeg));
      if (!Number.isFinite(sunsetDep) || sunsetDep < 0 || sunsetDep >= 2) throw new Error(`${spec.id}: sunset depression ${sunsetDep}`);

      const byTau = Object.fromEntries(taus.map(tau => [tau, {
        tauSeconds: tau, targetCount: 0, prehistoryRejectedTargetCount: 0, prehistoryRejectionReasons: {}, stateCount: 0, rawNegativePenaltyStateCount: 0,
        targetWithNegativePenaltyCount: 0, physicalInNegativeIntervalStateCount: 0,
        effectiveInNegativeIntervalStateCount: 0, eitherInNegativeIntervalStateCount: 0,
        intervalEntryOrExitTransitionCount: 0, maxDebtFractionsByTarget: [], minRawPenaltyByTarget: [],
        maxDebtCdM2ByTarget: [], usableEndDepressionByTarget: [], witnesses: [],
        global: { physicalMin: Infinity, physicalMax: -Infinity, debtMin: Infinity, debtMax: -Infinity, effectiveMin: Infinity, effectiveMax: -Infinity, rawPenaltyMin: Infinity, rawPenaltyMax: -Infinity },
      }]));
      let normalizedTargetCount = 0, insufficientSupportTargetCount = 0, unsupportedAtStartTargetCount = 0;

      const steps = Math.ceil((10.5 - 2.0) / stepDeg);
      for (let rowIndex = 0; rowIndex < rows.length; rowIndex += 1) {
        const row = rows[rowIndex];
        const target = engine.normalizeSitewideTarget(row);
        if (!target) continue;
        normalizedTargetCount += 1;
        const sampled = [];
        for (let i = 0; i <= steps; i += 1) {
          const dep = i === steps ? 10.5 : 2.0 + i * (8.5 / steps);
          const timestampMs = Number(hooks.timeAtSunDepression(dep));
          const sample = point(target, dep);
          const supported = sample.status === 'SUPPORTED' && sample.sky?.channels?.photopic?.available === true;
          sampled.push({ depression: dep, timestampMs, sample, sky: sample.sky ?? null, supported });
        }
        const segments = partition(sampled);
        const initial = segments[0] ?? null;
        if (!initial || Math.abs(Number(initial[0]?.depression) - 2.0) > 1e-12) { unsupportedAtStartTargetCount += 1; continue; }
        if (initial.length < 2) { insufficientSupportTargetCount += 1; continue; }
        const history = initial.map(s => ({
          timestampMs: s.timestampMs,
          adaptationFieldLuminanceCdM2: s.sky.channels.photopic.value,
          detectionBackgroundLuminanceCdM2: s.sky.channels.photopic.value,
          photopicLuminanceCdM2: s.sky.channels.photopic.value,
          scotopicLuminanceCdM2: s.sky.channels?.scotopic?.available ? s.sky.channels.scotopic.value : undefined,
          johnsonVEffectiveRadiance: s.sky.channels?.johnsonV?.available ? s.sky.channels.johnsonV.value : undefined,
          sunDepressionDeg: s.depression,
        }));
        for (const tau of taus) {
          const bucket = byTau[tau];
          let build;
          try {
            build = prehistory.buildContinuousSunsetAdaptationTimeline({
              levelBHistory: history, sunsetMs: spec.sunsetMs, sunDepressionAtSunsetDeg: sunsetDep,
              timeAtSunDepression: hooks.timeAtSunDepression, tauSeconds: tau, prehistoryStepDeg: 0.1,
            });
          } catch (error) {
            bucket.prehistoryRejectedTargetCount += 1;
            const reason = String(error?.code ?? error?.message ?? error ?? 'UNKNOWN');
            bucket.prehistoryRejectionReasons[reason] = (bucket.prehistoryRejectionReasons[reason] ?? 0) + 1;
            continue;
          }
          bucket.targetCount += 1;
          bucket.usableEndDepressionByTarget.push(initial.at(-1).depression);
          let targetMinPenalty = Infinity, targetMaxDebt = 0, targetMaxDebtFraction = 0, targetNegative = false;
          let prevPhysFlag = null, prevEffFlag = null;
          for (const s of initial) {
            const queried = adaptation.sampleTransientAdaptationAtTimestamp(build.timeline, s.timestampMs);
            const physicalB = Number(s.sky.channels.photopic.value);
            const debt = Number(queried.equivalentAdaptationDebtCdM2);
            const effectiveB = physicalB + debt;
            const eqLim = human.limitingVMagnitude({ backgroundLuminanceCdM2: physicalB, fieldFactor: 3.14, branch: 'full' });
            const effLim = human.limitingVMagnitude({ backgroundLuminanceCdM2: effectiveB, fieldFactor: 3.14, branch: 'full' });
            const rawPenaltyMag = eqLim - effLim;
            const debtFraction = debt / physicalB;
            const physFlag = inNeg(physicalB), effFlag = inNeg(effectiveB);
            bucket.stateCount += 1;
            if (rawPenaltyMag < -1e-12) { bucket.rawNegativePenaltyStateCount += 1; targetNegative = true; }
            if (physFlag) bucket.physicalInNegativeIntervalStateCount += 1;
            if (effFlag) bucket.effectiveInNegativeIntervalStateCount += 1;
            if (physFlag || effFlag) bucket.eitherInNegativeIntervalStateCount += 1;
            if (prevPhysFlag !== null && (prevPhysFlag !== physFlag || prevEffFlag !== effFlag)) bucket.intervalEntryOrExitTransitionCount += 1;
            prevPhysFlag = physFlag; prevEffFlag = effFlag;
            targetMinPenalty = Math.min(targetMinPenalty, rawPenaltyMag);
            targetMaxDebt = Math.max(targetMaxDebt, debt);
            targetMaxDebtFraction = Math.max(targetMaxDebtFraction, debtFraction);
            const g = bucket.global;
            g.physicalMin = Math.min(g.physicalMin, physicalB); g.physicalMax = Math.max(g.physicalMax, physicalB);
            g.debtMin = Math.min(g.debtMin, debt); g.debtMax = Math.max(g.debtMax, debt);
            g.effectiveMin = Math.min(g.effectiveMin, effectiveB); g.effectiveMax = Math.max(g.effectiveMax, effectiveB);
            g.rawPenaltyMin = Math.min(g.rawPenaltyMin, rawPenaltyMag); g.rawPenaltyMax = Math.max(g.rawPenaltyMax, rawPenaltyMag);
            if (rawPenaltyMag < 0 || physFlag || effFlag) upsertWitness(bucket.witnesses, {
              rowIndex, hr: Number(row.hr ?? -1), name: row.name ?? row.properName ?? row.bayer ?? null,
              tauSeconds: tau, sunDepressionDeg: s.depression, physicalB, debtCdM2: debt, debtFraction,
              effectiveB, physicalInNegativeInterval: physFlag, effectiveInNegativeInterval: effFlag,
              rawPenaltyMag,
            });
          }
          if (targetNegative) bucket.targetWithNegativePenaltyCount += 1;
          bucket.minRawPenaltyByTarget.push(targetMinPenalty);
          bucket.maxDebtCdM2ByTarget.push(targetMaxDebt);
          bucket.maxDebtFractionsByTarget.push(targetMaxDebtFraction);
        }
        if ((rowIndex + 1) % 500 === 0) console.log(`${spec.id}: ${rowIndex + 1}/${rows.length}`);
      }

      const tauReports = {};
      for (const tau of taus) {
        const b = byTau[tau];
        const finiteGlobal = Object.fromEntries(Object.entries(b.global).map(([k, v]) => [k, Number.isFinite(v) ? v : null]));
        tauReports[tau] = {
          tauSeconds: tau, targetCount: b.targetCount, prehistoryRejectedTargetCount: b.prehistoryRejectedTargetCount, prehistoryRejectionReasons: b.prehistoryRejectionReasons, stateCount: b.stateCount,
          rawNegativePenaltyStateCount: b.rawNegativePenaltyStateCount,
          rawNegativePenaltyStateFraction: b.stateCount ? b.rawNegativePenaltyStateCount / b.stateCount : null,
          targetWithNegativePenaltyCount: b.targetWithNegativePenaltyCount,
          targetWithNegativePenaltyFraction: b.targetCount ? b.targetWithNegativePenaltyCount / b.targetCount : null,
          physicalInNegativeIntervalStateCount: b.physicalInNegativeIntervalStateCount,
          effectiveInNegativeIntervalStateCount: b.effectiveInNegativeIntervalStateCount,
          eitherInNegativeIntervalStateCount: b.eitherInNegativeIntervalStateCount,
          intervalEntryOrExitTransitionCount: b.intervalEntryOrExitTransitionCount,
          targetLevelSummaries: {
            minRawPenaltyMag: summary(b.minRawPenaltyByTarget),
            maxDebtCdM2: summary(b.maxDebtCdM2ByTarget),
            maxDebtFractionOfPhysical: summary(b.maxDebtFractionsByTarget),
            usableEndSunDepressionDeg: summary(b.usableEndDepressionByTarget),
          },
          globalRanges: finiteGlobal,
          mostNegativeOrIntervalWitnesses: b.witnesses,
        };
      }
      reports.push({
        nightId: spec.id, site: { latitudeDeg: spec.latitudeDeg, longitudeDeg: spec.longitudeDeg, observerElevationM: spec.observerElevationM, date: spec.date, timeZone: spec.timeZone },
        sunsetMs: spec.sunsetMs, sunDepressionAtSunsetDeg: sunsetDep, transformedRowCount: rows.length,
        normalizedTargetCount, unsupportedAtLevelBStartTargetCount: unsupportedAtStartTargetCount,
        insufficientInitialContiguousSupportTargetCount: insufficientSupportTargetCount,
        atmosphere: { selectedProviderId: atmosphereResolution.selectedProviderId ?? null, aod550: atmosphereResolution.atmosphere.aod550, priorProjectAod550Reference: spec.priorProjectAod550Reference, referenceIsNonBinding: true, identity: atmosphereResolution.atmosphere.identity ?? null, provenance: atmosphereResolution.atmosphere.provenance ?? null },
        tauReports,
      });
    }
    return {
      schemaVersion: 1,
      diagnosticId: 'issue117-level-b-real-transient-trajectories-v1',
      applicationSha, applicationMainExact: true, resultOpening: 'diagnostic-state-only',
      scientificAcceptanceGate: false, experimental: true, observationallyCalibrated: false,
      noMysticSolverExecuted: true, changesTransientMapping: false, changesTransientTau: false,
      changesFieldFactor: false, fieldFactor: 3.14, changesProductionRouting: false, authorizesProduction: false,
      negativeSlopeIntervalBackgroundCdM2: negativeInterval, tauSeconds: taus, scanStepDeg: stepDeg,
      benchmarkSelection: 'existing canonical Jerusalem Tishrei/Tammuz project nights; not selected from observational residuals',
      reports,
    };
  }, { applicationSha: APPLICATION_SHA, expectedRows: EXPECTED_ROWS, taus: TAUS, stepDeg: STEP_DEG, negativeInterval: NEGATIVE_INTERVAL, nights: NIGHT_SPECS });
  const outDir = path.join(process.env.RUNNER_TEMP, 'issue117-level-b-real-trajectories-v1');
  fs.mkdirSync(outDir, { recursive: true });
  fs.writeFileSync(path.join(outDir, 'trajectory-summary.json'), JSON.stringify(result, null, 2) + '\n');
  console.log(JSON.stringify(result.reports.map(n => ({ nightId: n.nightId, rows: n.transformedRowCount, normalizedTargets: n.normalizedTargetCount, tau: Object.fromEntries(Object.entries(n.tauReports).map(([k, v]) => [k, { states: v.stateCount, negativeStates: v.rawNegativePenaltyStateCount, affectedTargets: v.targetWithNegativePenaltyCount, minPenalty: v.globalRanges.rawPenaltyMin, maxDebt: v.globalRanges.debtMax }])) })), null, 2));
} finally {
  await browser.close();
}
