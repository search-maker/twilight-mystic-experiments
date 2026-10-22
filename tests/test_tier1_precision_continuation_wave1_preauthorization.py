import hashlib, importlib.util, json, tempfile, unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location("m",Path(__file__).parents[1]/"experiments"/"tier1-precision-continuation-wave1-v2"/"preauthorization_review.py"); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
def write(p,v): p.write_text(json.dumps(v,sort_keys=True)+"\n"); return hashlib.sha256(p.read_bytes()).hexdigest()
def prereg():
 c=[]
 for i in range(20):
  role="internal-holdout" if i>=17 else "surrogate-training"
  for b in (3,4): c.append({"caseId":f"g{i}-b{b}","groupId":f"g{i}","block":b,"seed":1000+len(c),"role":role,"photonHistories":100_000_000,"proposalOnly":True})
 c[-1]["photonHistories"]=1_200_000_000
 return {"authorizationEnabled":False,"authorizationOrdinal":None,"authorizationRef":None,"executionKey":None,"dispatchEnabled":False,"workflowDispatchEnabled":False,"scientificExecution":False,"proposalOnly":True,"blocks":[3,4],"caseCount":40,"geometryCount":20,"maximumConfiguredPhotonHistories":5_100_000_000,"roleCounts":{"internalHoldoutCases":6,"internalHoldoutGeometries":3,"surrogateTrainingCases":34,"surrogateTrainingGeometries":17},"preservation":{k:True for k in ("evidenceBindingsUnchanged","geometryInputsUnchanged","historicalArtifactsImmutable","originalBlocksB1B2Preserved","photonScheduleUnchanged","rolesUnchanged","thresholdsUnchanged","zeroHitHandlingUnchanged")},"seedProof":{"allWave1SeedsUnique":True,"historicalOverlap":[],"historicalSeedCount":196,"wave1SeedCount":40},"cases":c}
def template(): return {"enabled":False,"dispatch":False,"automaticDispatch":False,"workflowDispatchEnabled":False,"solverExecutionAuthorized":False,"githubRerunAllowed":False,"authorizationOrdinal":None,"authorizationRef":None,"authorizationCommit":None,"executionKey":None}
def snapshot(): return {"status":"REVIEW_ONLY_SNAPSHOT","candidateIdentity":m.CANDIDATE,"checkedDimensions":sorted(m.DIMS),"findings":{"globalOrdinalCollisions":[{"authorizationOrdinal":3,"pullRequest":26}],"tier1ExecutionKeyCollisions":[],"authorizationRefCollisions":[],"runTitleCollisions":[],"branchPathCollisions":[],"authorizationFilePathCollisions":[],"wave1SeedCollisions":[]},"sources":[]}
class T(unittest.TestCase):
 def run_build(self,pm=None,tm=None,sm=None):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d); p=prereg(); t=template(); s=snapshot(); pm and pm(p); tm and tm(t); sm and sm(s)
   pp=r/"p"; tp=r/"t"; sp=r/"s"; ph=write(pp,p); th=write(tp,t); write(sp,s)
   return m.build(pp,tp,sp,ph,th)
 def test_blocked_packet(self):
  x=self.run_build(); self.assertEqual(x["status"],"BLOCKED_GLOBAL_ORDINAL_COLLISION_REVIEW_ONLY"); self.assertEqual(len(x["wave1Seeds"]),40); self.assertIsNone(x["authoritativeIdentity"]["authorizationOrdinal"])
 def test_missing_collision_refuses(self):
  with self.assertRaisesRegex(m.Refusal,"collision evidence"): self.run_build(sm=lambda s:s["findings"].update(globalOrdinalCollisions=[]))
 def test_duplicate_seed_refuses(self):
  with self.assertRaisesRegex(m.Refusal,"case/seed universe"): self.run_build(pm=lambda p:p["cases"][1].update(seed=p["cases"][0]["seed"]))
 def test_open_template_refuses(self):
  with self.assertRaisesRegex(m.Refusal,"boundary opened"): self.run_build(tm=lambda t:t.update(enabled=True))
if __name__=="__main__": unittest.main()
