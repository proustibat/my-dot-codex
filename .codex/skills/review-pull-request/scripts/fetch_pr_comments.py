#!/usr/bin/env python3
"""
Fetch all PR conversation comments + reviews + review threads (inline threads)
for a given PR (or the PR associated with the current git branch).

Usage:
  python3 scripts/fetch_pr_comments.py
  python3 scripts/fetch_pr_comments.py 3698
  python3 scripts/fetch_pr_comments.py "#3698"
  python3 scripts/fetch_pr_comments.py https://github.com/org/repo/pull/3698

Requires:
  - `gh auth login` already set up

Output JSON:
  {
    "pull_request": {number, url, title, state, owner, repo},
    "conversation_comments": [...],
    "reviews": [...],
    "review_threads": [...]
  }
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from typing import Any, Optional, Tuple

QUERY = """\
query(
  $owner: String!,
  $repo: String!,
  $number: Int!,
  $commentsCursor: String,
  $reviewsCursor: String,
  $threadsCursor: String
) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $number) {
      number
      url
      title
      state

      comments(first: 100, after: $commentsCursor) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          body
          createdAt
          updatedAt
          author { login }
        }
      }

      reviews(first: 100, after: $reviewsCursor) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          state
          body
          submittedAt
          author { login }
        }
      }

      reviewThreads(first: 100, after: $threadsCursor) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          isResolved
          isOutdated
          path
          line
          diffSide
          startLine
          startDiffSide
          originalLine
          originalStartLine
          comments(first: 100) {
            nodes {
              id
              body
              createdAt
              updatedAt
              author { login }
            }
          }
        }
      }
    }
  }
}
"""


def _run(cmd: list[str], stdin: Optional[str] = None) -> str:
    p = subprocess.run(cmd, input=stdin, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{p.stderr.strip()}")
    return p.stdout


def _run_json(cmd: list[str], stdin: Optional[str] = None) -> dict[str, Any]:
    out = _run(cmd, stdin=stdin)
    try:
        return json.loads(out)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse JSON from command output: {e}\nRaw:\n{out}") from e


def _ensure_gh_authenticated() -> None:
    try:
        _run(["gh", "auth", "status"])
    except Exception:
        raise RuntimeError("GitHub CLI is not authenticated. Run: gh auth login") from None


def _parse_pr_ref(arg: str) -> str:
    s = arg.strip()

    if re.fullmatch(r"#\d+", s):
        return s.lstrip("#")

    if re.fullmatch(r"\d+", s):
        return s

    m = re.search(r"/pull/(\d+)", s)
    if m:
        return s  # keep URL, gh can resolve it

    raise ValueError(f"Invalid PR reference: {arg!r}. Expected a number (e.g. 3698), #3698, or a PR URL.")


def _get_pr_owner_repo_number(pr_ref: Optional[str]) -> Tuple[str, str, int]:
    """
    Resolve PR number + head repo owner/name. Works for cross-repo PRs too.
    If pr_ref is None, resolves the PR associated with current branch.
    """
    fields = "number,headRepositoryOwner,headRepository"
    cmd = ["gh", "pr", "view"]
    if pr_ref:
        cmd.append(pr_ref)
    cmd += ["--json", fields]

    pr = _run_json(cmd)
    owner = pr["headRepositoryOwner"]["login"]
    repo = pr["headRepository"]["name"]
    number = int(pr["number"])
    return owner, repo, number


def _gh_api_graphql(
        owner: str,
        repo: str,
        number: int,
        comments_cursor: Optional[str] = None,
        reviews_cursor: Optional[str] = None,
        threads_cursor: Optional[str] = None,
) -> dict[str, Any]:
    cmd = [
        "gh",
        "api",
        "graphql",
        "-F",
        "query=@-",
        "-F",
        f"owner={owner}",
        "-F",
        f"repo={repo}",
        "-F",
        f"number={number}",
    ]
    if comments_cursor:
        cmd += ["-F", f"commentsCursor={comments_cursor}"]
    if reviews_cursor:
        cmd += ["-F", f"reviewsCursor={reviews_cursor}"]
    if threads_cursor:
        cmd += ["-F", f"threadsCursor={threads_cursor}"]

    return _run_json(cmd, stdin=QUERY)


def fetch_all(owner: str, repo: str, number: int) -> dict[str, Any]:
    conversation_comments: list[dict[str, Any]] = []
    reviews: list[dict[str, Any]] = []
    review_threads: list[dict[str, Any]] = []

    comments_cursor: Optional[str] = None
    reviews_cursor: Optional[str] = None
    threads_cursor: Optional[str] = None

    pr_meta: Optional[dict[str, Any]] = None

    while True:
        payload = _gh_api_graphql(
            owner=owner,
            repo=repo,
            number=number,
            comments_cursor=comments_cursor,
            reviews_cursor=reviews_cursor,
            threads_cursor=threads_cursor,
        )

        if "errors" in payload and payload["errors"]:
            raise RuntimeError(f"GitHub GraphQL errors:\n{json.dumps(payload['errors'], indent=2)}")

        pr = payload["data"]["repository"]["pullRequest"]
        if pr_meta is None:
            pr_meta = {
                "number": pr["number"],
                "url": pr["url"],
                "title": pr["title"],
                "state": pr["state"],
                "owner": owner,
                "repo": repo,
            }

        c = pr["comments"]
        r = pr["reviews"]
        t = pr["reviewThreads"]

        conversation_comments.extend(c.get("nodes") or [])
        reviews.extend(r.get("nodes") or [])
        review_threads.extend(t.get("nodes") or [])

        comments_cursor = c["pageInfo"]["endCursor"] if c["pageInfo"]["hasNextPage"] else None
        reviews_cursor = r["pageInfo"]["endCursor"] if r["pageInfo"]["hasNextPage"] else None
        threads_cursor = t["pageInfo"]["endCursor"] if t["pageInfo"]["hasNextPage"] else None

        if not (comments_cursor or reviews_cursor or threads_cursor):
            break

    assert pr_meta is not None
    return {
        "pull_request": pr_meta,
        "conversation_comments": conversation_comments,
        "reviews": reviews,
        "review_threads": review_threads,
    }


def main() -> None:
    pr_ref: Optional[str] = None

    if len(sys.argv) > 2:
        print("Usage: python3 scripts/fetch_pr_comments.py [pr_number|#pr_number|pr_url]", file=sys.stderr)
        sys.exit(2)

    if len(sys.argv) == 2:
        pr_ref = _parse_pr_ref(sys.argv[1])

    try:
        _ensure_gh_authenticated()
        owner, repo, number = _get_pr_owner_repo_number(pr_ref)
        result = fetch_all(owner, repo, number)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
