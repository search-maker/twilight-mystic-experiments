import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "review" / "empirical-twilight-radiance-source-admission-v1"


def load_json(name):
    return json.loads((REVIEW / name).read_text(encoding="utf-8"))


def git_blob_sha1(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(f"blob {len(raw)}\0".encode("ascii") + raw).hexdigest()


class PgnRequestDispatchBindingV1Tests(unittest.TestCase):
    def test_source_admission_dispatch_and_actual_request_bytes_agree(self):
        request_path = REVIEW / "PGN_METADATA_REQUEST.md"
        actual = git_blob_sha1(request_path)
        dispatch = load_json("PGN_METADATA_REQUEST_DISPATCH.review.json")
        source = load_json("source-admission.review.json")

        self.assertEqual(actual, "4dfb2edb4d80c4cf91022016ebb6abe7f4cef036")
        self.assertEqual(dispatch["requestArtifact"]["gitBlobSha1AtDispatch"], actual)
        self.assertEqual(source["sourceBindings"]["metadataResolutionRequest"]["preSendGitBlobSha1"], actual)
        self.assertTrue(dispatch["requestArtifact"]["frozenBeforeDispatch"])
        self.assertTrue(source["sourceBindings"]["metadataResolutionRequest"]["sent"])
        self.assertFalse(dispatch["blindnessBoundary"]["targetLevel1DataOpenedForThisValidation"])


if __name__ == "__main__":
    unittest.main()
