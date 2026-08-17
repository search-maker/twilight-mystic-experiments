const targetUrl = process.env.TARGET_URL;
if (!targetUrl || !/^https:\/\//.test(targetUrl)) throw new Error('TARGET_URL must be a public https URL');

const response = await fetch(targetUrl, { redirect: 'follow' });
const html = await response.text();
const marker = 'LEVEL-B-THREE-STAR-MIN-ALTITUDE-V1';
const routingMarker = 'LEVEL-B-THREE-STAR-POINTWISE-SUPPORT-V1';
const result = {
  url: response.url,
  status: response.status,
  ok: response.ok,
  bytes: html.length,
  routingMarkerPresent: html.includes(routingMarker),
  minimumAltitudeMarkerPresent: html.includes(marker),
};
console.log(JSON.stringify(result, null, 2));
if (!response.ok) throw new Error(`Preview returned HTTP ${response.status}`);
if (!result.routingMarkerPresent) throw new Error('Existing Three-Star pointwise routing marker is missing from Preview HTML');
if (!result.minimumAltitudeMarkerPresent) throw new Error('New Three-Star minimum-altitude patch marker is missing from Preview HTML');
