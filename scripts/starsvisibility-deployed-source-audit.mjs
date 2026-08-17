const targetUrl = process.env.TARGET_URL || 'https://preview-level-b-v3-sitewide-9a29.starsvisibility.pages.dev/';
const response = await fetch(targetUrl, { redirect: 'follow' });
const html = await response.text();
if (!response.ok) throw new Error(`Preview returned HTTP ${response.status}`);

const functionNeedle = 'async function __levelBSitewideRecomputeThreeStar';
const start = html.indexOf(functionNeedle);
if (start < 0) throw new Error('Three-Star recompute function not found');
const source = html.slice(start, start + 30000);

function sliceAround(needle, before = 900, after = 1800) {
  const index = source.indexOf(needle);
  if (index < 0) return null;
  return source.slice(Math.max(0, index - before), Math.min(source.length, index + needle.length + after));
}

const audit = {
  url: response.url,
  bytes: html.length,
  functionBytesCaptured: source.length,
  minAltitudeSetup: sliceAround('LEVEL-B-THREE-STAR-MIN-ALTITUDE-V1'),
  equilibriumEventSelection: sliceAround('findStableSimultaneousQualifiedEvent(candidates', 1800, 1800),
  effectiveTransientSelection: sliceAround("} else if (basis === 'effective')", 400, 2600),
  failureDiagnostics: sliceAround("const failureReason = eligibleCandidates.length < requiredCount", 300, 2200),
  successDiagnostics: sliceAround("modelVersion: 'Level-B-v3-sitewide-preview'", 1800, 500),
};
console.log(JSON.stringify(audit, null, 2));
