#!/usr/bin/env python3
"""Bounded metadata-only ESO TAP audit of Patat et al. (2006) Table 2.

NO raw science images downloaded, NO model predictions/fits, NO solver dispatch.
Use --fixtures to run a synthetic parser/selection self-test without network.
Use --live only in a permitted science work window with network access.
The journal table is not independent of the raw frames; reproducing them is
an archival re-reduction, not an independent held-out benchmark.
"""
import argparse
import datetime as dt
import json
import math
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ESO_TAP = "https://archive.eso.org/tap_obs/sync"
PAPER = "https://doi.org/10.1051/0004-6361:20064992"
TIMELIMIT = 20
MAX_QUERY = 201
MAX_RECORDS_PER_WINDOW = 200
CASES = [
    {"case":"paranal-1999-moon-down", "utc":"1999-04-16T09:54:36Z", "alt":41.1, "az":233.4, "sunDep":14.8},
    {"case":"paranal-2003-crescent-up", "utc":"2003-02-28T09:45:52Z", "alt":27.5, "az":299.3, "sunDep":11.9},
]
CORE = {"dp_id", "mjd_obs", "date_obs", "instrument", "tel_alt", "tel_az", "access_url"}
OPTIONAL = ["dp_cat","dp_type","dp_tech","exposure","prog_id","origfile","datalink_url","target","tel_ambi_pres_start","tel_ambi_rhum","tel_ambi_fwhm_start"]

def parse_utc(s):
    if not s or not isinstance(s, str):
        raise ValueError("Missing UTC timestamp")
    t = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    if t.tzinfo is None:
        t=t.replace(tzinfo=dt.timezone.utc)  # ESO archive date_obs timestamps are UTC
    return t.astimezone(dt.timezone.utc)

def mjd_from_utc(s):
    return parse_utc(s).timestamp() / 86400 + 40587

def separation_deg(a, b):
    return abs((a - b + 180) % 360 - 180)

def parse_votable(xmlbytes):
    """Parse ESO standard VOTable TABLEDATA; reject error/overflow/ambiguous tables."""
    root = ET.fromstring(xmlbytes)
    infos = [e for e in root.iter() if e.tag.rsplit('}', 1)[-1] == 'INFO' and e.attrib.get('name','').upper() == 'QUERY_STATUS']
    if not infos:
        raise ValueError("No TAP QUERY_STATUS in response")
    if any(i.attrib.get('value','').upper() != 'OK' for i in infos):
        raise ValueError("ESO TAP query status not clean: " + str([(i.attrib.get('value'),i.text) for i in infos]))
    tables = [e for e in root.iter() if e.tag.rsplit('}',1)[-1]=='TABLE']
    if len(tables) != 1:
        raise ValueError("Expected exactly one TABLE")
    table = tables[0]
    fields = [e.attrib['name'] for e in table if e.tag.rsplit('}',1)[-1]=='FIELD']
    if not fields or len(fields) != len(set(fields)):
        raise ValueError("Missing or repeated column headers")
    data = [e for e in table.iter() if e.tag.rsplit('}',1)[-1]=='TABLEDATA']
    if len(data)!=1:
        raise ValueError("TAP reply without one text TABLEDATA (binary not supported)")
    rows=[]
    for tr in data[0]:
        if tr.tag.rsplit('}',1)[-1]!='TR': continue
        cells=[(td.text or '').strip() for td in tr if td.tag.rsplit('}',1)[-1]=='TD']
        if len(cells)!=len(fields): raise ValueError("Field-count mismatch")
        rows.append(dict(zip(fields,cells)))
    return rows

def tap_query(query):
    form = urllib.parse.urlencode({"REQUEST":"doQuery","LANG":"ADQL","FORMAT":"votable","MAXREC":"500","QUERY":query}).encode('ascii')
    req = urllib.request.Request(ESO_TAP, form, headers={"Content-Type":"application/x-www-form-urlencoded","User-Agent":"Tzeit-Independent-Archival-Metadata-Audit/1.0"}, method='POST')
    with urllib.request.urlopen(req, timeout=TIMELIMIT) as r:
        if r.status!=200: raise RuntimeError("ESO TAP returned HTTP " + str(r.status))
        return parse_votable(r.read(2_000_000))

def discover_schema():
    q="SELECT column_name FROM TAP_SCHEMA.columns WHERE table_name='dbo.raw'"
    rows=tap_query(q)
    cols={r.get('column_name','').lower() for r in rows}
    absent=CORE-cols
    if absent: raise ValueError("ESO schema drift, missing required raw fields: "+repr(sorted(absent)))
    return cols

def build_query(case, available):
    mid=mjd_from_utc(case['utc'])
    # 15 minutes each side for discovery only; acceptance much tighter.
    fields=sorted(CORE)+[f for f in OPTIONAL if f in available]
    if len(fields)!=len(set(fields)): raise AssertionError("duplicate fields")
    return (f"SELECT TOP {MAX_QUERY} "+", ".join(fields)+" FROM dbo.raw WHERE "
            f"mjd_obs >= {mid-15/1440:.9f} AND mjd_obs < {mid+15/1440:.9f} "
            "AND (instrument='FORS1' OR instrument='FORS2') ORDER BY mjd_obs")

def score_row(row, case):
    try:
        when=parse_utc(row['date_obs'])
        delta_t=abs((when-parse_utc(case['utc'])).total_seconds())
        alt=float(row['tel_alt']);az=float(row['tel_az'])
    except (ValueError, TypeError, KeyError, OverflowError):
        return {"classification":"INVALID_ARCHIVE_METADATA"}
    if not all(map(math.isfinite, [delta_t,alt,az])):
        return {"classification":"INVALID_ARCHIVE_METADATA"}
    if row.get('instrument') not in ('FORS1','FORS2'):
        return {"classification":"INVALID_INSTRUMENT"}
    dalt=abs(alt-case['alt']);daz=separation_deg(az,case['az'])
    matches=(delta_t<=180 and dalt<=2 and daz<=2)
    return {"classification":"CANDIDATE_ONLY" if matches else "NON_MATCH",
            "delta_seconds":round(delta_t,3),"altitude_residual_deg":round(dalt,4),"azimuth_residual_deg":round(daz,4)}

def analyze(case,rows):
    if len(rows)>MAX_RECORDS_PER_WINDOW: raise ValueError("Truncated or excessively crowded archive window; cannot judge uniqueness")
    scored=[]
    for row in rows:
        rec={k:row.get(k) for k in sorted(set(CORE)|set(OPTIONAL)) if k in row}
        rec.update(score_row(row,case));scored.append(rec)
    accepted=[r for r in scored if r['classification']=='CANDIDATE_ONLY']
    outcome="UNIQUE_METADATA_CANDIDATE" if len(accepted)==1 else "NO_METADATA_MATCH" if not accepted else "AMBIGUOUS_METADATA_MATCH"
    return {"case":case,"status":outcome,"num_query_rows":len(rows),"num_matching_candidates":len(accepted),"matches":accepted,"raw_metadata":scored,
            "scientific_validation":"NOT_RUN","observations_downloaded":0,"sky_radiance_validation":"NOT_VALIDATED"}

def fixture_test():
    case=CASES[0]
    x={"dp_id":"FORS.1999-04-16T09:54:36.000","date_obs":"1999-04-16T09:54:36Z","instrument":"FORS1","tel_alt":"41.1","tel_az":"233.4","access_url":"https://dataportal.eso.org/example", "mjd_obs":str(mjd_from_utc(case['utc']))}
    cols=CORE|set(OPTIONAL)
    q=build_query(case,cols)
    assert "TOP 201" in q and "FORS1" in q and "mjd_obs" in q
    assert analyze(case,[x])['status']=='UNIQUE_METADATA_CANDIDATE'
    assert analyze(case,[])['status']=='NO_METADATA_MATCH'
    assert analyze(case,[x,x])['status']=='AMBIGUOUS_METADATA_MATCH'
    assert analyze(case,[dict(x,tel_alt='50')])['status']=='NO_METADATA_MATCH'
    assert analyze(case,[dict(x,date_obs='1999-04-16T10:05:00Z')])['status']=='NO_METADATA_MATCH'
    assert analyze(case,[dict(x,tel_az='235.5')])['status']=='NO_METADATA_MATCH'
    assert analyze(case,[dict(x,tel_alt='not a number')])['status']=='NO_METADATA_MATCH'
    assert analyze(case,[dict(x,instrument='UVES')])['status']=='NO_METADATA_MATCH'
    assert separation_deg(359,1)==2
    assert separation_deg(1,359)==2
    assert len(CASES)==2
    assert parse_utc('1999-04-16T09:54:36.1234')==parse_utc('1999-04-16T09:54:36.1234Z')
    assert abs(mjd_from_utc('1970-01-01T00:00:00Z')-40587)<1e-10
    assert len(CORE-{'nonexistent'})==len(CORE)
    # A tiny standards-shaped VOTable tests XML schema and error handling.
    xml=b'''<VOTABLE xmlns="http://www.ivoa.net/xml/VOTable/v1.3"><RESOURCE type="results"><INFO name="QUERY_STATUS" value="OK">OK</INFO><TABLE><FIELD name="dp_id" datatype="char" arraysize="*"/><DATA><TABLEDATA><TR><TD>a</TD></TR></TABLEDATA></DATA></TABLE></RESOURCE></VOTABLE>'''
    assert parse_votable(xml)==[{'dp_id':'a'}]
    try:
        parse_votable(xml.replace(b'value="OK"',b'value="OVERFLOW"'))
        raise AssertionError('must reject overflow')
    except ValueError as e:
        assert 'not clean' in str(e)
    print('PASS ESO_PARANAL_RAW_METADATA_FIXTURE_NO_NETWORK')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fixtures',action='store_true',help='Synthetic offline test only')
    p.add_argument('--live',action='store_true',help='Read anonymous ESO TAP raw metadata, two bounded queries; no files')
    p.add_argument('--output',default='paranal_archive_metadata_results.json')
    a=p.parse_args()
    if not a.fixtures and not a.live: p.error('Choose --fixtures or --live; never silently access external data')
    if a.fixtures: fixture_test();return
    schema=discover_schema()
    results=[]
    for case in CASES:
        q=build_query(case,schema)
        result=analyze(case,tap_query(q));result['query']=q
        results.append(result)
    payload={"created_utc":dt.datetime.now(dt.timezone.utc).isoformat(),"source":"ESO TAP dbo.raw (anonymous, instrument/time/pointing discovery)",
             "paper":PAPER,"source_table":"Patat et al 2006 Table 2 p.389","mode":"METADATA_ONLY",
             "records":results,"benchmark_acceptance":"BLOCKED_UNTIL_RAW_CALIBRATED_FRAMES_AND_MATCHED_ATMOSPHERE"}
    Path(a.output).write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print('WROTE '+a.output+'; NO raw frames downloaded; NO model validation claimed')

if __name__=='__main__': main()
