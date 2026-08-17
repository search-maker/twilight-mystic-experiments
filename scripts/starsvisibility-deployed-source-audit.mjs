const targetUrl = process.env.TARGET_URL || 'https://preview-level-b-v3-sitewide-9a29.starsvisibility.pages.dev/';
const response = await fetch(targetUrl, { redirect: 'follow' });
const html = await response.text();
if (!response.ok) throw new Error(`Preview returned HTTP ${response.status}`);

function allIndices(needle) {
  const out = [];
  let from = 0;
  while (true) {
    const index = html.indexOf(needle, from);
    if (index < 0) break;
    out.push(index);
    from = index + Math.max(1, needle.length);
  }
  return out;
}
function functionSlices(name, maxBytes = 9000) {
  const out = [];
  for (const prefix of [`async function ${name}`, `function ${name}`]) {
    for (const index of allIndices(prefix)) {
      out.push({ prefix, index, source: html.slice(index, Math.min(html.length, index + maxBytes)) });
    }
  }
  return out.sort((a, b) => a.index - b.index);
}
function functionSlice(name, maxBytes = 22000) {
  return functionSlices(name, maxBytes)[0]?.source ?? null;
}
function around(needle, before = 700, after = 2200) {
  const index = html.indexOf(needle);
  if (index < 0) return null;
  return html.slice(Math.max(0, index - before), Math.min(html.length, index + needle.length + after));
}

const audit = {
  url: response.url,
  bytes: html.length,
  counts: {
    workerFunctions: allIndices('function createReusableCalculationWorker').length,
    calculateInWorkerDefinitions: allIndices('function calculateInWorker').length,
    calculateDefinitions: allIndices('async function calculate()').length,
    workerModeMentions: allIndices('visibilityEngineMode').length,
    sitewideDispatchMentions: allIndices('const __sitewideEngineMode = __levelBSitewideEngineMode();').length,
    calculateButtonBindings: allIndices('$("calculate").addEventListener("click", calculate)').length,
    scaffoldDefinitions: allIndices('async function __levelBSitewideRunUsingLegacyScaffold').length,
    catalogOnlyMarkers: allIndices('__LEVEL_B_SITEWIDE_CATALOG_ONLY_SCAFFOLD__').length,
  },
  calculateFunctions: functionSlices('calculate', 7000),
  levelBScaffold: functionSlice('__levelBSitewideRunUsingLegacyScaffold', 9000),
  levelBPostprocess: functionSlice('__levelBSitewidePostprocess', 12000),
  catalogOnlyHook: around('LEVEL-B-THREE-STAR-DIRECT-CATALOG-HOOK-V2', 1000, 1800),
  createReusableCalculationWorker: functionSlice('createReusableCalculationWorker', 12000),
  calculateInWorker: functionSlice('calculateInWorker', 8000),
  calculateButtonBinding: around('$("calculate").addEventListener("click", calculate)', 1000, 1600),
  appScriptSource: around('const APP_SCRIPT_SOURCE = document.currentScript?.textContent || "";', 1200, 1600),
  sitewideDispatch: around('const __sitewideEngineMode = __levelBSitewideEngineMode();', 1800, 2200),
};
console.log(JSON.stringify(audit, null, 2));
