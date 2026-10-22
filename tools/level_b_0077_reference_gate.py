#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, importlib.util, json, math, sys
from pathlib import Path

ALT = [6.25, 8.75, 12.5, 17.5, 25.0, 37.5, 52.5, 65.0, 75.0]
ELEV = [250.0, 875.0, 1625.0, 2250.0]
AOD = [0.075, 0.15, 0.25, 0.35]
MAX_LIMIT = 0.025
RMS_LIMIT = 0.010
PROTOCOL_NAMES = (
    'STELLAR_TRANSPORT_VALIDATION_PROTOCOL_V1.md',
    'STELLAR_TRANSPORT_VALIDATION_PROTOCOL_V1_AMENDMENT_1.md',
    'STELLAR_TRANSPORT_VALIDATION_PROTOCOL_V1_AMENDMENT_2_SOURCE_TRANSPORT.md',
)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def load_json(p: Path):
    return json.loads(p.read_text(encoding='utf-8'))


def import_ref(app: Path):
    p = app/'scientific-tools/visibility-v3/stellar_transmission_libradtran_v3.py'
    spec = importlib.util.spec_from_file_location('stellar_ref', p)
    m = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules['stellar_ref'] = m
    spec.loader.exec_module(m)
    return m


def identity_coordinate(value):
    return value


def cosecant_altitude_coordinate(altitude_deg):
    mu = math.sin(math.radians(float(altitude_deg)))
    if not mu > 0:
        raise ValueError('target altitude must be above the geometric horizon')
    return 1.0 / mu


def bracket(axis, value, coordinate=identity_coordinate):
    if value < axis[0] or value > axis[-1]: raise ValueError('outside LUT support')
    if value == axis[-1]: return len(axis)-2, len(axis)-1, 1.0
    for hi in range(1, len(axis)):
        if value < axis[hi]:
            lo=hi-1
            clo, chi, cv = coordinate(axis[lo]), coordinate(axis[hi]), coordinate(value)
            return lo, hi, (cv-clo)/(chi-clo)
    raise AssertionError


def interp_tau(lut, altitude, elevation, aod):
    aa=lut['axes']['targetAltitudeDeg']; ee=lut['axes']['observerElevationM']; oo=lut['axes']['aod550']
    # The frozen libRadtran direct-beam reference is plane-parallel. At fixed
    # atmosphere state, line-of-sight direct optical depth scales exactly with
    # csc(target altitude)=1/mu0. Keep the preregistered altitude knots unchanged
    # but interpolate tau in that physical coordinate rather than raw degrees.
    ab=bracket(aa, altitude, cosecant_altitude_coordinate)
    eb=bracket(ee, elevation)
    ob=bracket(oo, aod)
    ne=len(ee); no=len(oo)
    def idx(ai,ei,oi): return ((ai*ne)+ei)*no+oi
    out=[]
    for w in range(len(lut['wavelengthNm'])):
        def v(ai,ei,oi): return float(lut['directOpticalDepth'][idx(ai,ei,oi)][w])
        c000=v(ab[0],eb[0],ob[0]); c001=v(ab[0],eb[0],ob[1]); c010=v(ab[0],eb[1],ob[0]); c011=v(ab[0],eb[1],ob[1])
        c100=v(ab[1],eb[0],ob[0]); c101=v(ab[1],eb[0],ob[1]); c110=v(ab[1],eb[1],ob[0]); c111=v(ab[1],eb[1],ob[1])
        lerp=lambda x,y,f: x+(y-x)*f
        c00=lerp(c000,c001,ob[2]); c01=lerp(c010,c011,ob[2]); c10=lerp(c100,c101,ob[2]); c11=lerp(c110,c111,ob[2])
        c0=lerp(c00,c01,eb[2]); c1=lerp(c10,c11,eb[2]); out.append(lerp(c0,c1,ab[2]))
    return out


def extinction(flux, response, transmission):
    den=sum(float(f)*float(r) for f,r in zip(flux,response))
    num=sum(float(f)*float(r)*float(t) for f,r,t in zip(flux,response,transmission))
    if not (den > 0 and num > 0): raise ValueError('non-positive Johnson-V integral')
    return -2.5*math.log10(num/den)


def choose_templates(bundle):
    normal=[t for t in bundle['templates'] if t.get('abundance')=='normal']
    if not normal: raise ValueError('no normal-abundance templates')
    blue=min(normal,key=lambda t:(float(t['bMinusVLandoltBmVc']),int(t['libraryNumber'])))
    solar=min(normal,key=lambda t:(abs(float(t['bMinusVLandoltBmVc'])-0.65),int(t['libraryNumber'])))
    red=max(normal,key=lambda t:(float(t['bMinusVLandoltBmVc']),-int(t['libraryNumber'])))
    return [blue,solar,red]


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--app-dir',type=Path,required=True)
    ap.add_argument('--sed-bundle',type=Path,required=True)
    ap.add_argument('--lut',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    app=args.app_dir.resolve(); bundle=load_json(args.sed_bundle); lut=load_json(args.lut)
    band_path=app/'scientific-tools/visibility-v3/generated/johnson-v-1nm.json'; band=load_json(band_path)
    grid=list(range(380,781))
    if bundle['wavelengthNm']!=grid or lut['wavelengthNm']!=grid or band['wavelengthNm']!=grid: raise SystemExit('wavelength grid mismatch')
    templates=choose_templates(bundle); ref=import_ref(app)
    rows=[]
    for alt in ALT:
      for elev in ELEV:
       for aod in AOD:
        rr=ref.run_reference(target_altitude_deg=alt,aod550=aod,observer_elevation_m=elev)
        rt=rr['spectrum']['lineOfSightDirectTransmission']
        tau=interp_tau(lut,alt,elev,aod); lt=[math.exp(-x) for x in tau]
        for t in templates:
          ar=extinction(t['fluxRelative'],band['response'],rt); al=extinction(t['fluxRelative'],band['response'],lt)
          rows.append({'targetAltitudeDeg':alt,'observerElevationM':elev,'aod550':aod,'templateId':t['templateId'],'bMinusV':t['bMinusVLandoltBmVc'],'referenceAvMag':ar,'runtimeAvMag':al,'deltaAvMag':al-ar,'absDeltaAvMag':abs(al-ar)})
    if len(rows)!=432: raise SystemExit(f'expected 432 rows, got {len(rows)}')
    maxerr=max(r['absDeltaAvMag'] for r in rows); rms=math.sqrt(sum(r['deltaAvMag']**2 for r in rows)/len(rows))
    protocol_dir=app/'scientific-tools/visibility-v3'
    protocol=sha256_bytes(b'\n'.join((protocol_dir/name).read_bytes() for name in PROTOCOL_NAMES))
    if lut.get('provenance',{}).get('validationProtocolSha256') != protocol:
        raise SystemExit('LUT protocol hash does not match gate protocol hash')
    passed=(maxerr<=MAX_LIMIT and rms<=RMS_LIMIT)
    result={'schemaVersion':1,'gate':'MYSTIC-STATE-0077-stellar-transport-reference','caseCount':len(rows),'atmosphericCaseCount':144,'templates':[{'templateId':t['templateId'],'libraryNumber':t['libraryNumber'],'bMinusV':t['bMinusVLandoltBmVc']} for t in templates],'limits':{'maxAbsDeltaAvMag':MAX_LIMIT,'rmsDeltaAvMag':RMS_LIMIT},'statistics':{'maxAbsDeltaAvMag':maxerr,'rmsDeltaAvMag':rms},'pass':passed,'protocolSha256':protocol,'interpolation':{'quantity':'directOpticalDepth','targetAltitudeCoordinate':'cosecant-altitude-1-over-sin-h','observerElevationCoordinate':'linear-meters','aod550Coordinate':'linear'},'hashes':{'sedBundleSha256':sha256_file(args.sed_bundle),'lutSha256':sha256_file(args.lut),'johnsonVGridSha256':sha256_file(band_path)},'rows':rows}
    args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:result[k] for k in ['gate','caseCount','statistics','pass','protocolSha256','interpolation','hashes']},sort_keys=True))
    raise SystemExit(0 if passed else 2)


if __name__=='__main__': main()
