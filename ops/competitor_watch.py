#!/usr/bin/env python3
"""Check public GitHub heads and discover candidates without running their code.

The committed snapshot is an input, never an output. Successful observations and
seen discovery candidates live in ignored .local state. Candidates require a
human source review before they can be called Stoa competitors.
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import ssl
import sys
import tempfile
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
REPO_PATTERN = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?/(?!(?:\.|\.\.)\Z)[A-Za-z0-9_.-]+\Z")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


class GitHubError(Exception):
    def __init__(self, kind: str, message: str):
        super().__init__(message)
        self.kind = kind


class PublicGitHub:
    """Unauthenticated, certificate-verified GitHub REST reads only."""

    def __init__(self, timeout: float = 15):
        self.timeout = timeout

    def get(self, path: str) -> dict | list:
        request = Request("https://api.github.com/" + path, headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "Trace-public-research-watch/1.0",
            "X-GitHub-Api-Version": "2022-11-28",
        })
        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = response.read(8 * 1024 * 1024 + 1)
                if len(payload) > 8 * 1024 * 1024:
                    raise GitHubError("response_too_large", "GitHub response exceeded the read limit.")
                return json.loads(payload)
        except HTTPError as exc:
            if exc.code == 404:
                raise GitHubError("unavailable", "Public resource not found (404); it may be renamed, removed or private.") from None
            if exc.code == 429 or (exc.code == 403 and exc.headers.get("X-RateLimit-Remaining") == "0"):
                reset = exc.headers.get("X-RateLimit-Reset", "unknown")
                raise GitHubError("rate_limit", f"GitHub public API rate limit reached; reset epoch: {reset}.") from None
            raise GitHubError("http_error", f"GitHub returned HTTP {exc.code}; retry later without changing the saved head.") from None
        except (URLError, TimeoutError, ssl.SSLError) as exc:
            detail = str(exc)
            if "CERTIFICATE_VERIFY_FAILED" in detail:
                detail = "TLS certificate verification failed. Configure SSL_CERT_FILE with a trusted CA bundle; do not disable verification."
            raise GitHubError("network_error", detail[:400]) from None
        except (ValueError, UnicodeError):
            raise GitHubError("invalid_response", "GitHub returned invalid JSON.") from None

    def repository(self, repo: str) -> dict:
        metadata = self.get("repos/" + quote(repo, safe="/"))
        if not isinstance(metadata, dict) or metadata.get("private") is not False:
            raise GitHubError("invalid_response", "Expected public repository metadata.")
        branch = metadata.get("default_branch")
        if not isinstance(branch, str) or not branch:
            raise GitHubError("invalid_response", "Repository has no usable default branch.")
        commits = self.get("repos/" + quote(repo, safe="/") + "/commits?" + urlencode({"sha": branch, "per_page": 1}))
        if not isinstance(commits, list) or not commits:
            raise GitHubError("invalid_response", "No default-branch commit was returned.")
        head = commits[0]
        if not isinstance(head, dict) or not isinstance(head.get("commit"), dict):
            raise GitHubError("invalid_response", "GitHub returned an invalid commit record.")
        sha = head.get("sha", "")
        if not isinstance(sha, str) or re.fullmatch(r"[0-9a-f]{40}", sha) is None:
            raise GitHubError("invalid_response", "GitHub returned an invalid commit SHA.")
        actual_repo = metadata.get("full_name", repo)
        if not isinstance(actual_repo, str) or REPO_PATTERN.fullmatch(actual_repo) is None:
            raise GitHubError("invalid_response", "GitHub returned an invalid repository name.")
        commit = head["commit"]
        committer = commit.get("committer") or {}
        message = commit.get("message") or ""
        if not isinstance(committer, dict) or not isinstance(message, str):
            raise GitHubError("invalid_response", "GitHub returned invalid commit details.")
        return {
            "repo": repo,
            "canonical_repo": actual_repo,
            "default_branch": branch,
            "head_sha": sha,
            "head_commit_at": committer.get("date"),
            "head_title": message.split("\n", 1)[0][:500],
            "pushed_at": metadata.get("pushed_at"),
            "commit_url": f"https://github.com/{actual_repo}/commit/{sha}",
        }

    def search(self, query: str) -> dict:
        result = self.get("search/repositories?" + urlencode({"q": query, "per_page": 100, "sort": "updated", "order": "desc"}))
        if not isinstance(result, dict) or not isinstance(result.get("items"), list):
            raise GitHubError("invalid_response", "GitHub returned invalid repository search results.")
        return result


def run_check(baseline: dict, state: dict | None, api: PublicGitHub, *, skip_search: bool = False, checked_at: str | None = None) -> tuple[dict, dict]:
    """Return a report and next local state; never mutate the supplied baseline."""
    checked_at = checked_at or utc_now()
    if baseline.get("schema_version") != 1 or not isinstance(baseline.get("repositories"), list):
        raise ValueError("Expected a version 1 baseline with a repositories list.")
    state = copy.deepcopy(state or {})
    if state and state.get("schema_version") != 1:
        raise ValueError("Unsupported local state version; preserve the file and inspect it.")
    prior = {entry["repo"].lower(): entry for entry in state.get("repositories", [])}
    known: dict[str, dict] = {}
    for entry in baseline["repositories"]:
        repo = entry.get("repo", "")
        if not isinstance(repo, str) or REPO_PATTERN.fullmatch(repo) is None:
            raise ValueError("Baseline contains an invalid owner/repository name.")
        key = repo.lower()
        if key in known:
            raise ValueError("Baseline contains a duplicate repository.")
        # The current baseline owns classification; local state owns observed heads.
        previous = prior.get(key, {})
        known[key] = {**copy.deepcopy(entry), **{k: v for k, v in previous.items() if k in {
            "head_sha", "head_commit_at", "head_title", "default_branch", "pushed_at", "commit_url", "canonical_repo", "last_success_at"
        }}}
    next_repositories = copy.deepcopy(known)
    report = {"schema_version": 1, "checked_at": checked_at, "status": "ok", "repositories": [],
              "changes": [], "unavailable": [], "errors": [], "candidates": [], "searches": []}
    for key, previous in known.items():
        repo = previous["repo"]
        try:
            current = api.repository(repo)
            old_sha = previous.get("head_sha")
            changed = old_sha != current["head_sha"]
            status = "new" if not old_sha else "changed" if changed else "unchanged"
            observed = {**current, "status": status, "classification": previous.get("classification", "watchlist")}
            if changed:
                observed["previous_head_sha"] = old_sha
                if old_sha:
                    observed["compare_url"] = f"https://github.com/{current.get('canonical_repo', repo)}/compare/{old_sha}...{current['head_sha']}"
                report["changes"].append(copy.deepcopy(observed))
            report["repositories"].append(observed)
            next_repositories[key] = {**previous, **current, "last_success_at": checked_at}
        except GitHubError as exc:
            failure = {"repo": repo, "kind": exc.kind, "message": str(exc)}
            report["repositories"].append({**previous, "status": "unavailable" if exc.kind == "unavailable" else "error"})
            report["errors"].append(failure)
            if exc.kind == "unavailable":
                report["unavailable"].append(failure)
    seen = {name.lower() for name in state.get("seen_candidates", [])}
    candidates: dict[str, dict] = {}
    if not skip_search:
        for query in baseline.get("discovery_queries", []):
            if not isinstance(query, str) or not query.strip():
                raise ValueError("Each discovery query must be a nonempty string.")
            try:
                result = api.search(query)
                items = result["items"][:100]
                report["searches"].append({"query": query, "total_count": result.get("total_count"), "returned_count": len(items),
                                           "incomplete_results": bool(result.get("incomplete_results")),
                                           "truncated": result.get("total_count", 0) > 100})
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    repo = item.get("full_name", "")
                    if not isinstance(repo, str) or REPO_PATTERN.fullmatch(repo) is None or item.get("private") is not False:
                        continue
                    key = repo.lower()
                    if key in known or key in seen:
                        continue
                    candidate = candidates.setdefault(key, {"repo": repo, "url": f"https://github.com/{repo}",
                        "description": item.get("description"), "default_branch": item.get("default_branch"),
                        "pushed_at": item.get("pushed_at"), "classification": "candidate_needs_review", "discovery_queries": []})
                    if query not in candidate["discovery_queries"]:
                        candidate["discovery_queries"].append(query)
            except GitHubError as exc:
                report["errors"].append({"query": query, "kind": exc.kind, "message": str(exc)})
    report["candidates"] = sorted(candidates.values(), key=lambda entry: entry["repo"].lower())
    if report["errors"]:
        successful = any(entry["status"] not in {"error", "unavailable"} for entry in report["repositories"]) or bool(report["searches"])
        report["status"] = "partial_error" if successful else "error"
    report["summary"] = {"changed": len(report["changes"]), "new_candidates": len(report["candidates"]),
                          "unavailable": len(report["unavailable"]), "errors": len(report["errors"])}
    next_state = {"schema_version": 1, "checked_at": checked_at,
                  "repositories": list(next_repositories.values()), "seen_candidates": sorted(seen | set(candidates))}
    return report, next_state


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, prefix=path.name + ".", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(data, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def main(argv: list[str] | None = None, *, api: PublicGitHub | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=ROOT / "docs/research/stoa-competitor-snapshot.json")
    parser.add_argument("--state", type=Path, default=ROOT / ".local/stoa-competitor-watch/state.json")
    parser.add_argument("--output", type=Path, default=ROOT / ".local/stoa-competitor-watch/latest.json")
    parser.add_argument("--skip-search", action="store_true", help="Only check known repositories")
    parser.add_argument("--no-update", action="store_true", help="Write the report without changing local state")
    parser.add_argument("--timeout", type=float, default=15, help="Seconds per public API request, from 1 to 60")
    args = parser.parse_args(argv)
    if not 1 <= args.timeout <= 60:
        parser.error("--timeout must be from 1 to 60 seconds")
    if len({args.baseline.resolve(), args.state.resolve(), args.output.resolve()}) != 3:
        parser.error("Baseline, local state and output must be separate files")
    try:
        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
        state = json.loads(args.state.read_text(encoding="utf-8")) if args.state.exists() else None
        report, next_state = run_check(baseline, state, api or PublicGitHub(args.timeout), skip_search=args.skip_search)
        write_json(args.output, report)
        if not args.no_update:
            write_json(args.state, next_state)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"Monitor configuration/output error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"status": report["status"], **report["summary"], "report": str(args.output), "state_updated": not args.no_update}))
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
