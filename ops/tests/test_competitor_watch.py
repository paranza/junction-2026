import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError


spec = importlib.util.spec_from_file_location("competitor_watch", Path(__file__).resolve().parents[1] / "competitor_watch.py")
watch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(watch)

OLD = "a" * 40
NEW = "b" * 40
BASELINE = {"schema_version": 1, "repositories": [{"repo": "team/project", "default_branch": "main", "head_sha": OLD,
             "classification": "implemented", "pushed_at": "old"}], "discovery_queries": ["stoa junction", '"Make Blueprints Talk" in:readme']}


class FakeAPI:
    def __init__(self, repositories=None, searches=None):
        self.repositories = repositories or {}
        self.searches = searches or {}

    def repository(self, repo):
        result = self.repositories[repo]
        if isinstance(result, Exception):
            raise result
        return copy.deepcopy(result)

    def search(self, query):
        result = self.searches[query]
        if isinstance(result, Exception):
            raise result
        return copy.deepcopy(result)


def observed(sha=OLD, **extra):
    return {"repo": "team/project", "canonical_repo": "team/project", "default_branch": "main", "head_sha": sha,
            "head_commit_at": "2026-11-14T07:30:00Z", "pushed_at": "new metadata", "commit_url": "https://github.com/team/project/commit/" + sha, **extra}


class MonitorChecks(unittest.TestCase):
    def test_head_change_not_metadata_time_triggers_compare(self):
        baseline = copy.deepcopy(BASELINE)
        report, _ = watch.run_check(baseline, None, FakeAPI({"team/project": observed()}), skip_search=True)
        self.assertEqual(report["changes"], [])
        self.assertEqual(report["repositories"][0]["status"], "unchanged")
        report, state = watch.run_check(baseline, None, FakeAPI({"team/project": observed(NEW)}), skip_search=True)
        self.assertEqual(report["changes"][0]["compare_url"], f"https://github.com/team/project/compare/{OLD}...{NEW}")
        self.assertEqual(state["repositories"][0]["head_sha"], NEW)
        self.assertEqual(baseline, BASELINE)

    def test_failed_fetch_preserves_last_success_and_reports_partial_error(self):
        baseline = copy.deepcopy(BASELINE)
        baseline["repositories"].append({"repo": "other/project", "head_sha": OLD})
        state = {"schema_version": 1, "repositories": [{"repo": "team/project", "head_sha": NEW}]}
        api = FakeAPI({"team/project": watch.GitHubError("rate_limit", "rate limited"), "other/project": {**observed(), "repo": "other/project"}})
        report, next_state = watch.run_check(baseline, state, api, skip_search=True)
        self.assertEqual(report["status"], "partial_error")
        self.assertEqual(next_state["repositories"][0]["head_sha"], NEW)
        self.assertEqual(report["repositories"][0]["status"], "error")
        self.assertEqual(state["repositories"][0]["head_sha"], NEW)

    def test_unavailable_is_not_unchanged_or_erased(self):
        report, state = watch.run_check(BASELINE, None, FakeAPI({"team/project": watch.GitHubError("unavailable", "404")}), skip_search=True)
        self.assertEqual(report["status"], "error")
        self.assertEqual(report["summary"]["unavailable"], 1)
        self.assertEqual(state["repositories"][0]["head_sha"], OLD)

    def test_candidates_are_public_valid_deduplicated_and_unqualified(self):
        items = [{"full_name": "new/project", "private": False}, {"full_name": "TEAM/project", "private": False},
                 {"full_name": "private/project", "private": True}, {"full_name": "bad/../path", "private": False}]
        searches = {q: {"items": items, "total_count": 201, "incomplete_results": False} for q in BASELINE["discovery_queries"]}
        api = FakeAPI({"team/project": observed()}, searches)
        report, state = watch.run_check(BASELINE, None, api)
        self.assertEqual(len(report["candidates"]), 1)
        self.assertEqual(report["candidates"][0]["classification"], "candidate_needs_review")
        self.assertEqual(report["candidates"][0]["discovery_queries"], BASELINE["discovery_queries"])
        self.assertTrue(report["searches"][0]["truncated"])
        again, _ = watch.run_check(BASELINE, state, api)
        self.assertEqual(again["candidates"], [])

    def test_no_update_writes_report_but_preserves_state_and_baseline(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            baseline, state, output = (root / name for name in ("baseline.json", "state.json", "report.json"))
            baseline.write_text(json.dumps(BASELINE))
            original_state = {"schema_version": 1, "repositories": [{"repo": "team/project", "head_sha": OLD}]}
            state.write_text(json.dumps(original_state))
            before = baseline.read_bytes(), state.read_bytes()
            status = watch.main(["--baseline", str(baseline), "--state", str(state), "--output", str(output), "--skip-search", "--no-update"], api=FakeAPI({"team/project": observed(NEW)}))
            self.assertEqual(status, 0)
            self.assertEqual((baseline.read_bytes(), state.read_bytes()), before)
            self.assertEqual(json.loads(output.read_text())["summary"]["changed"], 1)

    def test_search_failure_does_not_hide_successful_repo_check(self):
        searches = {q: watch.GitHubError("rate_limit", "try later") for q in BASELINE["discovery_queries"]}
        report, state = watch.run_check(BASELINE, None, FakeAPI({"team/project": observed(NEW)}, searches))
        self.assertEqual(report["status"], "partial_error")
        self.assertEqual(state["repositories"][0]["head_sha"], NEW)
        self.assertEqual(len(report["errors"]), 2)

    def test_rate_limit_is_explicit_and_tls_failure_is_not_bypassed(self):
        api = watch.PublicGitHub()
        with patch.object(watch, "urlopen", side_effect=HTTPError("https://api.github.com", 403, "Forbidden", {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1234"}, None)):
            with self.assertRaises(watch.GitHubError) as caught:
                api.get("rate_limit")
        self.assertEqual(caught.exception.kind, "rate_limit")
        self.assertIn("1234", str(caught.exception))
        with patch.object(watch, "urlopen", side_effect=watch.URLError("CERTIFICATE_VERIFY_FAILED")):
            with self.assertRaises(watch.GitHubError) as caught:
                api.get("rate_limit")
        self.assertEqual(caught.exception.kind, "network_error")
        self.assertIn("do not disable verification", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
