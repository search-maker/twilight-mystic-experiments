#!/usr/bin/env python3
from __future__ import annotations

import hashlib
from pathlib import Path

SCIENCE_SRC = Path(".github/workflows/avps-v2-postconsumption-recovery1-science.yml")
PUBLISHER_SRC = Path(".github/workflows/avps-v2-postconsumption-recovery1-dispatch-publisher.yml")
BRIDGE_SRC = Path(".github/workflows/avps-v2-postconsumption-recovery1-publisher-trigger-bridge.yml")
OUT = Path("generated-avps-v2-recovery2")

SCIENCE_OUT = "avps-v2-postconsumption-recovery2-science.yml"
PUBLISHER_OUT = "avps-v2-postconsumption-recovery2-dispatch-publisher.yml"
BRIDGE_OUT = "avps-v2-postconsumption-recovery2-publisher-trigger-bridge.yml"

AUTH_BRANCH = "authorization/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery2-ordinal-43"
AUTH_HEAD = "5fd0c82cb14a02ace38a5a7be30b8b075ccae298"
AUTH_PARENT = "0842dd27f62c4bc2af4b5763ae4dd547ee009fce"
AUTH_PR = "647"
AUTH_REVIEW_RUN = "33277629404"
AUTH_REVIEW_ARTIFACT = "9722104370"
AUTH_REVIEW_DIGEST = "sha256:9dac9e9305b78e2ddbceacbc10a19435121b0eeacfe48550d23878359556ae15"
AUTH_PATH = "review/avps-v2-recovery2-posttransport-authorization-control-recovery-v1/authorization.json"
AUTH_BLOB = "9db4602cd2877161b9c4d6d5ffad27409c52dd3f"

DISPATCH_BRANCH = "dispatch/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery2-ordinal-43"
EXECUTION_KEY = "aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery2:numerical:43"
ALLOCATION_MARKER = (
    "ORDINAL43_AVPS_V2_POSTCONSUMPTION_RECOVERY2_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED "
    "commit=5fd0c82cb14a02ace38a5a7be30b8b075ccae298 "
    "parent=0842dd27f62c4bc2af4b5763ae4dd547ee009fce pr=647"
)
CONSUMED_MARKER = "ORDINAL43_AVPS_V2_POSTCONSUMPTION_RECOVERY2_DISPATCH_CONSUMED"
SEED_SHA256 = "38c074fe01bd6d09fa7dc78af1ad323e2f42b606ca992c2950b8fc1f5b343a9f"
ROWS_SHA256 = "a88b28dcfaaeb354f294d1705a0f8ddbcd061083f277a038ab8c9dace44d9954"
AUTH_SEED_PATH = "review/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery2-seed-freshness-v1/seed_ledger.py"
AUTH_SEED_BLOB = "d4bdc95e9ed576fa6c70711c81d8097ddab33dbf"
NATIVE_HELPER_PATH = "review/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery2-science-transport-v1/native_authorization_seed_transport.py"
NATIVE_HELPER_BLOB = "2df2c3fd1ffa78e16f44e6825d67b3e82e903c1e"

HISTORICAL_AUTH_BRANCH = "authorization/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery1-ordinal-42"
HISTORICAL_HEAD = "e627a689ada0493a8a5b9cdafc4aba0198fbabec"
HISTORICAL_SEED_PATH = "review/aerosol-vertical-profile-sensitivity-v2-postconsumption-seed-freshness-v1/seed_ledger.py"
HISTORICAL_SEED_BLOB = "491d1b6653bea0fcc5275269723a76aa1af52300"

OLD_AUTH_HEAD = "e627a689ada0493a8a5b9cdafc4aba0198fbabec"
OLD_AUTH_PARENT = "a68f603d6da21cd28ab8324da080cc8ad27f9094"
OLD_AUTH_REVIEW_RUN = "33250602685"
OLD_AUTH_REVIEW_ARTIFACT = "9714316591"
OLD_AUTH_REVIEW_DIGEST = "sha256:083d7127a1591810870875d1b6c15f795c1fee0996c1dadaec5838b785bce8c2"
OLD_AUTH_PATH = "review/aerosol-vertical-profile-sensitivity-v2-postconsumption-authorization-control-v1/authorization.json"
OLD_AUTH_BLOB = "4aa103548029a7b8748ad636ae6e3e7e8f69a8d2"
OLD_SEED = "a514212990a94a39d577bd038b631a600e18e4c0f750f781bbd7c99b897228a7"
OLD_ALLOCATION = (
    "ORDINAL42_AVPS_V2_POSTCONSUMPTION_RECOVERY1_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED "
    "commit=e627a689ada0493a8a5b9cdafc4aba0198fbabec "
    "parent=a68f603d6da21cd28ab8324da080cc8ad27f9094 pr=629"
)


def must(text: str, old: str, new: str) -> str:
    if old not in text:
        raise SystemExit(f"missing required source token: {old!r}")
    return text.replace(old, new)


def replace_section(text: str, start: str, end: str, replacement: str) -> str:
    i = text.find(start)
    if i < 0:
        raise SystemExit(f"missing section start: {start!r}")
    j = text.find(end, i + len(start))
    if j < 0:
        raise SystemExit(f"missing section end: {end!r}")
    return text[:i] + replacement + text[j:]


def blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def common_identity(text: str) -> str:
    pairs = [
        (OLD_ALLOCATION, ALLOCATION_MARKER),
        ("authorization/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery1-ordinal-42", AUTH_BRANCH),
        (OLD_AUTH_HEAD, AUTH_HEAD),
        (OLD_AUTH_PARENT, AUTH_PARENT),
        ("AUTH_PR: '629'", f"AUTH_PR: '{AUTH_PR}'"),
        (f"AUTH_REVIEW_RUN: '{OLD_AUTH_REVIEW_RUN}'", f"AUTH_REVIEW_RUN: '{AUTH_REVIEW_RUN}'"),
        (f"AUTH_REVIEW_ARTIFACT: '{OLD_AUTH_REVIEW_ARTIFACT}'", f"AUTH_REVIEW_ARTIFACT: '{AUTH_REVIEW_ARTIFACT}'"),
        (OLD_AUTH_REVIEW_DIGEST, AUTH_REVIEW_DIGEST),
        ("dispatch/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery1-ordinal-42", DISPATCH_BRANCH),
        ("aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery1:numerical:42", EXECUTION_KEY),
        ("ORDINAL42_AVPS_V2_POSTCONSUMPTION_RECOVERY1_DISPATCH_CONSUMED", CONSUMED_MARKER),
        (OLD_SEED, SEED_SHA256),
        (OLD_AUTH_PATH, AUTH_PATH),
        (OLD_AUTH_BLOB, AUTH_BLOB),
        ("postconsumption-recovery1", "postconsumption-recovery2"),
        ("postconsumption recovery1", "postconsumption recovery2"),
        ("POSTCONSUMPTION_RECOVERY1", "POSTCONSUMPTION_RECOVERY2"),
        ("ordinal-42", "ordinal-43"),
        ("ordinal 42", "ordinal 43"),
        ("ORDINAL42", "ORDINAL43"),
        ("p['number']!=629", "p['number']!=647"),
        ("'scientificOrdinal':42", "'scientificOrdinal':43"),
        ("'authorizationPr':629", "'authorizationPr':647"),
    ]
    optional = {OLD_AUTH_PATH, OLD_AUTH_BLOB, "ORDINAL42"}
    for old, new in pairs:
        if old in optional and old not in text:
            continue
        text = must(text, old, new)
    return text


def add_native_env(text: str) -> str:
    needle = f"  CANDIDATE_SEED_SHA256: {SEED_SHA256}\n"
    extra = (
        needle
        + f"  CANDIDATE_ROWS_SHA256: {ROWS_SHA256}\n"
        + f"  AUTH_SEED_LEDGER_PATH: {AUTH_SEED_PATH}\n"
        + f"  AUTH_SEED_LEDGER_BLOB: {AUTH_SEED_BLOB}\n"
        + f"  NATIVE_SEED_HELPER_PATH: {NATIVE_HELPER_PATH}\n"
        + f"  NATIVE_SEED_HELPER_BLOB: {NATIVE_HELPER_BLOB}\n"
        + f"  HISTORICAL_AUTH_BRANCH: {HISTORICAL_AUTH_BRANCH}\n"
        + f"  HISTORICAL_HEAD: {HISTORICAL_HEAD}\n"
        + f"  HISTORICAL_SEED_LEDGER_PATH: {HISTORICAL_SEED_PATH}\n"
        + f"  HISTORICAL_SEED_LEDGER_BLOB: {HISTORICAL_SEED_BLOB}\n"
    )
    return must(text, needle, extra)


def native_seed_block(prefix: str) -> str:
    return (
        f"          git ls-files -z > {prefix}/tracked-files.nul\n"
        f"          test \"$(git rev-parse HEAD:$NATIVE_SEED_HELPER_PATH)\" = \"$NATIVE_SEED_HELPER_BLOB\"\n"
        f"          git fetch origin \"refs/heads/$HISTORICAL_AUTH_BRANCH:refs/remotes/origin/$HISTORICAL_AUTH_BRANCH\"\n"
        f"          test \"$(git rev-parse origin/$HISTORICAL_AUTH_BRANCH)\" = \"$HISTORICAL_HEAD\"\n"
        f"          python \"$NATIVE_SEED_HELPER_PATH\" \\\n"
        f"            --repo-root . \\\n"
        f"            --authorization-head \"$AUTH_HEAD\" \\\n"
        f"            --authorization-parent \"$AUTH_PARENT\" \\\n"
        f"            --authorization-ledger-path \"$AUTH_SEED_LEDGER_PATH\" \\\n"
        f"            --authorization-ledger-blob \"$AUTH_SEED_LEDGER_BLOB\" \\\n"
        f"            --candidate-seed-sha256 \"$CANDIDATE_SEED_SHA256\" \\\n"
        f"            --candidate-rows-sha256 \"$CANDIDATE_ROWS_SHA256\" \\\n"
        f"            --historical-head \"$HISTORICAL_HEAD\" \\\n"
        f"            --historical-ledger-path \"$HISTORICAL_SEED_LEDGER_PATH\" \\\n"
        f"            --historical-ledger-blob \"$HISTORICAL_SEED_LEDGER_BLOB\" \\\n"
        f"            --work-root {prefix}/native-seed-transport \\\n"
        f"            --output-ledger {prefix}/candidate-seed-ledger.json \\\n"
        f"            --output-context {prefix}/native-seed-context.json\n"
        f"          python - <<'PY'\n"
        f"          import json\n"
        f"          from pathlib import Path\n"
        f"          Path('{prefix}/empty-self-ledger-policy.json').write_text(json.dumps({{'schemaVersion':2,'requiredTrackedSelfLedgerPaths':[],'futureEvidenceSelfLedgerPaths':[]}},indent=2,sort_keys=True)+'\\n')\n"
        f"          PY\n"
    )


def science() -> str:
    t = common_identity(SCIENCE_SRC.read_text())
    t = add_native_env(t)
    start = "          git ls-files -z > execution-preflight/tracked-files.nul\n"
    end = "          python review/aerosol-vertical-profile-sensitivity-v2-seed-freshness/tracked_tree_seed_scan.py \\\n"
    t = replace_section(t, start, end, native_seed_block("execution-preflight"))
    required = [
        AUTH_BRANCH, AUTH_HEAD, AUTH_PARENT, EXECUTION_KEY, CONSUMED_MARKER,
        SEED_SHA256, ROWS_SHA256, NATIVE_HELPER_PATH, NATIVE_HELPER_BLOB,
        HISTORICAL_HEAD, HISTORICAL_SEED_BLOB,
        "len(cases)!=360", "len(v)!=90", "20_000_000",
        "auth.get('resultOpeningAuthorized') is not False",
        "auth.get('productionAuthorized') is not False",
    ]
    for token in required:
        if token not in t:
            raise SystemExit(f"missing recovery2 science binding: {token}")
    forbidden = [
        "execution-preflight/recovery-seed-ledger.py",
        "aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery1:numerical:42",
        "ORDINAL42_AVPS_V2_POSTCONSUMPTION_RECOVERY1_DISPATCH_CONSUMED",
        OLD_SEED,
    ]
    for token in forbidden:
        if token in t:
            raise SystemExit(f"forbidden recovery1 science binding remains: {token}")
    return t


def publisher() -> str:
    t = common_identity(PUBLISHER_SRC.read_text())
    t = add_native_env(t)
    start = "          git ls-files -z > dispatch-evidence/tracked-files.nul\n"
    end = "          python review/aerosol-vertical-profile-sensitivity-v2-seed-freshness/tracked_tree_seed_scan.py "
    t = replace_section(t, start, end, native_seed_block("dispatch-evidence"))

    t = must(
        t,
        "actions/workflows/aerosol-vertical-profile-sensitivity-v2-postconsumption-implementation-generator-v1-review.yml/runs",
        "actions/workflows/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery2-implementation-generator-v1-review.yml/runs",
    )
    t = must(
        t,
        "-n avps-v2-postconsumption-implementation-generator-v1-review",
        "-n avps-v2-postconsumption-recovery2-implementation-generator-v1-review",
    )
    t = must(
        t,
        "PASS_AVPS_V2_POSTCONSUMPTION_RECOVERY2_GENERATED_IMPLEMENTATION_REVIEW_DISPATCH_NOT_CREATED",
        "PASS_AVPS_V2_POSTCONSUMPTION_RECOVERY2_GENERATED_IMPLEMENTATION_REVIEW_DISPATCH_NOT_CREATED",
    )

    ordinal_anchor = (
        "          if g.get('repositoryGlobalCollisionCount',g.get('collisionCount'))!=0: "
        "raise SystemExit('repository-global seed collision')\n"
        "          PY\n"
    )
    ordinal_check = ordinal_anchor + (
        "\n"
        "          PYTHONPATH=experiments/aerosol-vertical-profile-sensitivity-v1 python - <<'PY'\n"
        "          import json,os\n"
        "          from pathlib import Path\n"
        "          import preauthorization_surface, global_ordinal\n"
        "          payload=preauthorization_surface.collect(os.environ['GITHUB_REPOSITORY'],os.environ['GITHUB_TOKEN'])\n"
        "          latest=preauthorization_surface.latest_consumed_or_dispatched_ordinal(payload)\n"
        "          observations=global_ordinal.authoritative_global_ordinal_observations(payload,current_run_id=int(os.environ['GITHUB_RUN_ID']))\n"
        "          ordinals=sorted({int(row['ordinal']) for row in observations})\n"
        "          if latest!=42: raise SystemExit(f'latest consumed/dispatched global ordinal drift: {latest}')\n"
        "          if not ordinals or max(ordinals)!=43: raise SystemExit(f'global ordinal surface drift: {ordinals[-10:]}')\n"
        "          bodies=[str(c.get('body') or '').strip() for c in payload.get('issue60Comments',[])]\n"
        "          if sum(b==os.environ['ALLOCATION_MARKER'] for b in bodies)!=1: raise SystemExit('ordinal43 allocation marker cardinality drift in global surface')\n"
        "          if sum(b.startswith(os.environ['CONSUMED_MARKER']) for b in bodies)!=0: raise SystemExit('ordinal43 consumed marker already exists in global surface')\n"
        "          Path('dispatch-evidence/global-ordinal-observations.json').write_text(json.dumps(observations,indent=2,sort_keys=True)+'\\n')\n"
        "          Path('dispatch-evidence/global-ordinal-recheck.json').write_text(json.dumps({'schemaVersion':1,'status':'PASS_GLOBAL_ORDINAL43_ALLOCATED_NOT_CONSUMED_PRE_DISPATCH','latestConsumedOrDispatchedScientificOrdinal':latest,'maxObservedScientificOrdinal':max(ordinals),'candidateScientificOrdinal':43},indent=2,sort_keys=True)+'\\n')\n"
        "          PY\n"
    )
    t = must(t, ordinal_anchor, ordinal_check)

    required = [
        AUTH_BRANCH, AUTH_HEAD, AUTH_PARENT, EXECUTION_KEY, ALLOCATION_MARKER,
        CONSUMED_MARKER, SEED_SHA256, ROWS_SHA256, NATIVE_HELPER_PATH,
        "PASS_GLOBAL_ORDINAL43_ALLOCATED_NOT_CONSUMED_PRE_DISPATCH",
        "candidateScientificOrdinal':43",
    ]
    for token in required:
        if token not in t:
            raise SystemExit(f"missing recovery2 publisher binding: {token}")
    forbidden = [
        "dispatch-evidence/recovery-seed-ledger.py",
        "aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery1:numerical:42",
        "ORDINAL42_AVPS_V2_POSTCONSUMPTION_RECOVERY1_DISPATCH_CONSUMED",
        OLD_SEED,
    ]
    for token in forbidden:
        if token in t:
            raise SystemExit(f"forbidden recovery1 publisher binding remains: {token}")
    return t


def bridge(publisher_blob: str) -> str:
    t = BRIDGE_SRC.read_text()
    pairs = [
        ("AVPS v2 publisher postconsumption-recovery1-ordinal42 trigger bridge", "AVPS v2 publisher postconsumption-recovery2-ordinal43 trigger bridge"),
        ("AVPS v2 postconsumption recovery1 ordinal 42 publisher postconsumption-recovery1-ordinal42 trigger bridge", "AVPS v2 postconsumption recovery2 ordinal 43 publisher postconsumption-recovery2-ordinal43 trigger bridge"),
        ("dispatch-trigger/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery1-ordinal-42-publisher", "dispatch-trigger/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery2-ordinal-43-publisher"),
        ("dispatch-triggers/avps-v2-postconsumption-recovery1-ordinal42-publisher.txt", "dispatch-triggers/avps-v2-postconsumption-recovery2-ordinal43-publisher.txt"),
        ("group: avps-v2-postconsumption-recovery1-ordinal-42-publisher-trigger-bridge", "group: avps-v2-postconsumption-recovery2-ordinal-43-publisher-trigger-bridge"),
        ("avps-v2-postconsumption-recovery1-dispatch-publisher.yml", PUBLISHER_OUT),
        ("885abc21c86d3bb0c3777e63b6254520479db34f", publisher_blob),
        ("SCIENTIFIC_ORDINAL: '42'", "SCIENTIFIC_ORDINAL: '43'"),
        ("AVPS_V2_POSTCONSUMPTION_RECOVERY1_ORDINAL42_PUBLISHER_TRIGGER_V1", "AVPS_V2_POSTCONSUMPTION_RECOVERY2_ORDINAL43_PUBLISHER_TRIGGER_V1"),
        ("POSTCONSUMPTION_RECOVERY1_ORDINAL42_PRE_TRIGGER_BRIDGE_PASS_ZERO_RUNTIME", "POSTCONSUMPTION_RECOVERY2_ORDINAL43_PRE_TRIGGER_BRIDGE_PASS_ZERO_RUNTIME"),
        ("POSTCONSUMPTION_RECOVERY1_ORDINAL42_PUBLISHER_WORKFLOW_DISPATCH_REQUESTED_BY_ZERO_RUNTIME_BRIDGE", "POSTCONSUMPTION_RECOVERY2_ORDINAL43_PUBLISHER_WORKFLOW_DISPATCH_REQUESTED_BY_ZERO_RUNTIME_BRIDGE"),
        ("'scientificOrdinal':42", "'scientificOrdinal':43"),
        ("postconsumption-recovery1-ordinal42", "postconsumption-recovery2-ordinal43"),
    ]
    for old, new in pairs:
        t = must(t, old, new)
    for token in ("postconsumption-recovery1", "ORDINAL42", "SCIENTIFIC_ORDINAL: '42'", "885abc21c86d3bb0c3777e63b6254520479db34f"):
        if token in t:
            raise SystemExit(f"forbidden recovery1 bridge binding remains: {token}")
    return t


def main() -> None:
    OUT.mkdir(exist_ok=True)
    s = science()
    p = publisher()
    b = bridge(blob_sha1(p.encode()))
    generated = {SCIENCE_OUT: s, PUBLISHER_OUT: p, BRIDGE_OUT: b}
    rows = []
    for name, text in generated.items():
        raw = text.encode()
        (OUT / name).write_bytes(raw)
        rows.append((name, hashlib.sha256(raw).hexdigest(), blob_sha1(raw), len(raw)))
    (OUT / "MANIFEST.tsv").write_text(
        "path\tsha256\tgitBlobSha1\tbytes\n"
        + "".join(f"{a}\t{b}\t{c}\t{d}\n" for a, b, c, d in rows)
    )


if __name__ == "__main__":
    main()
