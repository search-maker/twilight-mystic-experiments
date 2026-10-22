#!/usr/bin/env python3
"""Result-blind source audit for MYSTIC spectral zero serialization.

This is a POST_V1/NONBLOCKING reference checker.  It reads source text only;
it never runs uvspec/MYSTIC and never opens scientific result artifacts.

The narrow question answered by a PASS is whether the inspected libRadtran
source has the expected *final spectral serializer boundary*:

* multi-wavelength MYSTIC disables the monochromatic file writer;
* the spectral writer creates ``<mc_basename>.rad.spc``;
* the value written is the stored ``output->radiance3d[...]`` float;
* the final conversion uses C ``%g``, not a fixed-decimal formatter or an
  explicit epsilon/threshold substitution.

A PASS therefore supports only this implication for a conforming C printf:
if a serialized finite token parses numerically as zero, the stored float at
that final serializer boundary was +0 or -0.  It does NOT prove that the true
radiance is zero, that no upstream arithmetic underflow occurred, that the
Monte-Carlo estimator converged, that scores are nonnegative, or that the
inspected source is byte-equivalent to a historical source archive.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
import unittest
from pathlib import Path
from typing import Any


class AuditRefusal(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_file(root: Path, relative: str) -> str:
    path = root / relative
    if not path.is_file():
        raise AuditRefusal(f"required source file missing: {relative}")
    return path.read_text(encoding="utf-8", errors="strict")


def require_regex(text: str, pattern: str, label: str) -> None:
    if re.search(pattern, text, flags=re.MULTILINE | re.DOTALL) is None:
        raise AuditRefusal(f"required source semantic not found: {label}")


def audit_source_root(root: Path) -> dict[str, Any]:
    root = root.resolve()
    solve = require_file(root, "src/solve_rte.c")
    ancillary = require_file(root, "src/ancillary.c")
    header = require_file(root, "src/uvspec.h")

    require_regex(
        solve,
        r"write_files\s*=\s*\(\s*output->wl\.nlambda_r\s*\*\s*"
        r"output->atm\.nq_r\[output->wl\.nlambda_rte_lower\]\s*>\s*1\s*"
        r"\?\s*0\s*:\s*1\s*\)\s*;",
        "multi-wavelength write_files=0 gate",
    )
    require_regex(
        ancillary,
        r"strcat\s*\(\s*radfilename\s*,\s*\"\.rad\.spc\"\s*\)\s*;",
        "rad.spc filename construction",
    )
    require_regex(
        ancillary,
        r"fprintf\s*\(\s*frad\s*,\s*\"%9\.5f\s+%4d\s+%4d\s+%4d\s+%g\\n\"\s*,"
        r"\s*output->wl\.lambda_h\s*\[\s*iv\s*\]\s*,"
        r"\s*is\s*,\s*js\s*,\s*ks\s*,"
        r"\s*output->radiance3d\s*\[\s*ks\s*\]\s*\[\s*is\s*\]\s*"
        r"\[\s*js\s*\]\s*\[\s*ip\s*\]\s*\[\s*ic\s*\]\s*"
        r"\[\s*iv\s*\]\s*\)\s*;",
        "direct %g serialization of output->radiance3d",
    )
    require_regex(
        header,
        r"float\s+\*{6}radiance3d\s*;",
        "spectral radiance storage is float",
    )

    paths = ["src/solve_rte.c", "src/ancillary.c", "src/uvspec.h"]
    return {
        "schemaVersion": 1,
        "status": "SERIALIZER_BOUNDARY_CERTIFIED_SOURCE_LOCAL_ONLY",
        "resultBlind": True,
        "solverExecuted": False,
        "zeroSubstitutionUsed": False,
        "certifiedImplication": (
            "for a conforming C printf, a finite mc.rad.spc value token that parses "
            "as numeric zero came from a +0/-0 stored float at the final serializer boundary"
        ),
        "notCertified": [
            "physical radiance is exactly zero",
            "absence of upstream floating-point underflow",
            "Monte-Carlo convergence or estimator negligibility",
            "per-history score nonnegativity",
            "historical source-byte equivalence",
        ],
        "sourceSha256": {relative: sha256(root / relative) for relative in paths},
    }


class ReferenceTests(unittest.TestCase):
    SOLVE = """
      int write_files=0;
      write_files = (output->wl.nlambda_r * output->atm.nq_r[output->wl.nlambda_rte_lower] > 1 ? 0 : 1);
    """
    ANCILLARY = r'''
      strcpy (radfilename, input.rte.mc.filename[FN_MC_BASENAME]);
      strcat (radfilename, ".rad.spc");
      for (ip=0; ip<input.rte.mc.nstokes; ip++)
        for (ic=0; ic<output->mc.alis.Nc; ic++)
          fprintf (frad, "%9.5f %4d %4d %4d %g\n",
                   output->wl.lambda_h[iv], is, js, ks,
                   output->radiance3d[ks][is][js][ip][ic][iv]);
    '''
    HEADER = "float       ******radiance3d;"

    def make_root(self, *, solve: str | None = None, ancillary: str | None = None, header: str | None = None) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        (root / "src").mkdir()
        (root / "src/solve_rte.c").write_text(self.SOLVE if solve is None else solve)
        (root / "src/ancillary.c").write_text(self.ANCILLARY if ancillary is None else ancillary)
        (root / "src/uvspec.h").write_text(self.HEADER if header is None else header)
        return temp, root

    def test_expected_fixture_passes(self) -> None:
        temp, root = self.make_root()
        self.addCleanup(temp.cleanup)
        report = audit_source_root(root)
        self.assertEqual(report["status"], "SERIALIZER_BOUNDARY_CERTIFIED_SOURCE_LOCAL_ONLY")
        self.assertFalse(report["solverExecuted"])
        self.assertFalse(report["zeroSubstitutionUsed"])

    def test_fixed_decimal_writer_fails_closed(self) -> None:
        bad = self.ANCILLARY.replace("%g\\n", "%.6f\\n")
        temp, root = self.make_root(ancillary=bad)
        self.addCleanup(temp.cleanup)
        with self.assertRaisesRegex(AuditRefusal, "direct %g serialization"):
            audit_source_root(root)

    def test_epsilon_like_rewrite_breaks_direct_writer_contract(self) -> None:
        bad = self.ANCILLARY.replace(
            "output->radiance3d[ks][is][js][ip][ic][iv]",
            "fabs(output->radiance3d[ks][is][js][ip][ic][iv]) < 1e-12 ? 0 : output->radiance3d[ks][is][js][ip][ic][iv]",
        )
        temp, root = self.make_root(ancillary=bad)
        self.addCleanup(temp.cleanup)
        with self.assertRaisesRegex(AuditRefusal, "direct %g serialization"):
            audit_source_root(root)

    def test_missing_multi_wavelength_gate_fails_closed(self) -> None:
        temp, root = self.make_root(solve="int write_files = 1;")
        self.addCleanup(temp.cleanup)
        with self.assertRaisesRegex(AuditRefusal, "multi-wavelength"):
            audit_source_root(root)

    def test_double_storage_drift_fails_closed(self) -> None:
        temp, root = self.make_root(header="double ******radiance3d;")
        self.addCleanup(temp.cleanup)
        with self.assertRaisesRegex(AuditRefusal, "storage is float"):
            audit_source_root(root)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(ReferenceTests)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        return 0 if result.wasSuccessful() else 1
    if args.source_root is None:
        parser.error("--source-root is required unless --self-test is used")
    try:
        report = audit_source_root(args.source_root)
    except AuditRefusal as exc:
        print(json.dumps({"status": "REFUSED", "reason": str(exc)}, indent=2, sort_keys=True))
        return 2
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
