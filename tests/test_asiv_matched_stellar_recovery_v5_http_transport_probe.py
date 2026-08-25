import importlib.util
import io
import json
import urllib.error
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "review/asiv-matched-stellar-transport-v1/recovery-v5-transport-probe/read_only_github_rest_v5.py"
EXPECTED_HELPER_BLOB = "2bc293c7db73c436ba422f80566513459df77c7e"


def load_helper():
    spec = importlib.util.spec_from_file_location("matched_stellar_rest_v5", HELPER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FakeResponse:
    def __init__(self, payload, status=200, headers=None):
        self._raw = json.dumps(payload).encode("utf-8")
        self.status = status
        self.headers = headers or {}

    def read(self):
        return self._raw

    def getcode(self):
        return self.status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class RecoveryV5DirectRestTransportProbeTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_helper()

    def test_helper_blob_and_frozen_retry_policy(self):
        import hashlib
        data = HELPER.read_bytes()
        observed = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
        self.assertEqual(observed, EXPECTED_HELPER_BLOB)
        self.assertEqual(self.mod.API_BASE, "https://api.github.com")
        self.assertEqual(self.mod.API_VERSION, "2022-11-28")
        self.assertEqual(self.mod.TRANSIENT_HTTP_STATUSES, {502, 503, 504})
        self.assertEqual(self.mod.MAX_ATTEMPTS, 8)
        self.assertEqual(self.mod.BACKOFF_SECONDS, (2, 4, 8, 16, 30, 30, 30))
        self.assertEqual(self.mod.MAX_PAGES, 20)

    def test_request_is_get_only_and_token_is_header_only(self):
        req = self.mod._request("https://api.github.com/repos/search-maker/twilight-mystic-experiments/actions/runs/1", "secret-token")
        self.assertEqual(req.get_method(), "GET")
        self.assertNotIn("secret-token", req.full_url)
        headers = {k.lower(): v for k, v in req.header_items()}
        self.assertEqual(headers["authorization"], "Bearer secret-token")
        self.assertEqual(headers["x-github-api-version"], "2022-11-28")

    def test_non_github_or_other_repository_urls_are_refused(self):
        for url in (
            "http://api.github.com/repos/search-maker/twilight-mystic-experiments/actions/runs/1",
            "https://example.com/repos/search-maker/twilight-mystic-experiments/actions/runs/1",
            "https://api.github.com/repos/other/repo/actions/runs/1",
            "https://user:pass@api.github.com/repos/search-maker/twilight-mystic-experiments/actions/runs/1",
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                self.mod._assert_allowed_url(url, "search-maker/twilight-mystic-experiments")

    def test_three_502s_then_success_use_frozen_backoff(self):
        calls = []
        sleeps = []

        def opener(req, timeout):
            calls.append((req.get_method(), req.full_url, timeout))
            if len(calls) <= 3:
                raise urllib.error.HTTPError(req.full_url, 502, "bad gateway", {}, io.BytesIO())
            return FakeResponse({"id": 1})

        payload, audit = self.mod.get_json(
            "https://api.github.com/repos/search-maker/twilight-mystic-experiments/actions/runs/1",
            repo="search-maker/twilight-mystic-experiments",
            token="t",
            opener=opener,
            sleeper=sleeps.append,
        )
        self.assertEqual(payload, {"id": 1})
        self.assertEqual([x["httpStatus"] for x in audit["attempts"]], [502, 502, 502, 200])
        self.assertEqual(sleeps, [2, 4, 8])
        self.assertTrue(all(method == "GET" for method, _, _ in calls))
        self.assertFalse(audit["writeMethodPermitted"])

    def test_nontransient_http_error_is_not_retried(self):
        calls = []
        def opener(req, timeout):
            calls.append(req.full_url)
            raise urllib.error.HTTPError(req.full_url, 404, "not found", {}, io.BytesIO())
        with self.assertRaises(urllib.error.HTTPError):
            self.mod.get_json(
                "https://api.github.com/repos/search-maker/twilight-mystic-experiments/actions/runs/1",
                repo="search-maker/twilight-mystic-experiments",
                token="t",
                opener=opener,
                sleeper=lambda _: None,
            )
        self.assertEqual(len(calls), 1)

    def test_paginated_jobs_follow_only_exact_repository_next_links(self):
        first = "https://api.github.com/repos/search-maker/twilight-mystic-experiments/actions/runs/1/jobs?per_page=100"
        second = "https://api.github.com/repos/search-maker/twilight-mystic-experiments/actions/runs/1/jobs?per_page=100&page=2"
        payloads = {
            first: FakeResponse({"jobs": [{"id": 1}]}, headers={"Link": f'<{second}>; rel="next"'}),
            second: FakeResponse({"jobs": [{"id": 2}]}, headers={}),
        }
        rows, audits = self.mod.get_paginated(
            first,
            repo="search-maker/twilight-mystic-experiments",
            token="t",
            list_key="jobs",
            opener=lambda req, timeout: payloads[req.full_url],
            sleeper=lambda _: None,
        )
        self.assertEqual([x["id"] for x in rows], [1, 2])
        self.assertEqual(len(audits), 2)

    def test_run_bundle_uses_fixed_run_jobs_artifact_get_endpoints(self):
        seen = []
        repo = "search-maker/twilight-mystic-experiments"
        run_id = 123
        def opener(req, timeout):
            seen.append((req.get_method(), req.full_url))
            if req.full_url.endswith(f"/actions/runs/{run_id}"):
                return FakeResponse({"id": run_id, "status": "completed"})
            if "/jobs?" in req.full_url:
                return FakeResponse({"jobs": [{"id": 9}]})
            if "/artifacts?" in req.full_url:
                return FakeResponse({"artifacts": []})
            raise AssertionError(req.full_url)
        bundle = self.mod.fetch_run_bundle(repo, run_id, token="t", opener=opener, sleeper=lambda _: None)
        self.assertEqual(bundle["run"]["id"], run_id)
        self.assertEqual(bundle["jobs"], [{"id": 9}])
        self.assertEqual(bundle["artifacts"], [])
        self.assertEqual(len(seen), 3)
        self.assertTrue(all(method == "GET" for method, _ in seen))
        self.assertTrue(all(url.startswith(f"https://api.github.com/repos/{repo}/actions/runs/{run_id}") for _, url in seen))
        self.assertFalse(bundle["audit"]["writeMethodsPermitted"])

    def test_pull_request_transport_is_exact_single_get(self):
        seen = []
        def opener(req, timeout):
            seen.append((req.get_method(), req.full_url))
            return FakeResponse({"number": 99, "state": "open", "draft": True})
        payload = self.mod.fetch_pull_request(
            "search-maker/twilight-mystic-experiments", 99, token="t", opener=opener, sleeper=lambda _: None
        )
        self.assertEqual(payload["pullRequest"]["number"], 99)
        self.assertEqual(seen, [("GET", "https://api.github.com/repos/search-maker/twilight-mystic-experiments/pulls/99")])

    def test_source_has_no_subprocess_or_solver_execution_surface(self):
        text = HELPER.read_text(encoding="utf-8")
        self.assertNotIn("subprocess", text)
        self.assertNotIn("uvspec", text)
        self.assertNotIn("micromamba", text)
        self.assertNotIn("workflow_dispatch", text)
        self.assertNotIn("POST", text)
        self.assertNotIn("PATCH", text)
        self.assertNotIn("DELETE", text)


if __name__ == "__main__":
    unittest.main()
