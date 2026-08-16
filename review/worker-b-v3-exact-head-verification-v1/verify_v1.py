#!/usr/bin/env python3
import argparse, hashlib, json, zipfile
from pathlib import Path

ZIP_SHA = 'ed7c62c3efea525c531ab6587108320f5be5546d210af5054a5304ed07939a39'
MODEL_FILE_SHA = '0b850664584244abdc781f87ce9e5b89cdab28b08a2999612b155378cbe42d79'
REP_SHA = '2491ac91ed924f2ba69b37ea20f48d63f51d41146cd9fe50e0bd63bfb315a763'
MODEL_CANONICAL = 'c4902eb3c2ba67b12dc4ef2b9cefb67c5963a6abc104708a73b2aab5dd0163b9'
PACKAGE_MANIFEST_SHA = '2df88b800483127d565e66b03a5773920dd6a687f9afb0ace43f3cc93b2635aa'
VALIDATION_BINDING_SHA = '120a4649ad61159c4d4edc13f10dd8ca335408dc2dcc3b9c0889bbced2485c57'
RUNTIME_SHA = '6a927bd702ebbf1b1913ebe51731f3b92f967f2ae95edf090280b8370ea091e4'
APP_HEAD = 'cb45f4f04db9d3121141acce23e9e0a373ecfc1a'
EXPECTED_MEMBERS = {
    'model-artifact-materialization-v1.json',
    'spectral-representation-v2.npz',
    'validated-surrogate-package-v1.json',
}
EXPECTED_BLOBS = {
    'atmosphere-state.mjs': '158d61071ffb492ca2556f13983be2a2b6a3781a',
    'human-threshold.mjs': 'bb4cd0ff02159ecffe276022cec9d292c7a434a3',
    'sky-provider.mjs': 'ba79a4b92e0fdbb583e2136134a3644f26a6eb1c',
    'validated-v3-primary-runtime-v1.json': '5790ccb2c289de082a2851d96e4c3c660a1c4985',
    'validated-v3-sky-provider.mjs': 'da8c5995559020865118220d939e58d89e6b98e4',
    'visibility-event-timeline.mjs': 'b49ff62f8602035e85582c5805d470114159e8ba',
    'visibility-runtime.mjs': 'f801b8648452e50520e7f2bde997d95b399474e9',
    'tests/test-validated-v3-sky-provider.mjs': '1de90e1f9b4c68f86d7f3482b253b8ac18778f6c',
}

def sha256(data): return hashlib.sha256(data).hexdigest()
def git_blob_sha(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()

def runtime_from_model(model_doc):
    m = model_doc['model']
    b = m['baseModel']
    return {
        'schemaVersion': 1,
        'sourceModelCanonicalSha256': m['modelCanonicalSha256'],
        'primaryBasis': b['primary']['basis'],
        'primaryCoefficients': b['primary']['coefficients'],
        'supportCoordinates': b['shape']['coordinates'],
        'residualCoordinateSystem': m['residualCoordinateSystem'],
        'residualCoordinates': m['residualCoordinates'],
        'residualTargets': m['residualTargets'],
        'residualNeighbors': m['residualNeighbors'],
        'residualPower': m['residualPower'],
        'residualShrinkage': m['residualShrinkage'],
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--package', required=True)
    ap.add_argument('--snapshot')
    args = ap.parse_args()
    package = Path(args.package)
    zbytes = package.read_bytes()
    assert sha256(zbytes) == ZIP_SHA, 'package ZIP digest drift'
    with zipfile.ZipFile(package) as z:
        assert set(z.namelist()) == EXPECTED_MEMBERS, 'package member drift'
        model_bytes = z.read('model-artifact-materialization-v1.json')
        rep_bytes = z.read('spectral-representation-v2.npz')
        manifest_bytes = z.read('validated-surrogate-package-v1.json')
    assert sha256(model_bytes) == MODEL_FILE_SHA, 'model file drift'
    assert sha256(rep_bytes) == REP_SHA, 'representation drift'
    model_doc = json.loads(model_bytes)
    manifest = json.loads(manifest_bytes)
    assert model_doc['model']['modelCanonicalSha256'] == MODEL_CANONICAL
    assert manifest['packageManifestSha256'] == PACKAGE_MANIFEST_SHA
    assert manifest['model']['modelCanonicalSha256'] == MODEL_CANONICAL
    assert manifest['representation']['packageSha256'] == REP_SHA
    assert manifest['validationBinding']['bindingSelfSha256'] == VALIDATION_BINDING_SHA
    assert manifest['validationBinding']['scientificStatus'] == 'PASS_FROZEN_FRESH_DOD'
    assert manifest['validationBinding']['definitionOfDonePassed'] is True
    assert manifest['packageBuild']['protectedTruthCopied'] is False
    assert manifest['packageContents']['includesOrdinal28ProtectedTruthRecords'] is False
    assert manifest['packageContents']['includesOrdinal28CaseArtifacts'] is False
    assert manifest['packageContents']['includesRawMysticSpectra'] is False
    assert manifest['consumerBoundaries']['productionPromotionAuthorized'] is False
    assert manifest['consumerBoundaries']['measuredRealSkyValidationComplete'] is False
    assert manifest['consumerBoundaries']['humanFirstSeeingValidationComplete'] is False
    assert manifest['geometryInputContract']['silentExtrapolationAllowed'] is False
    assert manifest['geometryInputContract']['validatedSupportRule'].endswith('MUST_BE_LE_0.60')
    runtime = runtime_from_model(model_doc)
    runtime_bytes = json.dumps(runtime, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode() + b'\n'
    assert sha256(runtime_bytes) == RUNTIME_SHA, 'runtime extraction SHA drift'
    assert git_blob_sha(runtime_bytes) == EXPECTED_BLOBS['validated-v3-primary-runtime-v1.json'], 'runtime Git blob drift'
    if args.snapshot:
        root = Path(args.snapshot)
        for rel, expected in EXPECTED_BLOBS.items():
            data = (root / rel).read_bytes()
            got = git_blob_sha(data)
            assert got == expected, f'app snapshot blob drift: {rel} {got} != {expected}'
        assert (root / 'validated-v3-primary-runtime-v1.json').read_bytes() == runtime_bytes, 'snapshot runtime bytes differ from package-derived runtime'
    print(json.dumps({
        'status': 'PASS',
        'appHead': APP_HEAD,
        'packageZipSha256': ZIP_SHA,
        'runtimeSha256': RUNTIME_SHA,
        'runtimeGitBlob': EXPECTED_BLOBS['validated-v3-primary-runtime-v1.json'],
        'snapshotVerified': bool(args.snapshot),
        'protectedTruthCopied': False,
        'productionAuthorized': False,
    }, sort_keys=True))

if __name__ == '__main__': main()
