import hashlib, json, math, pathlib, unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
P=ROOT/'review/aerosol-scenario-interpolation-validation-v1/protocol.review.json'
G=ROOT/'review/aerosol-scenario-interpolation-validation-v1/geometry-source.review.json'

class AerosolScenarioInterpolationValidationV1Tests(unittest.TestCase):
    def test_review_is_zero_runtime_and_unallocated(self):
        p=json.loads(P.read_text())
        a=p['authorization']
        self.assertFalse(a['scientificOrdinalRequested'])
        self.assertFalse(a['ordinal39Allocated'])
        self.assertFalse(a['scientificExecutionAuthorized'])
        self.assertFalse(a['solverExecutionAuthorized'])
        self.assertFalse(a['resultOpeningAuthorized'])
        self.assertFalse(a['productionDeploymentAuthorized'])
        self.assertFalse(a['starsvisibilityMutationAuthorized'])
    def test_geometry_source_contains_only_id_and_geometry(self):
        g=json.loads(G.read_text())
        self.assertEqual(g['geometryCount'],58)
        self.assertFalse(g['targetFieldsCopied'])
        self.assertFalse(g['sourceCasesCopied'])
        for r in g['records']:
            self.assertEqual(set(r),{'geometryId','geometry'})
    def test_selected_holdout_is_balanced_supported_and_structurally_fresh(self):
        p=json.loads(P.read_text());g=json.loads(G.read_text())
        sel=p['freshHoldoutGeometrySelection'];levels=sel['newLatticeLevels']
        pts=sel['selectedGeometries'];self.assertEqual(len(pts),8)
        def nrm(x):
            z=x['geometry'];return [(z['sunDepressionDeg']-2)/8.5,(z['targetAltitudeDeg']-5)/75,(math.cos(math.radians(z['relativeAzimuthDeg']))+1)/2,z['observerElevationM']/2500,(z['aod550']-.05)/.35]
        train=[nrm({'geometry':r['geometry']}) for r in g['records']]
        xs=[nrm(x) for x in pts]
        for j in range(5):
            for lv in levels:self.assertEqual(sum(abs(x[j]-lv)<1e-12 for x in xs),2)
        old={0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9}
        for x,pt in zip(xs,pts):
            self.assertTrue(all(all(abs(v-o)>1e-12 for o in old) for v in x))
            d=min(math.dist(x,t) for t in train)
            self.assertGreaterEqual(d,0.30);self.assertLessEqual(d,0.60)
            self.assertAlmostEqual(d,pt['nearestTrainingDistance'],places=8)
            self.assertGreater(pt['geometry']['observerElevationM'],0)
            self.assertNotIn(pt['geometry']['sunDepressionDeg'],[2,4,6,8])
            self.assertNotIn(pt['geometry']['aod550'],[0.10,0.30])
        self.assertGreaterEqual(min(math.dist(xs[i],xs[j]) for i in range(8) for j in range(i)),sel['minimumPairwiseNormalizedDistance']-1e-12)
    def test_case_cardinality_and_primary_boundary(self):
        p=json.loads(P.read_text());e=p['frozenExecutionEnvelopeIfLaterAuthorized']
        self.assertEqual(e['caseCount'],8*5*3)
        self.assertEqual(e['commonRandomNumberGroups'],8*3)
        self.assertEqual(e['configuredPhotonHistories'],e['caseCount']*e['photonHistoriesPerCase'])
        self.assertFalse(p['predictionTarget']['fullSpectrumInterpolationPrimaryGate'])
        self.assertFalse(p['holdoutEvaluationDefinitionOfDone']['spectralDiagnostics']['spectralPassClaimAuthorizedByThisExperiment'])
        self.assertFalse(e['githubRerunRetryResumeAllowed'])
    def test_gates_are_fixed_before_holdout(self):
        p=json.loads(P.read_text())
        t=p['trainingOnlyInterpolatorSelection']['trainingEligibilityGates']
        h=p['holdoutEvaluationDefinitionOfDone']
        self.assertEqual(t['aggregateMeanAbsoluteLogContrastErrorMax'],0.12)
        self.assertEqual(h['aggregateMeanAbsoluteLogContrastErrorMax'],0.15)
        self.assertEqual(h['worstAbsoluteLogContrastErrorMax'],0.50)
        self.assertFalse(h['postResultThresholdChangePermitted'])
        self.assertFalse(h['pValuesPermitted']);self.assertFalse(h['confidenceIntervalsPermitted'])

if __name__=='__main__': unittest.main()
