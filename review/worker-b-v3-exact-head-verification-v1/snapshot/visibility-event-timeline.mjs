function requireFinite(name, value) {
  if (!Number.isFinite(value)) throw new RangeError(`${name} must be finite; got ${value}`);
  return value;
}

function requirePositiveFinite(name, value) {
  requireFinite(name, value);
  if (!(value > 0)) throw new RangeError(`${name} must be > 0; got ${value}`);
  return value;
}

function requirePositiveInteger(name, value) {
  if (!Number.isInteger(value) || value < 1) {
    throw new RangeError(`${name} must be a positive integer; got ${value}`);
  }
  return value;
}

function refineVisibilityTransition({
  lowerDeg,
  upperDeg,
  lowerMarginMag,
  upperMarginMag,
  margin,
  toleranceDeg,
  maxIterations,
}) {
  let lo = lowerDeg;
  let hi = upperDeg;
  let loMargin = lowerMarginMag;
  let hiMargin = upperMarginMag;
  const loVisible = loMargin >= 0;
  const hiVisible = hiMargin >= 0;
  if (loVisible === hiVisible) {
    throw new Error('visibility transition bracket does not change state');
  }
  if (loMargin === 0) {
    return {
      sunDepressionDeg: lo,
      iterations: 0,
      bracketWidthDeg: 0,
      lowerBracketDeg: lo,
      upperBracketDeg: lo,
      lowerBracketMarginMag: loMargin,
      upperBracketMarginMag: loMargin,
    };
  }
  if (hiMargin === 0) {
    return {
      sunDepressionDeg: hi,
      iterations: 0,
      bracketWidthDeg: 0,
      lowerBracketDeg: hi,
      upperBracketDeg: hi,
      lowerBracketMarginMag: hiMargin,
      upperBracketMarginMag: hiMargin,
    };
  }
  let iterations = 0;
  while ((hi - lo) > toleranceDeg && iterations < maxIterations) {
    const mid = (lo + hi) / 2;
    const midMargin = margin(mid);
    const midVisible = midMargin >= 0;
    if (midVisible === loVisible) {
      lo = mid;
      loMargin = midMargin;
    } else {
      hi = mid;
      hiMargin = midMargin;
    }
    iterations += 1;
  }
  if ((hi - lo) > toleranceDeg) {
    throw new Error(
      `visibility transition did not converge within maxIterations=${maxIterations}`,
    );
  }
  return {
    sunDepressionDeg: (lo + hi) / 2,
    iterations,
    bracketWidthDeg: hi - lo,
    lowerBracketDeg: lo,
    upperBracketDeg: hi,
    lowerBracketMarginMag: loMargin,
    upperBracketMarginMag: hiMargin,
  };
}

function visibilityIntervalsFromCrossings({
  lowerVisible,
  upperVisible,
  minSunDepressionDeg,
  maxSunDepressionDeg,
  crossings,
}) {
  const intervals = [];
  let start = lowerVisible ? null : undefined;
  for (const crossing of crossings) {
    if (crossing.type === 'entry') {
      if (start !== undefined) {
        throw new Error('encountered an entry while visibility was already active');
      }
      start = crossing.sunDepressionDeg;
    } else if (crossing.type === 'exit') {
      if (start === undefined) {
        throw new Error('encountered an exit while visibility was inactive');
      }
      intervals.push({
        startSunDepressionDeg: start,
        endSunDepressionDeg: crossing.sunDepressionDeg,
        leftCensored: start === null,
        rightCensored: false,
      });
      start = undefined;
    }
  }
  if (start !== undefined) {
    intervals.push({
      startSunDepressionDeg: start,
      endSunDepressionDeg: null,
      leftCensored: start === null,
      rightCensored: true,
    });
  }
  const finalVisible = start !== undefined;
  if (finalVisible !== upperVisible) {
    throw new Error('crossing sequence is inconsistent with the upper-bound state');
  }
  return intervals.map(interval => ({
    ...interval,
    domainLowerSunDepressionDeg: minSunDepressionDeg,
    domainUpperSunDepressionDeg: maxSunDepressionDeg,
  }));
}

/**
 * Chronologically scan and refine every threshold transition in a visibility
 * margin. The callback must return a finite magnitude margin, with values >= 0
 * meaning visible. Unlike endpoint-only bisection, this routine does not assume
 * that visibility improves monotonically as solar depression increases.
 *
 * A finite scan cannot prove that no arbitrarily narrow visible interval exists.
 * The returned `scanGuarantee` and actual `scanStepDeg` therefore remain part of
 * the scientific result. An end-to-end protocol must set an explicit scan step
 * from its temporal-resolution requirement rather than relying on root precision
 * alone.
 */
export function solveVisibilityMarginCrossing({
  minSunDepressionDeg,
  maxSunDepressionDeg,
  visibilityMarginMagAtDepression,
  toleranceDeg = 1e-8,
  maxIterations = 120,
  scanStepDeg = null,
  maxScanSamples = 20001,
}) {
  requireFinite('minSunDepressionDeg', minSunDepressionDeg);
  requireFinite('maxSunDepressionDeg', maxSunDepressionDeg);
  requirePositiveFinite('toleranceDeg', toleranceDeg);
  requirePositiveInteger('maxIterations', maxIterations);
  requirePositiveInteger('maxScanSamples', maxScanSamples);
  if (!(maxSunDepressionDeg > minSunDepressionDeg)) {
    throw new RangeError('maxSunDepressionDeg must exceed minSunDepressionDeg');
  }
  if (typeof visibilityMarginMagAtDepression !== 'function') {
    throw new TypeError('visibilityMarginMagAtDepression must be a function');
  }

  const rangeDeg = maxSunDepressionDeg - minSunDepressionDeg;
  const requestedScanStepDeg = scanStepDeg == null
    ? Math.min(0.01, rangeDeg / 2048)
    : requirePositiveFinite('scanStepDeg', scanStepDeg);
  const scanSegmentCount = Math.ceil(rangeDeg / requestedScanStepDeg);
  const sampleCount = scanSegmentCount + 1;
  if (sampleCount > maxScanSamples) {
    throw new RangeError(
      `scan requires ${sampleCount} samples, exceeding maxScanSamples=${maxScanSamples}`,
    );
  }
  const actualScanStepDeg = rangeDeg / scanSegmentCount;

  const margin = d => {
    const value = visibilityMarginMagAtDepression(d);
    return requireFinite(`visibility margin at d=${d}`, value);
  };

  const samples = [];
  const lowerMargin = margin(minSunDepressionDeg);
  samples.push({
    sunDepressionDeg: minSunDepressionDeg,
    marginMag: lowerMargin,
    visible: lowerMargin >= 0,
  });
  const crossings = [];
  for (let index = 1; index <= scanSegmentCount; index += 1) {
    const depression = index === scanSegmentCount
      ? maxSunDepressionDeg
      : minSunDepressionDeg + index * actualScanStepDeg;
    const currentMargin = margin(depression);
    const current = {
      sunDepressionDeg: depression,
      marginMag: currentMargin,
      visible: currentMargin >= 0,
    };
    const previous = samples[samples.length - 1];
    samples.push(current);
    if (previous.visible !== current.visible) {
      const transition = refineVisibilityTransition({
        lowerDeg: previous.sunDepressionDeg,
        upperDeg: current.sunDepressionDeg,
        lowerMarginMag: previous.marginMag,
        upperMarginMag: current.marginMag,
        margin,
        toleranceDeg,
        maxIterations,
      });
      crossings.push({
        type: previous.visible ? 'exit' : 'entry',
        visibleBefore: previous.visible,
        visibleAfter: current.visible,
        scanBracketLowerDeg: previous.sunDepressionDeg,
        scanBracketUpperDeg: current.sunDepressionDeg,
        ...transition,
      });
    }
  }

  const upperMargin = samples[samples.length - 1].marginMag;
  const lowerVisible = lowerMargin >= 0;
  const upperVisible = upperMargin >= 0;
  const entryCrossings = crossings.filter(crossing => crossing.type === 'entry');
  const exitCrossings = crossings.filter(crossing => crossing.type === 'exit');
  const visibilityIntervals = visibilityIntervalsFromCrossings({
    lowerVisible,
    upperVisible,
    minSunDepressionDeg,
    maxSunDepressionDeg,
    crossings,
  });
  const common = {
    lowerMarginMag: lowerMargin,
    upperMarginMag: upperMargin,
    scanStepDeg: actualScanStepDeg,
    requestedScanStepDeg,
    sampleCount,
    crossingCount: crossings.length,
    crossings,
    visibilityIntervals,
    multipleCrossings: crossings.length > 1,
    nonMonotonicVisibilityDetected: exitCrossings.length > 0 || entryCrossings.length > 1,
    scanGuarantee: (
      'all state changes intersecting the sampled grid are refined; a complete ' +
      'visible interval narrower than scanStepDeg can still be missed'
    ),
  };

  if (lowerVisible) {
    return {
      status: 'already-visible-at-lower-bound',
      sunDepressionDeg: minSunDepressionDeg,
      censoring: 'true first entry is at or before the lower model-domain bound',
      ...common,
    };
  }

  if (entryCrossings.length === 0) {
    return {
      status: 'not-visible-at-upper-bound',
      sunDepressionDeg: null,
      censoring: (
        'no visible state was sampled inside the model domain; first entry is ' +
        'after the upper bound, absent, or narrower than scanStepDeg'
      ),
      ...common,
    };
  }

  const firstEntry = entryCrossings[0];
  return {
    status: 'root',
    sunDepressionDeg: firstEntry.sunDepressionDeg,
    iterations: firstEntry.iterations,
    bracketWidthDeg: firstEntry.bracketWidthDeg,
    firstEntryCrossingIndex: crossings.indexOf(firstEntry),
    censoring: null,
    ...common,
  };
}

export const solveVisibilityMarginTimeline = solveVisibilityMarginCrossing;
