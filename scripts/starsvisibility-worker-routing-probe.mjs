import { chromium } from 'playwright';

const targetUrl = process.env.TARGET_URL;
if (!targetUrl || !/^https:\/\//.test(targetUrl)) throw new Error('TARGET_URL must be a public https URL');

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, locale: 'he-IL' });
const page = await context.newPage();

async function setValueSilently(selector, value) {
  await page.locator(selector).evaluate((el, nextValue) => {
    const proto = el instanceof HTMLInputElement ? HTMLInputElement.prototype
      : el instanceof HTMLSelectElement ? HTMLSelectElement.prototype
      : HTMLElement.prototype;
    const descriptor = Object.getOwnPropertyDescriptor(proto, 'value');
    if (descriptor?.set) descriptor.set.call(el, String(nextValue));
    else el.value = String(nextValue);
  }, value);
}

try {
  const response = await page.goto(targetUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });
  if (!response?.ok()) throw new Error(`Preview returned HTTP ${response?.status()}`);
  await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
  await page.locator('#visibilityEngineMode').waitFor({ state: 'attached', timeout: 20000 });

  const install = await page.evaluate(() => {
    try {
      return globalThis.eval(`
        disposeReusableCalculationWorker();
        activeCalculationWorker = null;
        workerEnabled = true;
        calculationResultsFinal = false;
        threeStarResultData = null;
        lastRunMetadata = {};
        globalThis.__WORKER_ROUTING_PROBE__ = { posts: [], messages: [] };
        const NativeWorker = globalThis.Worker;
        globalThis.__WORKER_ROUTING_NATIVE__ = NativeWorker;
        globalThis.Worker = class RoutingProbeWorker extends NativeWorker {
          constructor(...args) {
            super(...args);
            this.addEventListener('message', event => {
              const data = event.data || {};
              globalThis.__WORKER_ROUTING_PROBE__.messages.push({
                type: data.type ?? null,
                phase: data.phase ?? null,
                resultStatus: data.resultStatus ?? null,
                error: data.error ?? null,
                cacheHit: data.cacheHit ?? null,
                completed: data.completed ?? null,
                total: data.total ?? null,
                metadataEngine: data.metadata?.calculationEngine ?? data.metadata?.levelBRunProvenance?.calculationEngine ?? null,
                resultEngine: data.threeStarResult?.calculationEngine ?? null,
                resultFound: data.threeStarResult?.found ?? null,
                resultCandidateCount: data.threeStarResult?.candidateCount ?? null,
              });
            });
          }
          postMessage(message, ...rest) {
            globalThis.__WORKER_ROUTING_PROBE__.posts.push({
              mode: message?.mode ?? null,
              feature: message?.values?.calculatorFeature?.value ?? null,
              engine: message?.values?.visibilityEngineMode?.value ?? null,
              minAlt: message?.values?.minAlt?.value ?? null,
              basis: message?.values?.threeStarMagnitudeBasis?.value ?? null,
              threshold: message?.values?.threeStarMagnitudeThreshold?.value ?? null,
              count: message?.values?.threeStarCount?.value ?? null,
            });
            return super.postMessage(message, ...rest);
          }
        };
        ({ workerEnabled, nativeWorkerType: typeof NativeWorker })
      `);
    } catch (error) {
      return { error: String(error?.stack || error) };
    }
  });
  if (install?.error) throw new Error(`Could not install worker routing probe: ${install.error}`);

  await setValueSilently('#calculatorFeature', 'three-star');
  await setValueSilently('#threeStarMagnitudeBasis', 'effective');
  await setValueSilently('#threeStarMagnitudeThreshold', '1.7');
  await setValueSilently('#threeStarCount', '3');
  await setValueSilently('#minAlt', '89');
  await setValueSilently('#visibilityEngineMode', 'level-b-v3-crumey-blackwell-equilibrium');

  const inputs = await page.evaluate(() => ({
    feature: document.querySelector('#calculatorFeature')?.value ?? null,
    engine: document.querySelector('#visibilityEngineMode')?.value ?? null,
    engineFromRuntime: globalThis.eval('__levelBSitewideEngineMode()'),
    minAlt: document.querySelector('#minAlt')?.value ?? null,
  }));

  await page.locator('#calculate').click();
  await page.waitForFunction(() => {
    const messages = globalThis.__WORKER_ROUTING_PROBE__?.messages || [];
    return messages.some(message => message.phase === 'level-b-sitewide' || message.type === 'done' || message.type === 'error');
  }, { timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(250);

  const probe = await page.evaluate(() => ({
    ...(globalThis.__WORKER_ROUTING_PROBE__ || { posts: [], messages: [] }),
    calculationResultsFinal: globalThis.eval('calculationResultsFinal'),
    finalResultEngine: globalThis.eval('threeStarResultData?.calculationEngine ?? null'),
    finalMetadataEngine: globalThis.eval('lastRunMetadata?.calculationEngine ?? lastRunMetadata?.levelBRunProvenance?.calculationEngine ?? null'),
  }));
  const diagnostic = { url: page.url(), install, inputs, probe };
  console.log(JSON.stringify(diagnostic, null, 2));

  const post = probe.posts[0];
  if (!post) throw new Error('No calculation worker request was posted');
  if (post.engine !== 'level-b-v3-crumey-blackwell-equilibrium') {
    throw new Error(`Worker request carried engine=${post.engine}, expected Level-B equilibrium`);
  }
  if (post.minAlt !== '89') throw new Error(`Worker request carried minAlt=${post.minAlt}, expected 89`);

  const firstSignal = probe.messages.find(message => message.phase === 'level-b-sitewide' || message.type === 'done' || message.type === 'error');
  if (!firstSignal) throw new Error('Worker produced no Level-B progress, done, or error signal within probe window');
  if (firstSignal.type === 'done' && firstSignal.metadataEngine === 'legacy') {
    throw new Error('Worker received Level-B inputs but completed with Legacy metadata');
  }
  if (firstSignal.type === 'error') throw new Error(`Worker errored before Level-B completion: ${firstSignal.error}`);
} finally {
  await context.close();
  await browser.close();
}
