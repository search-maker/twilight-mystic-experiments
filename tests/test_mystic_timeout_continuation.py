from __future__ import annotations
import importlib.util,json,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];PKG=ROOT/"experiments/mystic-batch-v1"
def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);assert s and s.loader;m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
adapter=module("a",PKG/"cross_geometry_confirmation_timeout_execution_adapter.py");plan=module("p",PKG/"cross_geometry_confirmation_timeout_execution_plan.py");source=module("s",PKG/"cross_geometry_confirmation_timeout_source_audit.py")
class Tests(unittest.TestCase):
 def test_static_proposal(self):
  m=json.loads((PKG/"cross-geometry-confirmation-timeout-continuation.proposal.json").read_text());adapter.validate_manifest(m);self.assertEqual(len(m["cases"]),8);self.assertEqual(sum(c["photonHistories"] for c in m["cases"]),1600000000);self.assertFalse({c["seed"] for c in m["cases"]}&{82501,82502,82503,82504});self.assertTrue(all(c["photonHistories"]==200000000 for c in m["cases"]))
 def test_plan(self):
  with tempfile.TemporaryDirectory() as t:
   r=Path(t);mp=r/"m.json";mp.write_text((PKG/"cross-geometry-confirmation-timeout-continuation.proposal.json").read_text());import hashlib;gp=r/"g.json";gp.write_text(json.dumps({"status":"AUTHORIZED","stageId":adapter.STAGE_ID,"manifestRawSha256":hashlib.sha256(mp.read_bytes()).hexdigest(),"executionAdapterRawSha256":"a"*64,"runtimeLockRawSha256":"b"*64,"executionWorkflowRawSha256":"c"*64,"authorizationRef":"d"*40,"authorizationOrdinal":6,"executionKey":adapter.STAGE_ID+":screening:6"}));p=plan.build(mp,gp);self.assertEqual(p["caseCount"],8);self.assertEqual(p["perCaseTimeoutSeconds"],2400)
 def test_authorization_disabled(self):
  a=json.loads((PKG/"authorization.cross-geometry-timeout-continuation.json").read_text());t=json.loads((PKG/"authorization.cross-geometry-timeout-continuation-template.json").read_text());self.assertEqual(a,t);self.assertFalse(a["authorized"])
if __name__=="__main__":unittest.main()
