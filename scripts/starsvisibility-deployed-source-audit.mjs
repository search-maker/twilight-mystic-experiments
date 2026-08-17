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
function snippets(needle, before = 350, after = 900) {
  return allIndices(needle).map((index, ordinal) => ({
    ordinal: ordinal + 1,
    index,
    source: html.slice(Math.max(0, index - before), Math.min(html.length, index + needle.length + after)),
  }));
}
function functionSlice(name, maxBytes = 18000) {
  const needle = `function ${name}`;
  const index = html.indexOf(needle);
  if (index < 0) return null;
  return html.slice(index, Math.min(html.length, index + maxBytes));
}

const recomputeStart = html.indexOf('async function __levelBSitewideRecomputeThreeStar');
const recomputeSource = recomputeStart < 0 ? '' : html.slice(recomputeStart, recomputeStart + 30000);
const audit = {
  url: response.url,
  bytes: html.length,
  counts: {
    threeStarResultDataMentions: allIndices('threeStarResultData').length,
    directAssignments: allIndices('threeStarResultData =').length,
    eventTimePropertyWrites: allIndices('threeStarResultData.eventTime').length,
    candidateCountPropertyWrites: allIndices('threeStarResultData.candidateCount').length,
    eligibleCountPropertyWrites: allIndices('threeStarResultData.eligibleCandidateCount').length,
    renderFunctionDefinitions: allIndices('function renderThreeStarResult').length,
    renderCalls: allIndices('renderThreeStarResult(').length,
  },
  directAssignments: snippets('threeStarResultData =', 500, 1400),
  eventTimePropertyWrites: snippets('threeStarResultData.eventTime', 400, 900),
  candidateCountPropertyWrites: snippets('threeStarResultData.candidateCount', 400, 900),
  renderFunction: functionSlice('renderThreeStarResult', 22000),
  recomputeSuccess: (() => {
    const needle = "modelVersion: 'Level-B-v3-sitewide-preview'";
    const i = recomputeSource.indexOf(needle);
    return i < 0 ? null : recomputeSource.slice(Math.max(0, i - 2200), Math.min(recomputeSource.length, i + 1200));
  })(),
};
console.log(JSON.stringify(audit, null, 2));
