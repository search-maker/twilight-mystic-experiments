import fs from 'node:fs';

const path = process.argv[2];
if (!path) throw new Error('diagnostics JSON path required');
const diagnostics = JSON.parse(fs.readFileSync(path, 'utf8'));
if (!Array.isArray(diagnostics) || diagnostics.length === 0) throw new Error('diagnostics must be a non-empty array');

const isRumUrl = value => /https:\/\/cloudflareinsights\.com\/cdn-cgi\/rum(?:\b|\?|$)/i.test(String(value || ''));
const allowedAssertionFailure = message => /^No console errors \(got \d+\)$/.test(String(message || ''))
  || /^No failed network requests \(got \d+\)$/.test(String(message || ''));

let sawRumNoise = false;
for (const diag of diagnostics) {
  const failedAssertions = (diag.assertions || []).filter(item => item?.ok === false);
  if (failedAssertions.some(item => !allowedAssertionFailure(item?.message))) {
    throw new Error(`Non-RUM assertion failure remains: ${JSON.stringify(failedAssertions)}`);
  }

  const failedRequests = diag.failedRequests || [];
  if (failedRequests.some(item => !isRumUrl(item?.url))) {
    throw new Error(`Non-RUM failed request remains: ${JSON.stringify(failedRequests)}`);
  }
  if (failedRequests.length) sawRumNoise = true;

  const consoleErrors = diag.consoleErrors || [];
  const hasRumRequest = failedRequests.some(item => isRumUrl(item?.url));
  for (const message of consoleErrors) {
    const text = String(message || '');
    const allowed = /cloudflareinsights\.com\/cdn-cgi\/rum/i.test(text)
      || (hasRumRequest && text === 'Failed to load resource: net::ERR_FAILED');
    if (!allowed) throw new Error(`Non-RUM console error remains: ${text}`);
    sawRumNoise = true;
  }
}

if (!sawRumNoise) throw new Error('Original QA failed but diagnostics contain no recognized Cloudflare RUM noise');
console.log('Only Cloudflare Web Analytics RUM CORS noise was ignored; all product assertions passed.');
