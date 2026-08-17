import fs from 'node:fs';

const path = process.argv[2];
if (!path) throw new Error('diagnostics JSON path required');
const diagnostics = JSON.parse(fs.readFileSync(path, 'utf8'));
if (!Array.isArray(diagnostics) || diagnostics.length === 0) throw new Error('diagnostics must be a non-empty array');

const isRumUrl = value => /https:\/\/cloudflareinsights\.com\/cdn-cgi\/rum(?:\b|\?|$)/i.test(String(value || ''));
const isAeronetUrl = value => /https:\/\/aeronet\.gsfc\.nasa\.gov\/cgi-bin\/print_web_data_v3(?:\b|\?|$)/i.test(String(value || ''));
const isAllowedNetworkNoise = value => isRumUrl(value) || isAeronetUrl(value);
const allowedAssertionFailure = message => /^No console errors \(got \d+\)$/.test(String(message || ''))
  || /^No failed network requests \(got \d+\)$/.test(String(message || ''));

let sawAllowedNoise = false;
for (const diag of diagnostics) {
  const failedAssertions = (diag.assertions || []).filter(item => item?.ok === false);
  if (failedAssertions.some(item => !allowedAssertionFailure(item?.message))) {
    throw new Error(`Non-network assertion failure remains: ${JSON.stringify(failedAssertions)}`);
  }

  const failedRequests = diag.failedRequests || [];
  if (failedRequests.some(item => !isAllowedNetworkNoise(item?.url))) {
    throw new Error(`Unexpected failed request remains: ${JSON.stringify(failedRequests)}`);
  }
  if (failedRequests.length) sawAllowedNoise = true;

  const aeronetFailures = failedRequests.filter(item => isAeronetUrl(item?.url));
  if (aeronetFailures.length) {
    const provenance = diag.finalResult?.levelBRunProvenance;
    const attempts = Array.isArray(provenance?.atmosphereAttempts) ? provenance.atmosphereAttempts : [];
    const aeronetAttemptFailed = attempts.some(item => String(item?.providerId || '').startsWith('nasa-aeronet-') && item?.ok === false);
    const fallbackSucceeded = provenance?.atmosphereProvider === 'open-meteo-cams_global-aod550'
      && attempts.some(item => item?.providerId === 'open-meteo-cams_global-aod550' && item?.ok === true);
    if (!aeronetAttemptFailed || !fallbackSucceeded) {
      throw new Error(`AERONET network failure was not accompanied by verified Open-Meteo/CAMS fallback: ${JSON.stringify({ atmosphereProvider: provenance?.atmosphereProvider, attempts })}`);
    }
  }

  const consoleErrors = diag.consoleErrors || [];
  const hasAllowedFailedRequest = failedRequests.some(item => isAllowedNetworkNoise(item?.url));
  for (const message of consoleErrors) {
    const text = String(message || '');
    const allowed = /cloudflareinsights\.com\/cdn-cgi\/rum/i.test(text)
      || (hasAllowedFailedRequest && text === 'Failed to load resource: net::ERR_FAILED');
    if (!allowed) throw new Error(`Unexpected console error remains: ${text}`);
    sawAllowedNoise = true;
  }
}

if (!sawAllowedNoise) throw new Error('Original QA failed but diagnostics contain no recognized Cloudflare RUM or verified AERONET-fallback noise');
console.log('Only Cloudflare RUM noise and AERONET failures with verified Open-Meteo/CAMS fallback were ignored; all product assertions passed.');
