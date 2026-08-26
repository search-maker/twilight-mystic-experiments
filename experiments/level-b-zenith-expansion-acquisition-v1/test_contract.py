from __future__ import annotations
import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def mod(name,path):
 s=importlib.util.spec_from_file_location(name,path); assert s and s.loader; m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
b=mod('builder',ROOT/'build_manifest.py');a=mod('adapter',ROOT/'adapter.py')
m,h=b.build(); assert m==json.loads((ROOT/'manifest.json').read_text()); assert h==json.loads((ROOT/'holdout-design.review.json').read_text());a.validate_manifest(m)
assert m['configuredPhotonHistories']==2_040_000_000 and len(m['cases'])==72 and len({c['seed'] for c in m['cases']})==72
assert [g['relativeAzimuthDeg'] for g in m['geometries'] if g['targetAltitudeDeg']==90.0 and g['role'] in a.TRAINING_ROLES]==[0.0,0.0,0.0]
assert h['execution']['authorized'] is False and h['execution']['seedsAllocated'] is False
assert max(g['parentSupportDistanceInOldCoordinates'] for g in m['geometries'] if g['role']=='boundary-training')<0.1
print('level-b zenith acquisition manifest/holdout/adapter contract: PASS')
