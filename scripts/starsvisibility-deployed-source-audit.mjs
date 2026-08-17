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
function functionSlice(name, maxBytes = 22000) {
  for (const prefix of [`function ${name}`, `async function ${name}`]) {
    const index = html.indexOf(prefix);
    if (index >= 0) return html.slice(index, Math.min(html.length, index + maxBytes));
  }
  return null;
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
    workerModeMentions: allIndices('visibilityEngineMode').length,
    sitewideDispatchMentions: allIndices('const __sitewideEngineMode = __levelBSitewideEngineMode();').length,
  },
  createReusableCalculationWorker: functionSlice('createReusableCalculationWorker', 30000),
  calculateInWorker: functionSlice('calculateInWorker', 18000),
  appScriptSource: around('const APP_SCRIPT_SOURCE = document.currentScript?.textContent || "";', 1200, 1600),
  sitewideDispatch: around('const __sitewideEngineMode = __levelBSitewideEngineMode();', 1200, 1600),
};
console.log(JSON.stringify(audit, null, 2));
