#!/usr/bin/env python3
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[1]
WORKFLOW = REPO_ROOT / '.github/workflows/arm-ena-sws-query-only-availability-v1.yml'


class LiveAuthorizationWorkflowFenceTests(unittest.TestCase):
    def workflow(self) -> str:
        return WORKFLOW.read_text(encoding='utf-8')

    def auth_job(self, workflow: str) -> str:
        try:
            return workflow.split('\n  query-only-discovery:', 1)[1]
        except IndexError:
            self.fail('query-only-discovery job block missing')

    def test_actual_workflow_has_ordered_pre_query_and_post_query_live_fence(self):
        workflow = self.workflow()
        auth = self.auth_job(workflow)
        header = auth.split('\n    steps:', 1)[0]
        self.assertIn("needs: exact-executable-stress", header)
        self.assertIn("if: github.event_name == 'workflow_dispatch'", header)
        self.assertNotIn('ARM_USER_ID:', header)
        self.assertNotIn('ARM_ACCESS_TOKEN:', header)

        pre = 'python "$PREFLIGHT_TOOL/preflight_query_authorization_live_v2.py" > "$pre"'
        presence = 'if [ -z "${ARM_USER_ID:-}" ] || [ -z "${ARM_ACCESS_TOKEN:-}" ]; then'
        query = 'python "$QUERY_TOOL/discover.py" --output "$query_dir/query-only-receipt.json"'
        post_comment = '--authorization-comment "$auth_comment"'
        post_title = '--authorization-title "$auth_title" > "$post"'
        query_upload = 'name: arm-ena-sws-query-only-availability-v1'

        for needle in (pre, presence, query, post_comment, post_title, query_upload):
            self.assertIn(needle, auth)
        self.assertGreaterEqual(auth.count('env -u ARM_USER_ID -u ARM_ACCESS_TOKEN'), 2)

        pre_i = auth.index(pre)
        presence_i = auth.index(presence)
        query_i = auth.index(query)
        post_i = auth.index(post_comment)
        post_title_i = auth.index(post_title)
        upload_i = auth.index(query_upload)
        self.assertLess(pre_i, presence_i)
        self.assertLess(presence_i, query_i)
        self.assertLess(query_i, post_i)
        self.assertLess(post_i, post_title_i)
        self.assertLess(post_title_i, upload_i)

    def test_actual_workflow_keeps_arm_credentials_step_scoped_and_off_command_line(self):
        auth = self.auth_job(self.workflow())
        self.assertIn('ARM_USER_ID: ${{ secrets.ARM_USER_ID }}', auth)
        self.assertIn('ARM_ACCESS_TOKEN: ${{ secrets.ARM_ACCESS_TOKEN }}', auth)
        self.assertNotIn('--user-id', auth)
        self.assertNotIn('--access-token', auth)
        self.assertNotIn('echo "${ARM_USER_ID', auth)
        self.assertNotIn('echo "${ARM_ACCESS_TOKEN', auth)

    def test_actual_workflow_persists_only_sanitized_query_and_control_receipts(self):
        auth = self.auth_job(self.workflow())
        self.assertIn('arm-ena-sws-query-only-live-preflight-v2', auth)
        self.assertIn('arm-ena-sws-query-only-availability-v1', auth)
        self.assertIn('query-only-receipt.json', auth)
        self.assertNotIn('*.nc', auth)
        self.assertNotIn('*.cdf', auth)
        self.assertNotIn('/saveData', auth)


if __name__ == '__main__':
    unittest.main(verbosity=2)
