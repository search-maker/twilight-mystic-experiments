#!/usr/bin/env python3
"""P1 first-visibility RAW-event admission gate, v0.1; stdlib only.
Synthetic selftests are not observational validation and cannot score model error."""
import argparse
import datetime as dt
import json
from pathlib import Path
UTC = dt.timezone.utc
def instant(s):
    if not isinstance(s,str) or not s.endswith('Z'):
        raise ValueError('timestamp must be UTC Z')
    return dt.datetime.fromisoformat(s.replace('Z','+00:00')).astimezone(UTC)
def check_record(r, registration):
    fail=[]
    required=['event_id','observer_token','site_token','target_catalog_id','v_mag',
        'visual_mode','consent_verified','site_permission_verified','prediction_blinded',
        'clock_error_sec','adaptation_started_utc','site','pointing','conditions',
        'checks','raw_record_uri','raw_sha256']
    for key in required:
        if key not in r: fail.append('MISSING_'+key.upper())
    if fail: return {'event_id':r.get('event_id'),'raw_admissible':False,
        'first_onset_bracket':None,'reasons':fail,'model_error_seconds':None}
    if r['visual_mode']!='NAKED_EYE': fail.append('OPTICAL_AID_NOT_HUMAN_UNAIDED')
    for key in ('consent_verified','site_permission_verified','prediction_blinded'):
        if r[key] is not True: fail.append(key.upper()+'_NOT_TRUE')
    if not isinstance(r['raw_sha256'],str) or len(r['raw_sha256'])!=64 or any(x not in '0123456789abcdef' for x in r['raw_sha256']):
        fail.append('INVALID_RAW_SHA256')
    if not isinstance(r['raw_record_uri'],str) or not r['raw_record_uri']:
        fail.append('NO_RAW_RECORD_URI')
    if not isinstance(r['clock_error_sec'],(int,float)) or not (0<=r['clock_error_sec']<=5):
        fail.append('CLOCK_ERROR_EXCEEDS_5_SECONDS')
    site=r.get('site',{})
    for k in ('lat_deg','lon_deg','elevation_m','horizon_target_deg','coordinate_uncertainty_m'):
        if not isinstance(site.get(k),(float,int)): fail.append('MISSING_SITE_'+k.upper())
    p=r.get('pointing',{})
    for k in ('star_alt_deg','star_az_deg','solar_depression_deg','ephemeris_id','catalog_revision'):
        if p.get(k) is None: fail.append('MISSING_POINTING_'+k.upper())
    env=r.get('conditions',{})
    if env.get('target_cloud')!='CLEAR': fail.append('TARGET_CLOUD_NOT_CERTIFIED_CLEAR')
    for k in ('aod550','aod_source_uri','aod_quality_flag','skyglow_measurements'):
        if k not in env: fail.append('MISSING_CONDITIONS_'+k.upper())
    checks=r.get('checks'); bracket=None
    if not isinstance(checks,list) or not checks: fail.append('NO_SEQUENTIAL_CHECKS')
    else:
        try:
            events=[(instant(e['utc']),e['state'],e['visual_aid']) for e in checks]
            if events!=sorted(events,key=lambda x:x[0]): fail.append('CHECKS_NOT_CHRONOLOGICAL')
            if any(aid!='NONE' for _,_,aid in events): fail.append('AID_IN_CHECK_SEQUENCE')
            if any(state not in ('NO','YES','CONFIRM') for _,state,_ in events): fail.append('INVALID_CHECK_STATE')
            first_yes=next((i for i,(_,s,_) in enumerate(events) if s=='YES'),None)
            if first_yes is None: fail.append('RIGHT_CENSORED_NO_YES')
            else:
                last_no=next((i for i in range(first_yes-1,-1,-1) if events[i][1]=='NO'),None)
                if last_no is None: fail.append('LEFT_CENSORED_NO_PRIOR_NO')
                else:
                    a,b=events[last_no][0],events[first_yes][0]
                    width=(b-a).total_seconds()
                    if width<=0 or width>60: fail.append('ONSET_BRACKET_WIDTH_NOT_0_TO_60_SECONDS')
                    else: bracket={'last_no_utc':a.isoformat().replace('+00:00','Z'),
                        'first_yes_utc':b.isoformat().replace('+00:00','Z'),
                        'width_seconds':width}
                if first_yes+1>=len(events) or events[first_yes+1][1]!='CONFIRM' or (events[first_yes+1][0]-events[first_yes][0]).total_seconds()>60:
                    fail.append('FIRST_YES_NOT_CONFIRMED_WITHIN_60_SECONDS')
        except (ValueError,TypeError,KeyError) as exc:
            fail.append('INVALID_CHECK_FORMAT_'+type(exc).__name__)
    try:
        first_t=instant(r['checks'][0]['utc'])
        if (first_t-instant(r['adaptation_started_utc'])).total_seconds()<600:
            fail.append('ADAPTATION_LT_600_SECONDS')
    except (ValueError,TypeError,IndexError,KeyError):
        fail.append('MISSING_VALID_ADAPTATION_TIME')
    raw_ok=not fail
    if raw_ok and (env.get('aod550') is None or not env.get('aod_source_uri') or env.get('aod_quality_flag')!='VERIFIED'):
        fail.append('OBSERVATION_ONLY_AOD_UNVERIFIED')
    if raw_ok and not registration.get('freeze_complete'):
        fail.append('PROSPECTIVE_PREDICTION_NOT_FROZEN')
    return {'event_id':r['event_id'],'raw_admissible':raw_ok,
        'first_onset_bracket':bracket if raw_ok else None,
        'reasons':fail,'model_error_seconds':None}
def selftest():
    base={'event_id':'SYNTHETIC_DO_NOT_ADMIT','observer_token':'test-o',
        'site_token':'test-s','target_catalog_id':'HIP-00000','v_mag':4.8,
        'visual_mode':'NAKED_EYE','consent_verified':True,'site_permission_verified':True,
        'prediction_blinded':True,'clock_error_sec':1,
        'adaptation_started_utc':'2026-12-01T22:00:00Z',
        'site':{'lat_deg':40.6,'lon_deg':-73.9,'elevation_m':10,
            'horizon_target_deg':2,'coordinate_uncertainty_m':20},
        'pointing':{'star_alt_deg':45,'star_az_deg':170,'solar_depression_deg':12,
            'ephemeris_id':'synthetic','catalog_revision':'synthetic'},
        'conditions':{'target_cloud':'CLEAR','aod550':None,'aod_source_uri':None,
            'aod_quality_flag':'UNKNOWN','skyglow_measurements':[]},
        'checks':[{'utc':'2026-12-01T22:12:00Z','state':'NO','visual_aid':'NONE'},
                  {'utc':'2026-12-01T22:12:30Z','state':'YES','visual_aid':'NONE'},
                  {'utc':'2026-12-01T22:12:50Z','state':'CONFIRM','visual_aid':'NONE'}],
        'raw_record_uri':'synthetic://never-upload','raw_sha256':'0'*64}
    x=check_record(base,{'freeze_complete':False})
    assert x['raw_admissible'] and x['first_onset_bracket']['width_seconds']==30
    assert 'OBSERVATION_ONLY_AOD_UNVERIFIED' in x['reasons']
    assert 'PROSPECTIVE_PREDICTION_NOT_FROZEN' in x['reasons']
    assert x['model_error_seconds'] is None
    import copy
    y=copy.deepcopy(base);y['checks'][0]['utc']='2026-12-01T22:09:00Z'
    assert not check_record(y,{'freeze_complete':False})['raw_admissible']
    z=copy.deepcopy(base);z['visual_mode']='BINOCULARS'
    assert not check_record(z,{'freeze_complete':False})['raw_admissible']
    q=copy.deepcopy(base);q['checks']=q['checks'][1:]
    assert 'LEFT_CENSORED_NO_PRIOR_NO' in check_record(q,{'freeze_complete':False})['reasons']
    v=copy.deepcopy(base);v['prediction_blinded']=False
    assert not check_record(v,{'freeze_complete':False})['raw_admissible']
    w=copy.deepcopy(base);w['conditions']['target_cloud']='UNKNOWN'
    assert not check_record(w,{'freeze_complete':False})['raw_admissible']
    print('6/6 synthetic admission tests PASS; 0 empirical observations; no model predictions.')
def main():
    p=argparse.ArgumentParser()
    p.add_argument('--selftest',action='store_true')
    p.add_argument('--events')
    p.add_argument('--registration')
    a=p.parse_args()
    if a.selftest: selftest();return
    if not a.events or not a.registration: p.error('provide --events JSON array and --registration JSON')
    rows=json.loads(Path(a.events).read_text(encoding='utf-8'))
    reg=json.loads(Path(a.registration).read_text(encoding='utf-8'))
    if not isinstance(rows,list): p.error('events must be a JSON array')
    print(json.dumps({'records':len(rows),'admissions':[check_record(r,reg) for r in rows]},indent=2))
if __name__=='__main__': main()
