import { chromium } from 'playwright';
import fs from 'node:fs';

const TARGET_URL = process.env.TARGET_URL || 'https://starsvisibility.pages.dev/';
const YEAR = 2026;
const LOCATION = Object.freeze({ name: 'Jerusalem', lat: 31.778, lon: 35.235, timeZone: 'Asia/Jerusalem' });
const MIN_ALT_DEG = 3;
const BRIGHT_THRESHOLD_MAG = 1.5;
const LOOKBACK_MINUTES = 360;

function countOccurrences(source, needle) {
  return source.split(needle).length - 1;
}

function replaceAtLeastOnce(source, needle, replacement, label) {
  const count = countOccurrences(source, needle);
  if (count < 1) throw new Error(`${label}: expected at least one match, found ${count}`);
  return source.split(needle).join(replacement);
}

function patchCalculationSource(source) {
  let patched = source;
  patched = replaceAtLeastOnce(
    patched,
    [
      '        const observerMode = $("observerMode")?.value || "ordinaryOrGuided";',
      '        const threeStarCount = Number($("threeStarCount")?.value || 3);',
      '        const threeStarMagnitudeBasis = $("threeStarMagnitudeBasis")?.value || "catalog";',
      '        const threeStarMagnitudeThreshold = Number($("threeStarMagnitudeThreshold")?.value ?? 3);',
    ].join('\n'),
    [
      '        const observerMode = $("observerMode")?.value || "ordinaryOrGuided";',
      '        const brightObjectMode = $("brightObjectMode")?.value === "1";',
      '        const threeStarCount = brightObjectMode ? 1 : Number($("threeStarCount")?.value || 3);',
      '        const threeStarMagnitudeBasis = brightObjectMode',
      '          ? ($("brightObjectMagnitudeBasis")?.value || "catalog")',
      '          : ($("threeStarMagnitudeBasis")?.value || "catalog");',
      '        const threeStarMagnitudeThreshold = brightObjectMode',
      `          ? Number($("brightObjectMagnitudeThreshold")?.value ?? ${BRIGHT_THRESHOLD_MAG})`,
      '          : Number($("threeStarMagnitudeThreshold")?.value ?? 3);',
    ].join('\n'),
    'bright-object calculation inputs',
  );

  patched = replaceAtLeastOnce(
    patched,
    '        const includePlanets = $("includePlanets") ? $("includePlanets").checked === true : true;',
    '        const includePlanets = brightObjectMode\n          ? ($("brightObjectIncludePlanets") ? $("brightObjectIncludePlanets").checked === true : true)\n          : ($("includePlanets") ? $("includePlanets").checked === true : true);',
    'bright-object planet inclusion',
  );

  patched = replaceAtLeastOnce(
    patched,
    '        if (isThreeStarCalculation && ![2, 3].includes(threeStarCount)) throw new Error("Number of stars must be 2 or 3.");',
    '        if (isThreeStarCalculation && !(brightObjectMode ? threeStarCount === 1 : [2, 3].includes(threeStarCount))) throw new Error(brightObjectMode ? "Bright-object mode requires one object." : "Number of stars must be 2 or 3.");',
    'bright-object count validation',
  );

  patched = replaceAtLeastOnce(
    patched,
    [
      '          const selectionPreFilter = star => {',
      '            if (threeStarMagnitudeBasis === "known-exclusions") {',
      '              return !knownExclusionSet.has(knownObjectExclusionKey(star));',
      '            }',
      '            if (threeStarMagnitudeBasis === "catalog") {',
      '              return star.mag >= threeStarMagnitudeThreshold - 1e-10;',
      '            }',
      '            return true;',
      '          };',
    ].join('\n'),
    [
      '          const selectionPreFilter = star => {',
      '            if (brightObjectMode) {',
      '              if (star.isPlanet) return includePlanets;',
      '              if (threeStarMagnitudeBasis === "catalog") {',
      '                return Number.isFinite(star.mag) && star.mag <= threeStarMagnitudeThreshold + 1e-10;',
      '              }',
      '              return true;',
      '            }',
      '            if (threeStarMagnitudeBasis === "known-exclusions") {',
      '              return !knownExclusionSet.has(knownObjectExclusionKey(star));',
      '            }',
      '            if (threeStarMagnitudeBasis === "catalog") {',
      '              return star.mag >= threeStarMagnitudeThreshold - 1e-10;',
      '            }',
      '            return true;',
      '          };',
    ].join('\n'),
    'bright-object magnitude prefilter direction',
  );

  patched = replaceAtLeastOnce(
    patched,
    [
      '          const exhaustiveThreeStarScan = globalThis.__THREE_STAR_EXHAUSTIVE__ === true;',
      '          const useSafeCandidateReduction = threeStarCandidateReductionSafetyEnabled',
    ].join('\n'),
    [
      '          const exhaustiveThreeStarScan = globalThis.__THREE_STAR_EXHAUSTIVE__ === true;',
      '          const useSafeCandidateReduction = !brightObjectMode && threeStarCandidateReductionSafetyEnabled',
    ].join('\n'),
    'disable ordinary candidate reduction in bright-object mode',
  );

  patched = replaceAtLeastOnce(
    patched,
    [
      '            if (threeStarMagnitudeBasis !== "known-exclusions"',
      '                && (!Number.isFinite(selectionMagnitude) || selectionMagnitude < threeStarMagnitudeThreshold - 1e-10)) return null;',
    ].join('\n'),
    [
      '            if (threeStarMagnitudeBasis !== "known-exclusions") {',
      '              if (!Number.isFinite(selectionMagnitude)) return null;',
      '              if (brightObjectMode) {',
      '                if (selectionMagnitude > threeStarMagnitudeThreshold + 1e-10) return null;',
      '              } else if (selectionMagnitude < threeStarMagnitudeThreshold - 1e-10) return null;',
      '            }',
    ].join('\n'),
    'bright-object magnitude qualifier direction',
  );

  patched = replaceAtLeastOnce(
    patched,
    [
      '        if (isThreeStarCalculation) {',
      '          const sunsetMs = sunsetAtSeaLevel(dateText, timeZone, lat, lon);',
      '          const stabilityMs = 60000;',
    ].join('\n'),
    [
      '        if (isThreeStarCalculation) {',
      '          const sunsetMs = sunsetAtSeaLevel(dateText, timeZone, lat, lon);',
      `          const brightObjectLookbackMinutes = brightObjectMode ? Math.max(0, Math.min(720, Number($("brightObjectLookbackMinutes")?.value || ${LOOKBACK_MINUTES}))) : 0;`,
      '          const threeStarSearchStartMs = brightObjectMode && Number.isFinite(sunsetMs)',
      '            ? Math.max(localNoon, sunsetMs - brightObjectLookbackMinutes * 60000)',
      '            : sunsetMs;',
      '          const stabilityMs = 60000;',
    ].join('\n'),
    'bright-object pre-sunset search start',
  );

  patched = replaceAtLeastOnce(
    patched,
    [
      '          function findEventTimeForCurrentCandidates(skyScenario = "nominal", atmosphereSeriesOverride = atmosphereSeries) {',
      '            if (!Number.isFinite(sunsetMs) || candidateEntries.length < threeStarCount) return null;',
      '            const lastStableStart = scanEnd - stabilityMs;',
      '            if (sunsetMs <= lastStableStart && conditionAt(sunsetMs, skyScenario, atmosphereSeriesOverride)) {',
      '              return sunsetMs;',
      '            }',
      '            let previous = sunsetMs;',
      '            for (let t = sunsetMs + scanStep; t <= lastStableStart; t += scanStep) {',
    ].join('\n'),
    [
      '          function findEventTimeForCurrentCandidates(skyScenario = "nominal", atmosphereSeriesOverride = atmosphereSeries) {',
      '            if (!Number.isFinite(sunsetMs) || !Number.isFinite(threeStarSearchStartMs) || candidateEntries.length < threeStarCount) return null;',
      '            const lastStableStart = scanEnd - stabilityMs;',
      '            if (threeStarSearchStartMs <= lastStableStart && conditionAt(threeStarSearchStartMs, skyScenario, atmosphereSeriesOverride)) {',
      '              return threeStarSearchStartMs;',
      '            }',
      '            let previous = threeStarSearchStartMs;',
      '            for (let t = threeStarSearchStartMs + scanStep; t <= lastStableStart; t += scanStep) {',
    ].join('\n'),
    'bright-object pre-sunset event scan',
  );

  patched = replaceAtLeastOnce(
    patched,
    [
      '              isPlanet: currentObject.isPlanet === true,',
      '              catalogMagnitude: currentObject.mag,',
      '              effectiveMagnitude: ep.magEff,',
    ].join('\n'),
    [
      '              isPlanet: currentObject.isPlanet === true,',
      '              phaseDeg: currentObject.isPlanet && Number.isFinite(currentObject.phaseDeg) ? currentObject.phaseDeg : null,',
      '              heliocentricDistanceAu: currentObject.isPlanet && Number.isFinite(currentObject.helioDistance) ? currentObject.helioDistance : null,',
      '              geocentricDistanceAu: currentObject.isPlanet && Number.isFinite(currentObject.geoDistance) ? currentObject.geoDistance : null,',
      '              solarSeparationDeg: currentObject.isPlanet ? angularSeparation(s.alt, s.az, sm.sun.alt, sm.sun.az) : null,',
      '              planetMagnitudeApproximate: currentObject.isPlanet ? currentObject.magApprox !== false : null,',
      '              catalogMagnitude: currentObject.mag,',
      '              effectiveMagnitude: ep.magEff,',
    ].join('\n'),
    'planet diagnostics at event time',
  );

  patched = replaceAtLeastOnce(
    patched,
    '            minutesAfterSunset: Number.isFinite(eventTime) && Number.isFinite(sunsetMs) ? (eventTime - sunsetMs) / 60000 : null,',
    [
      '            minutesAfterSunset: Number.isFinite(eventTime) && Number.isFinite(sunsetMs) ? (eventTime - sunsetMs) / 60000 : null,',
      '            brightObjectMode,',
      '            brightObjectComparator: brightObjectMode ? "brighter-than-or-equal" : null,',
      '            brightObjectSearchStartTime: brightObjectMode ? threeStarSearchStartMs : null,',
      '            lowerBoundCensored: brightObjectMode && Number.isFinite(eventTime) && eventTime === threeStarSearchStartMs,',
    ].join('\n'),
    'bright-object result metadata',
  );

  return patched;
}

function starCsv(star) {
  const esc = value => {
    const text = String(value ?? '');
    return /[",\n\r]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
  };
  return [
    'name,raHours,decDeg,mag,bv,pmra,pmdec,epoch',
    [star.name, star.ra, star.dec, star.mag, star.bv ?? '', star.pmRA ?? '', star.pmDec ?? '', star.epoch ?? ''].map(esc).join(','),
  ].join('\n');
}

function formatLocal(ms) {
  if (!Number.isFinite(ms)) return null;
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: LOCATION.timeZone,
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23',
  }).format(new Date(ms));
}

async function setBase(page) {
  await page.evaluate(({ year, location, minAlt }) => {
    const setValue = (id, value) => {
      const el = document.getElementById(id);
      if (!el) throw new Error(`Missing #${id}`);
      el.value = String(value);
      el.dispatchEvent(new Event('change', { bubbles: true }));
    };
    setValue('calculatorFeature', 'three-star');
    setValue('lat', location.lat);
    setValue('lon', location.lon);
    setValue('timezone', location.timeZone);
    if (document.getElementById('customLocationName')) setValue('customLocationName', location.name);
    setValue('minAlt', minAlt);
    setValue('stepMin', 2);
    setValue('horizon', 'dark');
    setValue('moonOn', 'on');
    setValue('modelMode', 'physical');
    setValue('observerMode', 'ordinaryOrGuided');
    setValue('variableStarMode', 'catalog');
    setValue('maxMag', 15);
    if (document.getElementById('catalogDepth')) setValue('catalogDepth', 7.5);
    if (document.getElementById('kvMode')) setValue('kvMode', 'auto');
    setValue('annualCalendar', 'gregorian-year');
    setValue('annualYear', year);
    setValue('annualCadence', 'daily');
    if (document.getElementById('annualResultKind')) setValue('annualResultKind', 'regular');
  }, { year: YEAR, location: LOCATION, minAlt: MIN_ALT_DEG });
}

async function installPatchedWorker(page) {
  const source = await page.evaluate(() => globalThis.eval('APP_SCRIPT_SOURCE'));
  const patched = patchCalculationSource(source);
  await page.evaluate(({ patched, threshold, lookback }) => {
    globalThis.__QA_BRIGHT_APP_SCRIPT_SOURCE = patched;
    globalThis.__QA_BRIGHT_THRESHOLD = threshold;
    globalThis.__QA_BRIGHT_LOOKBACK = lookback;
    const state = globalThis.eval(`(() => {
      disposeReusableCalculationWorker();
      if (!globalThis.__QA_ORIGINAL_COLLECT_THREE_STAR_BATCH_VALUES) {
        globalThis.__QA_ORIGINAL_COLLECT_THREE_STAR_BATCH_VALUES = collectThreeStarBatchValues;
      }
      const factorySource = createThreeStarBatchWorker.toString().split('APP_SCRIPT_SOURCE').join('globalThis.__QA_BRIGHT_APP_SCRIPT_SOURCE');
      createThreeStarBatchWorker = eval('(' + factorySource + ')');
      collectThreeStarBatchValues = function qaBrightCollectValues() {
        const values = globalThis.__QA_ORIGINAL_COLLECT_THREE_STAR_BATCH_VALUES();
        values.brightObjectMode = { value: '1', checked: false };
        values.brightObjectMagnitudeBasis = { value: 'catalog', checked: false };
        values.brightObjectMagnitudeThreshold = { value: String(globalThis.__QA_BRIGHT_THRESHOLD), checked: false };
        values.brightObjectLookbackMinutes = { value: String(globalThis.__QA_BRIGHT_LOOKBACK), checked: false };
        values.brightObjectIncludePlanets = { value: 'on', checked: false };
        return values;
      };
      return { factoryPatched: createThreeStarBatchWorker.toString().includes('__QA_BRIGHT_APP_SCRIPT_SOURCE') };
    })()`);
    if (!state.factoryPatched) throw new Error('Could not patch annual worker factory');
  }, { patched, threshold: BRIGHT_THRESHOLD_MAG, lookback: LOOKBACK_MINUTES });
}

async function topTen(page) {
  return page.evaluate(({ lat, minAlt }) => {
    const catalog = document.getElementById('catalog');
    const previous = catalog.value;
    catalog.value = '';
    const stars = parseCatalog().map(star => ({
      name: star.name,
      ra: Number(star.ra), dec: Number(star.dec), mag: Number(star.mag),
      bv: Number.isFinite(Number(star.bv)) ? Number(star.bv) : null,
      pmRA: Number.isFinite(Number(star.pmRA)) ? Number(star.pmRA) : null,
      pmDec: Number.isFinite(Number(star.pmDec)) ? Number(star.pmDec) : null,
      epoch: Number.isFinite(Number(star.epoch)) ? Number(star.epoch) : null,
    }));
    catalog.value = previous;
    return stars
      .filter(star => Number.isFinite(star.ra) && Number.isFinite(star.dec) && Number.isFinite(star.mag))
      .filter(star => 90 - Math.abs(lat - star.dec) >= minAlt)
      .sort((a, b) => a.mag - b.mag || a.name.localeCompare(b.name))
      .slice(0, 10);
  }, { lat: LOCATION.lat, minAlt: MIN_ALT_DEG });
}

async function runAnnual(page, csv, includePlanets) {
  await page.evaluate(({ csv, includePlanets }) => {
    const catalog = document.getElementById('catalog');
    catalog.value = csv;
    catalog.dispatchEvent(new Event('change', { bubbles: true }));
    globalThis.__QA_BRIGHT_INCLUDE_PLANETS = Boolean(includePlanets);
    const original = globalThis.__QA_ORIGINAL_COLLECT_THREE_STAR_BATCH_VALUES;
    collectThreeStarBatchValues = function qaBrightCollectValues() {
      const values = original();
      values.brightObjectMode = { value: '1', checked: false };
      values.brightObjectMagnitudeBasis = { value: 'catalog', checked: false };
      values.brightObjectMagnitudeThreshold = { value: String(globalThis.__QA_BRIGHT_THRESHOLD), checked: false };
      values.brightObjectLookbackMinutes = { value: String(globalThis.__QA_BRIGHT_LOOKBACK), checked: false };
      values.brightObjectIncludePlanets = { value: 'on', checked: globalThis.__QA_BRIGHT_INCLUDE_PLANETS };
      return values;
    };
    clearAnnualBatchResults();
    calculateAnnualResults();
  }, { csv, includePlanets });

  await page.waitForFunction(() => {
    try {
      return globalThis.eval('activeAnnualWorker === null && annualResultsFinal === true && Array.isArray(annualResults) && annualResults.length >= 365 && annualResults.every(row => row && row.pending !== true && row.provisional !== true)');
    } catch { return false; }
  }, null, { timeout: 900_000, polling: 500 });

  return page.evaluate(() => globalThis.eval(`annualResults.map(row => {
    const objects = Array.isArray(row?.stars) ? row.stars : [];
    const object = objects.find(item => item?.completing) || objects[0] || null;
    return {
      date: row?.date || null,
      found: row?.found === true,
      eventTimeMs: Number(row?.time),
      sunsetTimeMs: Number(row?.sunsetTime),
      offsetMinutes: Number(row?.minutesAfterSunset),
      sunAltitudeDeg: Number(row?.sunAltitude),
      lowerBoundCensored: row?.lowerBoundCensored === true,
      object: object ? {
        name: object.name || null,
        isPlanet: object.isPlanet === true,
        catalogMagnitude: Number(object.catalogMagnitude),
        effectiveMagnitude: Number(object.effectiveMagnitude),
        apparentAltitudeDeg: Number(object.apparentAltitude),
        trueAltitudeDeg: Number(object.trueAltitude),
        azimuthDeg: Number(object.azimuth),
        visibilityMarginMag: Number(object.visibilityMargin),
        phaseDeg: Number(object.phaseDeg),
        solarSeparationDeg: Number(object.solarSeparationDeg),
        heliocentricDistanceAu: Number(object.heliocentricDistanceAu),
        geocentricDistanceAu: Number(object.geocentricDistanceAu),
        planetMagnitudeApproximate: object.planetMagnitudeApproximate === true,
      } : null,
    };
  })`));
}

function best(rows, limit = 1) {
  return rows.filter(row => row.found && Number.isFinite(row.offsetMinutes))
    .sort((a, b) => a.offsetMinutes - b.offsetMinutes || String(a.date).localeCompare(String(b.date)))
    .slice(0, limit);
}

fs.mkdirSync('qa-artifacts', { recursive: true });
const browser = await chromium.launch({ headless: true });
let report;
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, locale: 'he-IL' });
  const errors = [];
  page.on('pageerror', error => errors.push(String(error?.stack || error)));
  page.on('console', msg => { if (msg.type() === 'error') errors.push(`console: ${msg.text()}`); });
  const response = await page.goto(TARGET_URL, { waitUntil: 'domcontentloaded', timeout: 120_000 });
  if (!response?.ok()) throw new Error(`Target returned HTTP ${response?.status()}`);
  await page.waitForSelector('#annualYear', { timeout: 30_000 });
  await page.evaluate(async () => { if (typeof ensureBuiltInCatalogReady === 'function') await ensureBuiltInCatalogReady(); });
  await setBase(page);
  await installPatchedWorker(page);

  const stars = await topTen(page);
  if (stars.length !== 10) throw new Error(`Expected ten stars, found ${stars.length}`);
  console.log('Selected stars:', stars.map((s, i) => `${i + 1}. ${s.name} (${s.mag})`).join(' | '));

  const starResults = [];
  for (let i = 0; i < stars.length; i += 1) {
    const star = stars[i];
    console.log(`[${i + 1}/10] ${star.name}`);
    const rows = await runAnnual(page, starCsv(star), false);
    const earliest = best(rows, 1)[0] || null;
    starResults.push({
      rankByCatalogBrightness: i + 1,
      catalogStar: star,
      daysFound: rows.filter(row => row.found).length,
      annualEarliest: earliest ? {
        ...earliest,
        localEventTime: formatLocal(earliest.eventTimeMs),
        localSunsetTime: formatLocal(earliest.sunsetTimeMs),
      } : null,
    });
  }

  console.log('Planet sanity run');
  const planetRows = await runAnnual(page, 'name,raHours,decDeg,mag,bv\nFaint validation dummy,0,0,10,0.65', true);
  const planetTop = best(planetRows, 10).map(row => ({
    ...row,
    localEventTime: formatLocal(row.eventTimeMs),
    localSunsetTime: formatLocal(row.sunsetTimeMs),
  }));
  if (!planetTop.some(row => row.object?.isPlanet)) throw new Error('Planet sanity run found no planet');

  report = {
    generatedAt: new Date().toISOString(),
    targetUrl: TARGET_URL,
    year: YEAR,
    location: LOCATION,
    settings: {
      minimumApparentAltitudeDeg: MIN_ALT_DEG,
      magnitudeBasis: 'catalog',
      brightThresholdMag: BRIGHT_THRESHOLD_MAG,
      stableVisibilitySeconds: 60,
      preSunsetLookbackMinutes: LOOKBACK_MINUTES,
      moonlight: 'included',
      skyPreset: 'dark',
      observerMode: 'ordinaryOrGuided',
    },
    selectionRule: 'Ten brightest built-in catalog stars whose maximum geometric altitude at Jerusalem reaches the 3 degree calculator minimum.',
    starResults,
    planetSanityTop10: planetTop,
    pageErrors: errors,
  };
  fs.writeFileSync('qa-artifacts/jerusalem-bright-stars-2026.json', JSON.stringify(report, null, 2));
  console.log('JERUSALEM_REPORT_BEGIN');
  console.log(JSON.stringify(report, null, 2));
  console.log('JERUSALEM_REPORT_END');
  if (process.env.GITHUB_STEP_SUMMARY) {
    const lines = ['# Jerusalem bright-star annual visibility — 2026', '', '| # | Star | Mag | Earliest date | Local time | From sunset |', '|---:|---|---:|---|---|---:|'];
    for (const row of starResults) {
      const e = row.annualEarliest;
      lines.push(`| ${row.rankByCatalogBrightness} | ${row.catalogStar.name} | ${row.catalogStar.mag.toFixed(2)} | ${e?.date || '—'} | ${e?.localEventTime || '—'} | ${Number.isFinite(e?.offsetMinutes) ? e.offsetMinutes.toFixed(2) + ' min' : '—'} |`);
    }
    fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY, lines.join('\n') + '\n');
  }
} finally {
  await browser.close();
}
