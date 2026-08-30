#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'generated-avps-v2-recovery3-ordinal44-execution-package'
SCIENCE = OUT / 'avps-v2-postconsumption-recovery3-science.yml'
PUBLISHER = OUT / 'avps-v2-postconsumption-recovery3-dispatch-publisher.yml'
TRIGGER = OUT / 'avps-v2-postconsumption-recovery3-publisher-trigger-bridge.yml'
MANIFEST = OUT / 'manifest.json'
AUTH_HEAD = 'dd3a4c692af505389e9feb1e5f5480fa389110a3'
AUTH_PARENT = 'd8cd4af807e7a8f11ed39fdc579ed92adf866aab'


def replace_exact(text: str, old: str, new: str, count: int) -> str:
    got = text.count(old)
    if got != count:
        raise SystemExit(f'expected {count} occurrences of {old!r}, found {got}')
    return text.replace(old, new)


def git_blob(raw: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def file_identity(path: Path) -> dict[str, str]:
    raw = path.read_bytes()
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'gitBlobSha1': git_blob(raw)}


def main() -> int:
    science = SCIENCE.read_text()
    science = replace_exact(
        science,
        'avps-v2-postconsumption-recovery2-preflight-ordinal-43',
        'avps-v2-postconsumption-recovery3-preflight-ordinal-44',
        2,
    )
    science = replace_exact(
        science,
        'avps-v2-postconsumption-recovery2-complete-ordinal-43',
        'avps-v2-postconsumption-recovery3-complete-ordinal-44',
        1,
    )
    SCIENCE.write_text(science)

    publisher = PUBLISHER.read_text()
    old = "if r.get('status')!='PASS_AVPS_V2_RECOVERY3_ORDINAL44_EXECUTION_PACKAGE_REVIEW_ZERO_RUNTIME': raise SystemExit(1)"
    new = (
        "if r.get('status')!='PASS_AVPS_V2_RECOVERY3_ORDINAL44_EXECUTION_PACKAGE_REVIEW_ZERO_RUNTIME' "
        "or r.get('mode')!='publication' "
        f"or r.get('authorizationHead')!='{AUTH_HEAD}' "
        f"or r.get('authorizationParent')!='{AUTH_PARENT}' "
        "or r.get('authorizationPr')!=718: raise SystemExit(1)"
    )
    publisher = replace_exact(publisher, old, new, 1)
    PUBLISHER.write_text(publisher)

    publisher_blob = git_blob(PUBLISHER.read_bytes())
    trigger = TRIGGER.read_text()
    pattern = re.compile(r'(?m)^  PUBLISHER_BLOB: [0-9a-f]{40}$')
    matches = pattern.findall(trigger)
    if len(matches) != 1:
        raise SystemExit(f'expected exactly one trigger PUBLISHER_BLOB binding, found {len(matches)}')
    trigger = pattern.sub(f'  PUBLISHER_BLOB: {publisher_blob}', trigger, count=1)
    TRIGGER.write_text(trigger)

    manifest = json.loads(MANIFEST.read_text())
    manifest['hardeningPostprocessApplied'] = True
    manifest['freshPreflightArtifactIdentity'] = True
    manifest['publicationModeReviewRequiredBeforeDispatch'] = True
    manifest['triggerBindsHardenedPublisherBlob'] = True
    manifest['outputs'] = {
        SCIENCE.name: file_identity(SCIENCE),
        PUBLISHER.name: file_identity(PUBLISHER),
        TRIGGER.name: file_identity(TRIGGER),
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
