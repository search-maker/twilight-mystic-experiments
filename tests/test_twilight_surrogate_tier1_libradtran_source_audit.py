from __future__ import annotations

import hashlib
import importlib.util
import io
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    ROOT
    / "experiments"
    / "mystic-batch-v1"
    / "twilight_surrogate_tier1_libradtran_source_audit.py"
)

spec = importlib.util.spec_from_file_location(
    "tier1_libradtran_source_audit",
    MODULE_PATH,
)
if spec is None or spec.loader is None:
    raise RuntimeError(f"cannot load {MODULE_PATH}")
AUDIT = importlib.util.module_from_spec(spec)
spec.loader.exec_module(AUDIT)


def add_text(
    archive: tarfile.TarFile,
    name: str,
    text: str,
) -> None:
    raw = text.encode()
    info = tarfile.TarInfo(name)
    info.size = len(raw)
    archive.addfile(info, io.BytesIO(raw))


def fixture(path: Path, *, valid: bool = True) -> str:
    with tarfile.open(path, "w:gz") as archive:
        add_text(
            archive,
            "libRadtran-2.0.6/src_py/lex_starter.l",
            """
if (Input.rte.solver== SOLVER_MONTECARLO &&
    Input.alt.altitude != NOT_DEFINED_FLOAT) {
  fprintf(stderr, "Error, option altitude does not work with\\n");
  fprintf(stderr, "       solver montecarlo! Use mc_elevation_file!\\n");
}
""",
        )
        add_text(
            archive,
            "libRadtran-2.0.6/src/cloud3d.c",
            """
if (strlen(input.rte.mc.filename[FN_MC_ELEVATION]) > 0) {
  status = setup_elevation2D(
      input.rte.mc.filename[FN_MC_ELEVATION],
      &output->mc.elev);
  output->mc.elev.elev2D = 1;
}
""",
        )
        add_text(
            archive,
            "libRadtran-2.0.6/src/elevation2d.c",
            "int setup_elevation2D (char *filename) { return 0; }\n",
        )
        add_text(
            archive,
            "libRadtran-2.0.6/src/atmosphere.c",
            (
                "double altitude = input.alt.altitude;\n"
                if valid
                else "double altitude = 0;\n"
            ),
        )
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SourceAuditTests(unittest.TestCase):
    def test_exact_source_is_preserved_with_no_equivalence_claim(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            archive = root / "source.tar.gz"
            expected = fixture(archive)
            report = AUDIT.audit_archive(
                archive,
                root / "out",
                expected,
            )
            self.assertEqual(
                report["status"],
                (
                    "EXACT_SOURCE_MECHANISMS_DISTINCT_"
                    "EQUIVALENCE_NOT_ESTABLISHED"
                ),
            )
            self.assertTrue(
                report["monteCarloAltitudeExplicitlyRejected"]
            )
            self.assertFalse(report["siteAltitudeEquivalenceEstablished"])
            self.assertFalse(report["authorizationPermitted"])
            self.assertFalse(
                report["ordinal2ScientificDispatchPermitted"]
            )
            self.assertEqual(report["solverExecutionCount"], 0)
            self.assertEqual(len(report["primarySourceFiles"]), 4)

    def test_changed_source_or_hash_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            archive = root / "source.tar.gz"
            expected = fixture(archive, valid=False)
            with self.assertRaises(AUDIT.SourceAuditError):
                AUDIT.audit_archive(
                    archive,
                    root / "out",
                    expected,
                )
            with self.assertRaises(AUDIT.SourceAuditError):
                AUDIT.audit_archive(
                    archive,
                    root / "out2",
                    "0" * 64,
                )


if __name__ == "__main__":
    unittest.main()
