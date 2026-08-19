from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from core import (
    Refusal, canonical_sha256, dump, raw_sha256, git_blob_sha1,
    validate_seed_audit_for_freeze, write_manifest,
)

STAGE_ID = "aerosol-family-challenge-v2-freeze"
CHANNEL_SOURCE_PATH = "review/full-spectrum-estimator-pilot-v2/build_full_spectrum_training_handoff.py"
CHANNEL_SOURCE_BLOB = "9bc53956fc4a49935ba2957087d8bf4203b7e8be"
POSTPROCESS_SOURCE_BLOB = "47e90aa128942276e1510305449bb3c58930032e"


def _validate_analysis_contract(path: Path, package_dir: Path) -> dict:
    c = json.loads(path.read_text())
    if path.name != "analysis-contract.v3.json":
        raise Refusal("analysis contract filename/version drift")
    exact = {
        "schemaVersion": 3,
        "stageId": "aerosol-family-challenge-v2-analysis",
        "status": "FROZEN_BEFORE_RESULTS",
        "resultsOpened": False,
        "scientificExecutionAuthorized": False,
    }
    for key, value in exact.items():
        if c.get(key) != value:
            raise Refusal(f"analysis contract drift: {key}")
    if c.get("baselineState") != {"aerosolFamily": "rural", "aerosolSeason": "spring-summer"}:
        raise Refusal("analysis baseline changed")
    crn = c.get("commonRandomNumberUncertainty")
    if not isinstance(crn, dict) or "independent quadrature" not in str(crn.get("forbidden", "")):
        raise Refusal("CRN covariance guard missing")
    spectrum = c.get("spectrumContract")
    if not isinstance(spectrum, dict) or "8001" not in str(spectrum.get("rawSerializedGrid", "")) or "0.05" not in str(spectrum.get("rawSerializedGrid", "")):
        raise Refusal("raw serialized spectrum contract changed")
    implementation = c.get("analysisImplementation")
    analysis_impl = package_dir / "analysis.py"
    if not isinstance(implementation, dict) or implementation.get("path") != "analysis.py" or not analysis_impl.is_file() or implementation.get("localImplementationRawSha256") != raw_sha256(analysis_impl):
        raise Refusal("local analysis implementation drift")
    channels = c.get("channelDefinitions")
    if not isinstance(channels, dict) or channels.get("sourcePath") != CHANNEL_SOURCE_PATH or channels.get("sourceGitBlobSha") != CHANNEL_SOURCE_BLOB:
        raise Refusal("derived-channel source binding changed")
    local = package_dir / "derived_channels.py"
    if not local.is_file() or channels.get("localImplementationRawSha256") != raw_sha256(local):
        raise Refusal("local derived-channel implementation drift")
    if c.get("channelDefinitions", {}).get("additionalScalarColorIndex") != "NONE_PREDECLARED; spectral/color response is represented by S/P and the full per-wavelength paired log-ratio vector":
        raise Refusal("post-result scalar color metric could be introduced")
    return c


def freeze(design: Path, analysis_contract: Path, seed_audit: Path, manifest_out: Path, freeze_out: Path) -> dict:
    d = json.loads(design.read_text())
    a = json.loads(seed_audit.read_text())
    validate_seed_audit_for_freeze(a, design, d)
    c = _validate_analysis_contract(analysis_contract, design.parent)
    source = d.get("sourceBindings", {})
    post = source.get("fullSpectrumPostprocessGridContract", {})
    if post.get("gitBlobSha") != POSTPROCESS_SOURCE_BLOB or post.get("contractSha256") != "d7d9c98e5676689959dcc3ffca4778925728df819d3fdbc7e39bfa9be92069a3":
        raise Refusal("full-spectrum serialized-grid source binding changed")
    grid = design.parent / "wavelength-grid-1nm.dat"
    if not grid.is_file() or grid.read_text().splitlines() != [str(x) for x in range(380, 781)] or git_blob_sha1(grid) != "3bb3db96580d555ef758f57cabd6cac55b61cebb":
        raise Refusal("local 1-nm calculation grid is not byte-equivalent to reviewed grid")

    # No output is written before every gate above succeeds.
    m = write_manifest(design, manifest_out)
    m["status"] = "FROZEN_MANIFEST_SEED_FRESHNESS_PROVEN_REVIEW_ONLY"
    m["seedFreshnessStatus"] = a["status"]
    m["seedAuditRawSha256"] = raw_sha256(seed_audit)
    m["seedAuditRepositoryHead"] = a["repositoryHead"]
    manifest_out.write_text(dump(m), encoding="utf-8", newline="\n")
    r = {
        "schemaVersion": 3,
        "stageId": STAGE_ID,
        "status": "FROZEN_REVIEW_PACKAGE_NOT_AUTHORIZATION",
        "scientificExecutionAuthorized": False,
        "solverExecutionAuthorized": False,
        "resultsOpened": False,
        "sourceBaseMainSha": d["sourceBindings"]["publicRepoMainSha"],
        "seedAuditExactHead": a["repositoryHead"],
        "authorizationTimeSeedRecheckStillRequired": True,
        "designRawSha256": raw_sha256(design),
        "analysisContractRawSha256": raw_sha256(analysis_contract),
        "analysisContractCanonicalSha256": canonical_sha256(c),
        "analysisImplementationRawSha256": raw_sha256(design.parent / "analysis.py"),
        "derivedChannelsRawSha256": raw_sha256(design.parent / "derived_channels.py"),
        "seedAuditRawSha256": raw_sha256(seed_audit),
        "wavelengthGridRawSha256": raw_sha256(grid),
        "wavelengthGridGitBlobSha": git_blob_sha1(grid),
        "manifestRawSha256": raw_sha256(manifest_out),
        "manifestCanonicalSha256": canonical_sha256(m),
    }
    freeze_out.write_text(dump(r), encoding="utf-8", newline="\n")
    return r


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--design', type=Path, required=True)
    ap.add_argument('--analysis-contract', type=Path, required=True)
    ap.add_argument('--seed-audit', type=Path, required=True)
    ap.add_argument('--manifest-out', type=Path, required=True)
    ap.add_argument('--freeze-out', type=Path, required=True)
    x = ap.parse_args()
    try:
        print(dump(freeze(x.design, x.analysis_contract, x.seed_audit, x.manifest_out, x.freeze_out)), end='')
        return 0
    except Exception as e:
        print(dump({'stageId': STAGE_ID, 'status': 'REFUSED', 'reason': str(e)}), end='', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
