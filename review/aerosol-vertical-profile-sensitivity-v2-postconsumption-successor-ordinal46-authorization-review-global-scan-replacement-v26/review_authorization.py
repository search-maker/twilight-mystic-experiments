from __future__ import annotations

import ast
import base64
import hashlib
import json
import os
import re
import zlib
from pathlib import Path

V25_PAYLOAD_SHA256 = "e99dcdbb408db224f13411cf3fa2ba205a36fe3d768ca8176538d10ea08a86a8"
_B85_ALPHABET = set("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz!#$%&()*+-;<=>?@^_`{|}~")


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _launcher_failure(exc: BaseException) -> None:
    if os.environ.get("V26_PREACTUAL_ACTIVE") != "1":
        return
    raw_dir = os.environ.get("V26_PREACTUAL_FAILURE_DIR")
    if not raw_dir:
        return
    out = Path(raw_dir) / "failure.json"
    payload = {
        "status": "FAIL_V26_PREACTUAL_BASE85_LAUNCHER_SERIALIZATION",
        "type": type(exc).__name__,
        "message": str(exc),
        "protectedAuthorizationReview": False,
        "ordinal46Allocated": False,
        "ordinal46Reserved": False,
        "ordinal46Dispatched": False,
        "candidateSeedsConsumed": False,
        "scienceFalse": True,
    }
    _atomic_json(out, payload)


def _single_assignment_string(tree: ast.AST, name: str) -> str:
    vals: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name) and target.id == name and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            vals.append(node.value.value)
    if len(vals) != 1:
        raise RuntimeError(f"V26 frozen V25 {name} assignment count drift: {len(vals)}")
    return vals[0]


def _prepare_lifted_payload() -> bytes:
    src_raw = os.environ.get("V25_FROZEN_REVIEWER")
    if not src_raw:
        raise RuntimeError("V26 V25_FROZEN_REVIEWER missing")
    src = Path(src_raw).resolve()
    text = src.read_text(encoding="utf-8")
    if "\r" in text:
        raise RuntimeError("V26 frozen V25 launcher contains noncanonical CR whitespace")

    tree = ast.parse(text, filename=str(src))
    bound_sha = _single_assignment_string(tree, "PAYLOAD_SHA256")
    if bound_sha != V25_PAYLOAD_SHA256:
        raise RuntimeError(f"V26 frozen V25 payload SHA binding drift: {bound_sha}")

    pattern = re.compile(r'^PAYLOAD_B85 = r"""(.*?)"""$', re.MULTILINE | re.DOTALL)
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        raise RuntimeError(f"V26 frozen V25 PAYLOAD_B85 physical block count drift: {len(matches)}")
    payload_text = matches[0].group(1)
    if not payload_text or payload_text.startswith("\n") or payload_text.endswith("\n"):
        raise RuntimeError("V26 frozen V25 PAYLOAD_B85 edge newline drift")
    if "\t" in payload_text or " " in payload_text or "\r" in payload_text:
        raise RuntimeError("V26 frozen V25 PAYLOAD_B85 noncanonical whitespace")
    lines = payload_text.split("\n")
    if not lines or any(not line for line in lines):
        raise RuntimeError("V26 frozen V25 PAYLOAD_B85 blank physical line drift")
    line_lengths = [len(line) for line in lines]
    if line_lengths[0] != 72:
        raise RuntimeError(f"V26 frozen V25 first Base85 physical line length drift: {line_lengths[0]}")
    for index, line in enumerate(lines, 1):
        bad = [ch for ch in line if ch not in _B85_ALPHABET]
        if bad:
            raise RuntimeError(f"V26 frozen V25 Base85 invalid char line {index}: {bad[0]!r}")

    direct_refusal = None
    try:
        base64.b85decode(payload_text.encode("ascii"))
    except ValueError as exc:
        direct_refusal = str(exc)
    if direct_refusal != "bad base85 character at position 72":
        raise RuntimeError(f"V26 direct multiline Base85 refusal drift: {direct_refusal!r}")

    canonical = "".join(lines)
    canonical_bytes = canonical.encode("ascii")
    compressed = base64.b85decode(canonical_bytes)
    roundtrip = base64.b85encode(compressed).decode("ascii")
    if roundtrip != canonical:
        raise RuntimeError("V26 canonical Base85 serializer round-trip drift")
    raw_v25 = zlib.decompress(compressed)
    raw_sha = hashlib.sha256(raw_v25).hexdigest()
    if raw_sha != V25_PAYLOAD_SHA256:
        raise RuntimeError(f"V26 decompressed V25 payload SHA drift: {raw_sha}")
    compile(raw_v25, "<v25-frozen-carried-payload>", "exec", flags=ast.PyCF_ONLY_AST, dont_inherit=True)

    upper_count = raw_v25.count(b"V25")
    lower_count = raw_v25.count(b"v25")
    if upper_count == 0 or lower_count == 0:
        raise RuntimeError(f"V26 carried version-token cardinality drift: V25={upper_count} v25={lower_count}")
    lifted = raw_v25.replace(b"V25", b"V26").replace(b"v25", b"v26")
    if len(lifted) != len(raw_v25):
        raise RuntimeError("V26 carried version lift changed payload byte length")
    if b"V25" in lifted or b"v25" in lifted:
        raise RuntimeError("V26 carried version lift left stale V25/v25 token")
    compile(lifted, "<v26-generated-carried-payload>", "exec", flags=ast.PyCF_ONLY_AST, dont_inherit=True)

    proof_path = os.environ.get("V26_LAUNCHER_PROOF_OUT")
    if proof_path:
        proof = {
            "status": "PASS_V26_PREACTUAL_BASE85_CANONICAL_TRANSPORT",
            "frozenV25Launcher": str(src),
            "boundPayloadSha256": bound_sha,
            "physicalLineCount": len(lines),
            "physicalLineLengths": line_lengths,
            "firstPhysicalLineLength": line_lengths[0],
            "multilineEncodedCharCount": len(payload_text),
            "canonicalEncodedCharCount": len(canonical),
            "directMultilineDecodeRefusal": direct_refusal,
            "canonicalCompressedByteCount": len(compressed),
            "canonicalCompressedSha256": hashlib.sha256(compressed).hexdigest(),
            "serializerRoundTripExact": True,
            "decompressedByteCount": len(raw_v25),
            "decompressedSha256": raw_sha,
            "rawByteShaBindingExact": True,
            "v25UpperTokenCount": upper_count,
            "v25LowerTokenCount": lower_count,
            "liftedByteCount": len(lifted),
            "liftedSha256": hashlib.sha256(lifted).hexdigest(),
            "liftedParserOk": True,
            "executionTargetEqualsProofTarget": True,
            "protectedAuthorizationReview": False,
            "ordinal46Allocated": False,
            "ordinal46Reserved": False,
            "ordinal46Dispatched": False,
            "candidateSeedsConsumed": False,
            "scienceFalse": True,
        }
        _atomic_json(Path(proof_path), proof)
    return lifted


try:
    _lifted = _prepare_lifted_payload()
except BaseException as _exc:
    _launcher_failure(_exc)
    raise

exec(compile(_lifted, str(Path(__file__).resolve()), "exec"), globals(), globals())
