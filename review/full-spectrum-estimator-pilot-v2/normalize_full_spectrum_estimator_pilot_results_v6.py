#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, importlib.util, json, math, re, zipfile
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parent
CORE=ROOT/'build_full_spectrum_training_handoff.py'
spec=importlib.util.spec_from_file_location('full_core',CORE)
if spec is None or spec.loader is None: raise RuntimeError('cannot load integration core')
core=importlib.util.module_from_spec(spec); spec.loader.exec_module(core)

EVIDENCE_ID='public-tier1-full-spectrum-estimator-pilot-normalized-evidence-v6'
ACQ_ID='public-tier1-full-spectrum-estimator-pilot-acquisition-manifest-v4'
EXEC_ID='public-tier1-full-spectrum-estimator-pilot-execution-manifest-v4'
PROTOCOL_SHA='7ca0923204452ab203249dfd060dd5fef5465c48a20ba529c0a20748e0152434'
EXEC_SHA='be81c717cd943415ac51dc2b5356010b3d584b5279228c525d2defccc4680e0f'
GRID_SHA='488f6bd90c35a6f5aeffe1ef230186ae87002d42747af4fe94f07d82c5eef692'
RUNTIME={
 'uvspecSha256':'2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3',
 'uvspecHelpSha256':'868aea5af762d968f6f62c4e1472916d25232ed9cab5be112d753b0823d20548',
 'libRadtranDataTreeSha256':'ad30b49177e9c84e46497d69faf0c75e466996b0d0003f1de210289ae9f847d7',
 'atmosphereSha256':'dab26290ed81c762ed0c607e5dc2d53393c1462a0c3a528bc5e3f5935191cfb5',
 'runtimeLockRawSha256':'3b5fbec964642b04c73a6423b3355dbcc4ba5e84f9614f6d74420491bacc20c5',
}

PHYSICAL_FINGERPRINTS={
 'train-0009':'24c39466a3456496f67289375518a54fd04304734bad9c3165726970d717ca4f',
 'train-0013':'7a6a6c8279c8c156269dfee3ada413e429365b74eb349412276711518e65d71f',
 'train-0014':'5eab27f6bad59ba4acfd9bcb98e357794b21fbc4de116e0f3747a663bedffd0f',
 'train-0023':'947c463c889dede14f99ec2b3335e1be529aabc73c14a487c3dfb6e048c28e29',
 'train-0031':'25440d4a3c6c26cfa343fbffa330075280c2a4372a197f7e24ea71101bb01944',
 'train-0037':'fb0a9c81afe1043f8552d468d111c218cfd431af0d29095f3c2d15a3cbea41d5',
 'train-0039':'ec413d514a4a16aeabf45f0bd75b701569cda57e0abe2394679ac77c5f539975',
 'train-0041':'e1fae07492864857da6f10f8f3d09a8385ef6a2a6b161bfe23d645da1514aa19',
 'train-0047':'f7012c6295b656fe024e16769b046088baf2e36590243dce1bd953ce1c2d3d95',
}
PHYSICAL_AUDIT_SHA='91f903d7e6ee411489fa8d72a28d5e8a4adac1a82cbf2a4aff06bf0e2424136b'
PHYSICAL_KEYS={'data_files_path','atmosphere_file','source','mol_abs_param','wavelength','sza','phi0','albedo','aerosol_default','aerosol_set_tau_at_wvl','atm_z_grid','rte_solver','mc_spherical','mc_photons','mc_std','zout','umu','phi'}

def physical_fingerprint(raw:bytes)->str:
 lines=[]
 for line in raw.decode('utf-8').splitlines():
  p=line.split()
  if not p or p[0] not in PHYSICAL_KEYS: continue
  k=p[0]
  if k=='data_files_path': line='data_files_path libRadtran/data'
  elif k=='atmosphere_file': line='atmosphere_file atmmod/afglus.dat'
  elif k=='source' and len(p)>=3 and p[1]=='solar': line='source solar solar_flux/atlas_plus_modtran'
  lines.append(line)
 return hashlib.sha256(('\n'.join(lines)+'\n').encode('utf-8')).hexdigest()


DIRECTIVE_SEQUENCE_ALIS=(
 'data_files_path','atmosphere_file','source','mol_abs_param','wavelength','sza','phi0',
 'rte_solver','mc_spherical','mc_photons','mc_vroom','mc_std','mc_randomseed','mc_basename',
 'mc_spectral_is','albedo','aerosol_default','aerosol_set_tau_at_wvl','atm_z_grid','zout','umu','phi','quiet',
)
DIRECTIVE_SEQUENCE_VROOM=(
 'data_files_path','atmosphere_file','source','mol_abs_param','wavelength_grid_file','wavelength','sza','phi0',
 'rte_solver','mc_spherical','mc_photons','mc_vroom','mc_std','mc_randomseed','mc_basename',
 'albedo','aerosol_default','aerosol_set_tau_at_wvl','atm_z_grid','zout','umu','phi','quiet',
)

def verify_exact_directive_surface(raw:bytes,case:dict[str,Any])->None:
 keys=[]
 for line in raw.decode('utf-8').splitlines():
  stripped=line.strip()
  if not stripped or stripped.startswith('#'): continue
  p=stripped.split()
  if not p: continue
  keys.append(p[0])
 expected=DIRECTIVE_SEQUENCE_ALIS if case['method']=='alis-alt-importance' else DIRECTIVE_SEQUENCE_VROOM if case['method']=='reference-vroom-1nm' else None
 if expected is None: raise ValueError('unknown method for directive surface')
 if tuple(keys)!=expected:
  extra=[]; missing=[]
  from collections import Counter
  gotc=Counter(keys); wantc=Counter(expected)
  for k,n in sorted((gotc-wantc).items()): extra.extend([k]*n)
  for k,n in sorted((wantc-gotc).items()): missing.extend([k]*n)
  raise ValueError(f'exact input directive surface drift: extra={extra} missing={missing} got={keys}')

def canon(v:Any)->str: return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def raw_sha(b:bytes)->str: return hashlib.sha256(b).hexdigest()
def load(p:Path)->dict[str,Any]:
 v=json.loads(p.read_text());
 if not isinstance(v,dict): raise ValueError(f'expected object: {p}')
 return v

def find_one(names:list[str],suffix:str)->str:
 m=[n for n in names if n.endswith(suffix)]
 if len(m)!=1: raise ValueError(f'expected exactly one {suffix}, got {m}')
 return m[0]

def parse_spectrum(raw:bytes,node_count:int,step:float)->tuple[list[float],list[float]]:
 wl=[]; rad=[]
 for line in raw.decode('utf-8').splitlines():
  p=line.split()
  if len(p)<2: continue
  try: w=float(p[0]); x=float(p[-1])
  except ValueError: continue
  if not math.isfinite(w) or not math.isfinite(x) or x<0: raise ValueError('spectrum contains invalid number')
  wl.append(w); rad.append(x)
 if len(wl)!=node_count or abs(wl[0]-380)>1e-8 or abs(wl[-1]-780)>1e-8: raise ValueError(f'output grid mismatch: {len(wl)}')
 for i in range(len(wl)-1):
  if abs((wl[i+1]-wl[i])-step)>1e-7: raise ValueError('output grid step mismatch')
 return wl,rad

def channels(wl:list[float],rad:list[float])->dict[str,float]:
 return {
  'photopicLuminanceCdM2':core.trap_weighted(wl,rad,lambda x:core.interp(core.V_PHOT,x),core.KM_PHOTOPIC),
  'scotopicLuminanceScotCdM2':core.trap_weighted(wl,rad,lambda x:core.interp(core.V_SCOT,x),core.KM_SCOTOPIC),
  'johnsonVEffectiveRadiance_mW_m2_nm_sr':core.johnson_effective(wl,rad),
 }

def parse_directives(raw:bytes)->dict[str,Any]:
 lines=raw.decode('utf-8').splitlines(); out={'hasMcStd':False,'hasAerosolDefault':False,'forbidden':[]}
 for line in lines:
  p=line.split()
  if not p: continue
  k=p[0]
  if k in {'altitude','mc_elevation_file'}: out['forbidden'].append(k)
  if k=='data_files_path': out['dataFilesPath']=p[1]
  elif k=='atmosphere_file': out['atmosphereFile']=p[1]
  elif k=='source' and len(p)>=3 and p[1]=='solar': out['solarFlux']=p[2]
  elif k=='mol_abs_param': out['molAbs']=p[1]
  elif k=='wavelength': out['wavelength']=[float(p[1]),float(p[2])]
  elif k=='wavelength_grid_file': out['wavelengthGridFile']=p[1]
  elif k=='sza': out['sunDepressionDeg']=float(p[1])-90.0
  elif k=='phi0': out['phi0']=float(p[1])
  elif k=='rte_solver': out['rteSolver']=p[1]
  elif k=='mc_spherical': out['mcSpherical']=p[1]
  elif k=='mc_photons': out['mcPhotons']=int(p[1])
  elif k=='mc_vroom': out['mcVroom']=p[1]
  elif k=='mc_std': out['hasMcStd']=True
  elif k=='mc_randomseed': out['seed']=int(p[1])
  elif k=='mc_spectral_is': out['mcSpectralIsNm']=float(p[1])
  elif k=='albedo': out['albedo']=float(p[1])
  elif k=='aerosol_default': out['hasAerosolDefault']=True
  elif k=='aerosol_set_tau_at_wvl' and float(p[1])==550.0: out['aod550']=float(p[2])
  elif k=='atm_z_grid': out['atmZGridKm']=[float(x) for x in p[1:]]
  elif k=='zout': out['zoutKm']=float(p[1])
  elif k=='umu': out['umu']=float(p[1])
  elif k=='phi': out['relativeAzimuthDeg']=float(p[1])
 return out

def close(a:float,b:float,tol:float=2e-6)->bool: return abs(float(a)-float(b))<=tol

def verify_input(d:dict[str,Any],case:dict[str,Any])->None:
 g=case['physicalInputs']; m=case['numericalMethod']
 if d['forbidden']: raise ValueError(f'forbidden physical directive: {d["forbidden"]}')
 if not str(d.get('dataFilesPath','')).endswith('/share/libRadtran/data'): raise ValueError('wrong data_files_path')
 if not str(d.get('atmosphereFile','')).endswith('/atmmod/afglus.dat'): raise ValueError('wrong atmosphere file')
 if not str(d.get('solarFlux','')).endswith('/solar_flux/atlas_plus_modtran'): raise ValueError('wrong solar source')
 if d.get('molAbs')!='crs' or d.get('wavelength')!=[380.0,780.0] or d.get('rteSolver')!='mystic' or d.get('mcSpherical')!='1D' or not d.get('hasMcStd') or not d.get('hasAerosolDefault'): raise ValueError('common numerical/atmosphere directive drift')
 if d.get('mcPhotons')!=case['photonHistories'] or d.get('seed')!=case['seed']: raise ValueError('seed/photon drift')
 for got,want,label in [(d.get('sunDepressionDeg'),g['sunDepressionDeg'],'sun'),(d.get('albedo'),g['albedo'],'albedo'),(d.get('aod550'),g['aod550'],'aod'),(d.get('relativeAzimuthDeg'),g['relativeAzimuthDeg'],'azimuth')]:
  if got is None or not close(got,want,3e-6): raise ValueError(f'{label} drift')
 if d.get('phi0')!=0.0 or d.get('zoutKm')!=0.0: raise ValueError('phi0/zout drift')
 grid=d.get('atmZGridKm');
 if not isinstance(grid,list) or not grid or not close(grid[0],g['observerElevationM']/1000.0,3e-6) or any(grid[i+1]<=grid[i] for i in range(len(grid)-1)): raise ValueError('atm_z_grid drift')
 want_umu=-math.sin(math.radians(g['targetAltitudeDeg']))
 if d.get('umu') is None or not close(d['umu'],want_umu,2e-7): raise ValueError('target altitude/umu drift')
 if case['method']=='alis-alt-importance':
  if d.get('mcVroom')!='off' or not close(d.get('mcSpectralIsNm'),m['mc_spectral_is_nm'],1e-9) or 'wavelengthGridFile' in d: raise ValueError('ALIS numerical method drift')
 elif case['method']=='reference-vroom-1nm':
  if d.get('mcVroom')!='on' or 'mcSpectralIsNm' in d or 'wavelengthGridFile' not in d: raise ValueError('VROOM numerical method drift')
 else: raise ValueError('unknown method')

def verify_runtime(r:dict[str,Any])->None:
 for k,want in RUNTIME.items():
  if r.get(k)!=want: raise ValueError(f'runtime identity drift: {k}')

def parse_case_zip(path:Path,expected:dict[str,Any],required_members:list[str])->dict[str,Any]:
 zbytes=path.read_bytes()
 with zipfile.ZipFile(path) as z:
  file_names=[n for n in z.namelist() if not n.endswith('/')]
  by_base:dict[str,str]={}
  for name in file_names:
   base=Path(name).name
   if base in by_base: raise ValueError(f'duplicate artifact member basename: {base}')
   by_base[base]=name
  required=list(required_members)
  if len(required)!=len(set(required)): raise ValueError('manifest required member basename duplicated')
  if set(by_base)!=set(required) or len(by_base)!=len(required):
   missing=sorted(set(required)-set(by_base)); extra=sorted(set(by_base)-set(required))
   raise ValueError(f'exact artifact member set mismatch: missing={missing} extra={extra}')
  raw_by_base={base:z.read(name) for base,name in by_base.items()}
 result_raw=raw_by_base['case-result.json']; input_raw=raw_by_base['input-resolved.txt']; runtime_raw=raw_by_base['runtime-report.json']; rad_raw=raw_by_base['mc.rad.spc']; std_raw=raw_by_base['mc.rad.std.spc']
 result=json.loads(result_raw); runtime=json.loads(runtime_raw); prepared=json.loads(raw_by_base['prepared.json'])
 if result.get('schemaVersion')!=1 or result.get('stageId')!='full-spectrum-estimator-pilot-v2' or result.get('status')!='COMPLETED' or result.get('caseId')!=expected['caseId']: raise ValueError('case-result identity/status mismatch')
 execution_fields={
  'workflowRunAttempt':1,'syntaxCheckCount':1,'solverExecutionCount':1,
  'retryPerformed':False,'resumePerformed':False,'githubRerun':False,
  'syntaxExitCode':0,'solverExitCode':0,'syntaxTimedOut':False,'solverTimedOut':False,
 }
 stale={k:(result.get(k),v) for k,v in execution_fields.items() if result.get(k)!=v}
 if stale: raise ValueError(f'case-result execution contract mismatch: {stale}')
 if result.get('seed')!=expected['seed'] or result.get('photonHistories')!=expected['photonHistories']: raise ValueError('case-result seed/photon mismatch')
 supplied=result.get('contentSha256'); core_result={k:v for k,v in result.items() if k!='contentSha256'}
 if supplied!=canon(core_result): raise ValueError('case-result self-hash mismatch')
 raw_member_hashes={base:raw_sha(raw) for base,raw in raw_by_base.items() if base!='case-result.json'}
 if result.get('rawMemberSha256ByBasename')!=raw_member_hashes: raise ValueError('case-result exact raw-member SHA-256 map mismatch')
 if int(raw_by_base['randomseed'].decode('utf-8').strip())!=expected['seed']: raise ValueError('randomseed file does not equal manifest seed')
 hashes={'inputResolvedSha256':raw_sha(input_raw),'runtimeReportRawSha256':raw_sha(runtime_raw),'radianceOutputSha256':raw_sha(rad_raw),'stdRadianceOutputSha256':raw_sha(std_raw)}
 for k,v in hashes.items():
  if result.get(k)!=v: raise ValueError(f'case-result member hash mismatch: {k}')
 prepared_expected={
  'schemaVersion':1,'stageId':'full-spectrum-estimator-pilot-v2-prepared','caseId':expected['caseId'],'geometryId':expected['geometryId'],
  'method':expected['method'],'replicate':expected['replicate'],'seed':expected['seed'],'photonHistories':expected['photonHistories'],
  'inputResolvedSha256':hashes['inputResolvedSha256'],'executionManifestSha256':EXEC_SHA,
 }
 stale_prepared={k:(prepared.get(k),v) for k,v in prepared_expected.items() if prepared.get(k)!=v}
 if stale_prepared: raise ValueError(f'prepared-record binding mismatch: {stale_prepared}')
 verify_runtime(runtime); verify_exact_directive_surface(input_raw,expected); directives=parse_directives(input_raw); verify_input(directives,expected)
 fp=physical_fingerprint(input_raw); want_fp=PHYSICAL_FINGERPRINTS.get(expected['geometryId'])
 if want_fp is None or fp!=want_fp: raise ValueError(f'historical physical-input fingerprint drift: {expected["geometryId"]} {fp}')
 if expected['method']=='reference-vroom-1nm':
  if raw_sha(raw_by_base['wavelength-grid-1nm.dat'])!=GRID_SHA: raise ValueError('VROOM grid bytes drift')
  node_count=401; step=1.0
 else: node_count=8001; step=.05
 for base,raw in raw_by_base.items():
  if base not in {'syntax-stdout.txt','syntax-stderr.txt','solver-stdout.txt','solver-stderr.txt'} and len(raw)==0:
   raise ValueError(f'unexpected empty required raw member: {base}')
 wl,rad=parse_spectrum(rad_raw,node_count,step); swl,srad=parse_spectrum(std_raw,node_count,step)
 if swl!=wl: raise ValueError('std spectrum grid differs')
 ch=channels(wl,rad); zero=all(x==0.0 for x in ch.values())
 return {'caseId':expected['caseId'],'geometryId':expected['geometryId'],'method':expected['method'],'importanceCenterNm':expected['numericalMethod'].get('mc_spectral_is_nm'),'replicate':expected['replicate'],'seed':expected['seed'],'photonHistories':expected['photonHistories'],'channels':ch,'zeroHit':zero,'zipSha256':raw_sha(zbytes),'caseResultSha256':raw_sha(result_raw),'inputResolvedSha256':hashes['inputResolvedSha256'],'runtimeReportSha256':hashes['runtimeReportRawSha256'],'radianceSha256':hashes['radianceOutputSha256'],'stdRadianceSha256':hashes['stdRadianceOutputSha256'],'rawMemberSha256ByBasename':raw_member_hashes}

def normalize(exec_manifest:dict[str,Any],acq:dict[str,Any])->dict[str,Any]:
 supplied=exec_manifest.get('manifestSha256');
 if exec_manifest.get('manifestId')!=EXEC_ID or supplied!=EXEC_SHA or canon({k:v for k,v in exec_manifest.items() if k!='manifestSha256'})!=supplied: raise ValueError('execution manifest identity/self-hash mismatch')
 contract=exec_manifest.get('artifactContract',{}); limits=exec_manifest.get('executionLimits',{})
 expected_names=[f"full-spectrum-estimator-pilot-v2-case-{c['caseId']}" for c in exec_manifest.get('cases',[])]
 if contract.get('expectedArtifactNames')!=expected_names or contract.get('expectedArtifactNamesSha256')!=canon(expected_names): raise ValueError('execution manifest expected artifact universe drift')
 method_members=contract.get('requiredMembersByMethod',{})
 if not isinstance(method_members,dict) or set(method_members)!={'alis-alt-importance','reference-vroom-1nm'}: raise ValueError('method-specific artifact member contract drift')
 for method,members in method_members.items():
  if not isinstance(members,list) or len(members)!=len(set(members)) or 'case-result.json' not in members or 'prepared.json' not in members or 'randomseed' not in members: raise ValueError(f'invalid exact member contract: {method}')
 if contract.get('exactMemberBasenamesRequired') is not True or contract.get('unexpectedExtraMembersRefused') is not True or contract.get('rawMemberSha256MapRequiredForAllMembersExceptCaseResult') is not True or contract.get('randomseedFileMustEqualManifestSeed') is not True: raise ValueError('exact raw-evidence artifact contract weakened')
 wanted_limits={'workflowAttemptExactly':1,'syntaxChecksPerCaseMaximum':1,'solverExecutionsPerCaseMaximum':1,'automaticRetryCountMaximum':0,'automaticContinuation':False,'artifactMustBeEmittedForTerminalCaseOutcome':True,'all44CasesMustReachTerminalArtifactBeforeNormalization':True}
 if any(limits.get(k)!=v for k,v in wanted_limits.items()): raise ValueError('execution limits drift')
 if acq.get('schemaVersion')!=1 or acq.get('manifestId')!=ACQ_ID or acq.get('protocolSha256')!=PROTOCOL_SHA or acq.get('executionManifestSha256')!=EXEC_SHA: raise ValueError('acquisition identity mismatch')
 a_sup=acq.get('manifestSha256');
 if a_sup!=canon({k:v for k,v in acq.items() if k!='manifestSha256'}): raise ValueError('acquisition self-hash mismatch')
 rows=acq.get('artifacts')
 if acq.get('partial') is not False or not isinstance(rows,list) or len(rows)!=44 or acq.get('observedArtifactCount')!=44: raise ValueError('complete exact 44-artifact acquisition required')
 exp={c['caseId']:c for c in exec_manifest['cases']}; seen=set(); evidence=[]
 for a in rows:
  cid=a.get('caseId')
  if cid not in exp or cid in seen: raise ValueError('unexpected/duplicate acquisition case')
  seen.add(cid)
  if not isinstance(a.get('artifactId'),int) or a['artifactId']<=0 or not isinstance(a.get('artifactName'),str): raise ValueError('invalid artifact metadata')
  if a['artifactName']!=f'full-spectrum-estimator-pilot-v2-case-{cid}': raise ValueError('artifact name mismatch')
  digest=a.get('githubZipDigest'); path=Path(a.get('localZipPath',''))
  if not isinstance(digest,str) or not digest.startswith('sha256:') or not path.is_file(): raise ValueError('transport binding incomplete')
  if a.get('downloadedZipSha256')!=digest.removeprefix('sha256:') or raw_sha(path.read_bytes())!=a['downloadedZipSha256'] or a.get('bytesOpenedAfterTransportBinding') is not True: raise ValueError('ZIP digest/transport order mismatch')
  required=method_members.get(exp[cid]['method']); ev=parse_case_zip(path,exp[cid],required); evidence.append(ev)
 if seen!=set(exp): raise ValueError('acquisition does not cover exact pilot universe')
 evidence.sort(key=lambda x:x['caseId'])
 out={'schemaVersion':1,'evidenceId':EVIDENCE_ID,'status':'COMPLETE_NORMALIZED_PILOT_EVIDENCE','protocolSha256':PROTOCOL_SHA,'executionManifestSha256':EXEC_SHA,'physicalInputAuditRawSha256':PHYSICAL_AUDIT_SHA,'acquisitionManifestSha256':a_sup,'caseCount':44,'holdoutValuesRead':False,'modelFittingAuthorized':False,'productionAuthorization':False,'cases':evidence}
 out['evidenceSha256']=canon(out); return out

def main()->int:
 ap=argparse.ArgumentParser(); ap.add_argument('--execution-manifest',type=Path,required=True); ap.add_argument('--acquisition-manifest',type=Path,required=True); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
 try:
  v=normalize(load(a.execution_manifest),load(a.acquisition_manifest)); a.output.write_text(json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+'\n'); print(json.dumps({'status':v['status'],'caseCount':v['caseCount'],'evidenceSha256':v['evidenceSha256']},indent=2)); return 0
 except Exception as e: print(json.dumps({'status':'REFUSED','reason':str(e)},indent=2)); return 2
if __name__=='__main__': raise SystemExit(main())
