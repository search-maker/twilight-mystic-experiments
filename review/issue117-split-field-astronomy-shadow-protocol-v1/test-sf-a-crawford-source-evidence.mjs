import assert from 'node:assert/strict';
import fs from 'node:fs';

const path = new URL('./SF_A_CRAWFORD_SOURCE_EVIDENCE_v1.json', import.meta.url);
const e = JSON.parse(fs.readFileSync(path, 'utf8'));

assert.equal(e.schema, 'SF_A_CRAWFORD_EQUIVALENT_BACKGROUND_SOURCE_EVIDENCE_V1');
assert.equal(e.status, 'FROZEN_PREOUTPUT_INDEPENDENT_PROVENANCE_ONLY');
assert.equal(e.bindings.splitFieldPr, 610);
assert.equal(e.bindings.splitFieldHeadBeforeThisAmendment, '5f78825dd6ec275081f28373ad53b87c463d6a94');
assert.equal(e.bindings.applicationSha, 'e0da52eb0a2d5bac333da6572f51df52ea7e676e');
assert.equal(e.bindings.noSfALuminanceOpened, true);
assert.equal(e.bindings.noCandidateThresholdOpened, true);
assert.equal(e.bindings.noTaylorJerusalemUse, true);

const expected = new Map([
  ['CRAWFORD_1947_RSPB', '10.1098/rspb.1947.0015'],
  ['SPILLMANN_NOWLAN_BERNHOLZ_1972_JOSA', '10.1364/josa.62.000177'],
  ['THOMAS_LAMB_1999_JPHYSIOL', '10.1111/j.1469-7793.1999.0479p.x'],
  ['PIANTA_KALLONIATIS_2000_JPHYSIOL', '10.1111/j.1469-7793.2000.00591.x'],
  ['RINALDUCCI_HIGGINS_CRAMER_1970_JOSA', '10.1364/josa.60.001518'],
]);
assert.equal(e.sources.length, expected.size);
for (const row of e.sources) {
  assert.equal(row.doi, expected.get(row.id), `source identity drift: ${row.id}`);
  expected.delete(row.id);
}
assert.equal(expected.size, 0);

const f = e.frozenInterpretation;
assert.equal(f.equivalentBackgroundDerivation, 'INVERT_STEADY_STATE_THRESHOLD_BACKGROUND_RELATION_FROM_ADAPTIVE_EFFECT');
assert.equal(f.localCombinationWhenHypothesisApplicable, 'REAL_LOCAL_BACKGROUND_PLUS_INFERRED_EQUIVALENT_BACKGROUND');
assert.equal(f.C4, 'PRIMARY_EQUIVALENT_BACKGROUND_PROVENANCE_CANDIDATE');
assert.equal(f.C2, 'PATH_ENVELOPE_STRUCTURAL_CONTROL_NOT_CRAWFORD_TRANSFORM');
assert.equal(f.C3, 'THRESHOLD_RATIO_STRUCTURAL_CONTROL_NOT_CLASSICAL_REAL_PLUS_EQUIVALENT_CONSTRUCTION');
assert.equal(f.astronomyOutputCanSelectWinner, false);
assert.equal(f.completePhotopicMesopicPhysiologyClaimAuthorized, false);
assert.equal(f.separateRodConeOdeAuthorized, false);
assert.equal(f.productionPromotionAuthorized, false);
assert.equal(f.pr116FinalPhysiology, false);
assert.equal(f.failClosedGuard, 'TRANSIENT_VISIBILITY_NEGATIVE_PENALTY');

console.log('SF-A Crawford/equivalent-background source-evidence contract PASS');
