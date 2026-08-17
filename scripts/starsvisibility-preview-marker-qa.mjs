const targetUrl = process.env.TARGET_URL;
if (!targetUrl || !/^https:\/\//.test(targetUrl)) throw new Error('TARGET_URL must be a public https URL');

const response = await fetch(targetUrl, { redirect: 'follow' });
const html = await response.text();
const marker = 'LEVEL-B-THREE-STAR-MIN-ALTITUDE-V1';
const routingMarker = 'LEVEL-B-THREE-STAR-POINTWISE-SUPPORT-V1';
const timeParityMarker = 'LEVEL-B-THREE-STAR-RESULT-TIME-PARITY-V1';
const runtimeProbe = '__LEVEL_B_THREE_STAR_MIN_ALTITUDE_RUNTIME__';
const count = needle => html.split(needle).length - 1;
const result = {
  url: response.url,
  status: response.status,
  ok: response.ok,
  bytes: html.length,
  routingMarkerPresent: html.includes(routingMarker),
  minimumAltitudeMarkerPresent: html.includes(marker),
  resultTimeParityMarkerPresent: html.includes(timeParityMarker),
  minimumAltitudeRuntimeProbePresent: html.includes(runtimeProbe),
  recomputeFunctionCount: count('async function __levelBSitewideRecomputeThreeStar'),
  routingMarkerCount: count(routingMarker),
  minimumAltitudeMarkerCount: count(marker),
  resultTimeParityMarkerCount: count(timeParityMarker),
  minimumAltitudeGuardCount: count('if (!meetsMinimumAltitudeAt(entry, timestampMs)) return false;'),
  minimumAltitudeReaderCount: count('const rawMinStarAltitudeDeg = Number($("minAlt")?.value);'),
  successTimeParityCount: count('time: event.eventTimeMs, eventTime: event.eventTimeMs'),
  failureTimeParityCount: count('time: null, eventTime: null'),
};
console.log(JSON.stringify(result, null, 2));
if (!response.ok) throw new Error(`Preview returned HTTP ${response.status}`);
if (!result.routingMarkerPresent) throw new Error('Existing Three-Star pointwise routing marker is missing from Preview HTML');
if (!result.minimumAltitudeMarkerPresent) throw new Error('New Three-Star minimum-altitude patch marker is missing from Preview HTML');
if (!result.resultTimeParityMarkerPresent) throw new Error('Three-Star Level-B result-time parity patch marker is missing from Preview HTML');
if (result.recomputeFunctionCount !== 1) throw new Error(`Expected one Three-Star recompute function, found ${result.recomputeFunctionCount}`);
if (result.minimumAltitudeGuardCount !== 2) throw new Error(`Expected two min-altitude guards, found ${result.minimumAltitudeGuardCount}`);
if (result.minimumAltitudeReaderCount !== 1) throw new Error(`Expected one min-altitude reader, found ${result.minimumAltitudeReaderCount}`);
if (result.successTimeParityCount !== 1) throw new Error(`Expected one Level-B success time parity assignment, found ${result.successTimeParityCount}`);
if (result.failureTimeParityCount < 1) throw new Error('Expected Level-B failure result to expose time=null and eventTime=null');
