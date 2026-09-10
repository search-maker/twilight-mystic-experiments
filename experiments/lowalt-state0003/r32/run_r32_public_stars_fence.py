#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNNER = HERE / "run_r32.py"
STARS_URL = "https://api.github.com/repos/search-maker/starsvisibility/branches/main"

spec = importlib.util.spec_from_file_location("lowalt_r32_core", RUNNER)
if spec is None or spec.loader is None:
    raise RuntimeError("cannot-load-r32-runner")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
_original_api_get = mod.api_get


def _public_get(url: str):
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "lowalt-state0003-r32-public-stars-fence",
        },
    )
    with urllib.request.urlopen(req, timeout=90) as response:
        return json.load(response)


def _api_get(url: str, token: str):
    if url == STARS_URL:
        return _public_get(url)
    return _original_api_get(url, token)


mod.api_get = _api_get

pre = Path(os.environ.get("R32_PRE_DIR", "/tmp"))
pre.mkdir(parents=True, exist_ok=True)
mod.write_json(
    pre / "public-stars-fence-adapter.json",
    {
        "schemaVersion": 1,
        "classification": "LOWALT_R32_MECHANICAL_PUBLIC_STARSVISIBILITY_FENCE_ADAPTER",
        "starsUrl": STARS_URL,
        "authorizationHeaderForStarsRequest": False,
        "sameRepoGithubApiRemainsAuthenticated": True,
        "scientificMatrixModified": False,
        "scientificContractModified": False,
        "scientificIdentityModified": False,
        "developmentResultOpenedByAdapter": False,
        "auditOpenedByAdapter": False,
        "productionBelow5Deg": "FAIL_CLOSED_UNCHANGED",
    },
)

if __name__ == "__main__":
    try:
        rc = mod.main()
    except Exception as exc:
        evidence = Path(os.environ.get("R32_EVIDENCE_DIR", "/tmp/r32-evidence"))
        evidence.mkdir(parents=True, exist_ok=True)
        mod.write_json(
            evidence / "fatal-barrier.json",
            {
                "classification": "LOWALT_R32_MECHANICAL_OR_GOVERNANCE_BARRIER",
                "errorType": type(exc).__name__,
                "error": str(exc),
                "auditOpened": False,
                "retuningPerformed": False,
                "productionBelow5Deg": "FAIL_CLOSED_UNCHANGED",
            },
        )
        mod.manifest(evidence)
        raise
    raise SystemExit(rc)
