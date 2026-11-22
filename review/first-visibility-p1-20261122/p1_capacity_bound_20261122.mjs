#!/usr/bin/env node
// P1-FVS-20261122-R0 | deterministic PRE-OUTCOME capacity and independent-unit audit.
// No observer data, predictions, model calibration, solver, or network access.
import assert from "node:assert/strict";

const freeze = Object.freeze({
  protocol_id: "P1-FVS-20261122-R0",
  protocol_blob: "9003f0a4be530539ce58a0ffc6d40288286711d0",
  status: "REVIEW_ONLY_NO_FIELD_CONSENT_NO_SCIENTIFIC_REGISTRATION",
  max_sites: 2,
  consenting_observers_per_site: 2,
  fixed_hip_targets_per_site: 3,
  max_usable_evenings: 12,
  max_calendar_days: 30,
  max_spend_usd: 0,
  feasibility_required_brackets: 12,
  late_descriptive_required_brackets: 6,
  powered_screen_required_independent_site_night_clusters: 30,
  bootstrap_sampling_unit: "site-night"
});
function capacity(spec) {
  for (const k of ["max_sites","consenting_observers_per_site","fixed_hip_targets_per_site","max_usable_evenings","max_calendar_days","feasibility_required_brackets","late_descriptive_required_brackets","powered_screen_required_independent_site_night_clusters"]) {
    if (!Number.isSafeInteger(spec[k]) || spec[k] <= 0) throw Error("INVALID_CAP_"+k);
  }
  if (spec.max_spend_usd !== 0) throw Error("PAID_SCOPE_NOT_AUTHORIZED");
  // The generous interpretation grants EVERY site its own 12 independent evenings.
  // If 12 evenings is a study-wide total, the bound is lower, not higher.
  const maximum_independent_site_night_clusters = spec.max_sites * spec.max_usable_evenings;
  const maximum_event_brackets_under_ideal_weather = maximum_independent_site_night_clusters * spec.consenting_observers_per_site * spec.fixed_hip_targets_per_site;
  return {
    protocol_id: spec.protocol_id,
    status: spec.status,
    assumption: "UPPER_BOUND_12_EVENINGS_PER_SITE_ALL_STARS_SEEN_IDEAL_WEATHER",
    max_independent_site_night_clusters: maximum_independent_site_night_clusters,
    max_theoretical_per_star_observer_brackets: maximum_event_brackets_under_ideal_weather,
    pilot_feasibility_min_brackets: spec.feasibility_required_brackets,
    pilot_late_descriptive_min_brackets: spec.late_descriptive_required_brackets,
    powered_screen_min_independent_clusters: spec.powered_screen_required_independent_site_night_clusters,
    powered_screen_reachable_in_P1: maximum_independent_site_night_clusters >= spec.powered_screen_required_independent_site_night_clusters,
    actual_human_brackets: 0,
    actual_independent_clusters: 0,
    model_prediction_errors: null,
    late_domain_numeric_model_support: "UNSUPPORTED/null",
    interpretation: "CAPACITY_BOUND_ONLY__NOT_A_FIELD_RESULT__P1_FEASIBILITY_ONLY"
  };
}
const output=capacity(freeze);
assert.equal(output.max_independent_site_night_clusters,24);
assert.equal(output.max_theoretical_per_star_observer_brackets,144);
assert.equal(output.powered_screen_reachable_in_P1,false);
assert.equal(output.model_prediction_errors,null);
assert.equal(output.actual_human_brackets,0);
assert.equal(capacity({...freeze,max_sites:1}).max_independent_site_night_clusters,12);
assert.equal(capacity({...freeze,max_usable_evenings:1}).max_independent_site_night_clusters,2);
assert.throws(()=>capacity({...freeze,max_spend_usd:1}),/PAID_SCOPE/);
assert.throws(()=>capacity({...freeze,max_sites:0}),/INVALID_CAP/);
if (process.argv.length > 2 && process.argv[2] !== "--self-test") throw Error("UNKNOWN_ARGUMENT");
console.log(JSON.stringify({test_assertions_passed:8,...output},null,2));
