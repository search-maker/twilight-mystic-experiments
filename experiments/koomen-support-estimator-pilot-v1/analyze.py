#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,json,math,statistics
from pathlib import Path
ROWS=[18,22,27]; REPS=range(1,7); CASES=['baseline','profile']; OPS=['ciePhotopicQ','sqmConditionalQ']; EDGES=[1,2,3,4]; T95=2.570581835636305

def mag(q):
 if not q>0: raise RuntimeError('nonpositive q')
 return -2.5*math.log10(q)
def stat(xs):
 xs=list(map(float,xs)); m=statistics.fmean(xs); sd=statistics.stdev(xs); se=sd/math.sqrt(len(xs)); h=T95*se; return {'meanMag':m,'sdMag':sd,'seMag':se,'ci95Mag':[m-h,m+h]}
def load(root):
 f={}
 for p in root.rglob('pilot-result.json'):
  x=json.loads(p.read_text()); k=(x['row'],x['replicate'])
  if k in f: raise RuntimeError('duplicate')
  f[k]=x
 exp={(r,k) for r in ROWS for k in REPS}
 if set(f)!=exp: raise RuntimeError(f'universe mismatch {set(f)^exp}')
 return f
def q(x,method,case,di,op): return float(x['results'][method][case][di][op])
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--results-root',type=Path,required=True); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args(); a.output.mkdir(parents=True,exist_ok=True); f=load(a.results_root)
 rows=[]; all_vroom_precision=True; all_shift=True
 for row in ROWS:
  for case in CASES:
   for op in OPS:
    center_shift=[mag(q(f[(row,k)],'on',case,0,op))-mag(q(f[(row,k)],'off',case,0,op)) for k in REPS]
    cs=stat(center_shift); center_ok=(cs['ci95Mag'][0]<=0<=cs['ci95Mag'][1]) or abs(cs['meanMag'])<=0.03; all_shift &= center_ok
    rows.append({'kind':'center_method_shift','row':row,'case':case,'operator':op,'directionIndex':0,**cs,'precisionPass':None,'methodShiftPass':center_ok})
    for di in EDGES:
     off=[]; on=[]; shift=[]
     for k in REPS:
      x=f[(row,k)]
      do=mag(q(x,'off',case,di,op))-mag(q(x,'off',case,0,op)); dn=mag(q(x,'on',case,di,op))-mag(q(x,'on',case,0,op))
      off.append(do); on.append(dn); shift.append(dn-do)
     so=stat(off); sn=stat(on); ss=stat(shift); prec=sn['seMag']<=0.03; sh=(ss['ci95Mag'][0]<=0<=ss['ci95Mag'][1]) or abs(ss['meanMag'])<=0.03
     all_vroom_precision &= prec; all_shift &= sh
     rows.append({'kind':'edge_delta','row':row,'case':case,'operator':op,'directionIndex':di,'off':so,'on':sn,'methodShiftOnMinusOff':ss,'precisionPass':prec,'methodShiftPass':sh})
 classification='VROOM_NUMERICALLY_ELIGIBLE_FOR_FULL_SUPPORT_CONTINUATION' if all_vroom_precision and all_shift else 'ESTIMATOR_PILOT_INELIGIBLE'
 edges=[r for r in rows if r['kind']=='edge_delta']; centers=[r for r in rows if r['kind']=='center_method_shift']
 worst={'maxVroomEdgeSeMag':max(r['on']['seMag'] for r in edges),'maxCurrentEdgeSeMag':max(r['off']['seMag'] for r in edges),'maxAbsEdgeMethodShiftMeanMag':max(abs(r['methodShiftOnMinusOff']['meanMag']) for r in edges),'maxAbsCenterMethodShiftMeanMag':max(abs(r['meanMag']) for r in centers),'precisionFailureCount':sum(not r['precisionPass'] for r in edges),'methodShiftFailureCount':sum(not r['methodShiftPass'] for r in rows)}
 out={'schemaVersion':1,'stageId':'koomen-support-estimator-pilot-v1','executionKey':'koomen-support-estimator-pilot-v1:scientific:51','classification':classification,'decision':{'allVroomEdgeSeLe003':all_vroom_precision,'allMethodShiftGatesPass':all_shift},'worst':worst,'rows':rows,'TaylorResidualUsed':False,'historicalKoomenCorrectionComputed':False,'productionAuthorized':False}
 (a.output/'summary.json').write_text(json.dumps(out,indent=2,sort_keys=True,allow_nan=False)+'\n')
 with (a.output/'compact.csv').open('w',newline='') as fh:
  flat=[]
  for r in edges: flat.append({'row':r['row'],'case':r['case'],'operator':r['operator'],'directionIndex':r['directionIndex'],'off_mean':r['off']['meanMag'],'off_se':r['off']['seMag'],'on_mean':r['on']['meanMag'],'on_se':r['on']['seMag'],'shift_mean':r['methodShiftOnMinusOff']['meanMag'],'shift_ci_low':r['methodShiftOnMinusOff']['ci95Mag'][0],'shift_ci_high':r['methodShiftOnMinusOff']['ci95Mag'][1],'precision_pass':r['precisionPass'],'shift_pass':r['methodShiftPass']})
  w=csv.DictWriter(fh,fieldnames=list(flat[0])); w.writeheader(); w.writerows(flat)
 print(json.dumps({'classification':classification,'worst':worst},sort_keys=True))
if __name__=='__main__': main()
