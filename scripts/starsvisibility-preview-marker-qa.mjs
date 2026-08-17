const targetUrl = process.env.TARGET_URL;
if (!targetUrl || !/^https:\/\//.test(targetUrl)) throw new Error('TARGET_URL must be a public https URL');

const response = await fetch(targetUrl, { redirect: 'follow' });
const html = await response.text();
const marker = 'LEVEL-B-THREE-STAR-MIN-ALTITUDE-V1';
const routingMarker = 'LEVEL-B-THREE-STAR-POINTWISE-SUPPORT-V1';
const runtimeProbe = '__LEVEL_B_THREE_STAR_MIN_ALTITUDE_RUNTIME__';
const result = {
  url: response.url,
  status: response.status,
  ok: response.ok,
  bytes: html.length,
  routingMarkerPresent: html.includes(routingMarker),
  minimumAltitudeMarkerPresent: html.includes(marker),
  minimumAltitudeRuntimeProbePresent: html.includes(runtimeProbe),
};
console.log(JSON.stringify(result, null, 2));
if (!response.ok) throw new Error(`Preview returned HTTP ${response.status}`);
if (!result.routingMarkerPresent) throw new Error('Existing Three-Star pointwise routing marker is missing from Preview HTML');
if (!result.minimumAltitudeMarkerPresent) throw new Error('New Three-Star minimum-altitude patch marker is missing from Preview HTML');
if (!result.minimumAltitudeRuntimeProbePresent) throw new Error('Latest Three-Star minimum-altitude runtime probe is missing from Preview HTML');
