#!/usr/bin/env python3
"""
Fetch PR metadata + list of modified files + diff for a given PR (or current branch PR).

Usage:
  python3 scripts/fetch_pr_diff.py
  python3 scripts/fetch_pr_diff.py 3698
  python3 scripts/fetch_pr_diff.py "#3698"
  python3 scripts/fetch_pr_diff.py https://github.com/org/repo/pull/3698

Requires:
  - `gh` installed
  - `gh auth login` already set up
  - run inside a git repo that can resolve the PR context

Output JSON:
  {
    "pr": {...},         # gh pr view --json fields
    "diff": "..."        # gh pr diff output
  }
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from typing import Any, Optional


def _run(cmd: list[str]) -> str:
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{p.stderr.strip()}")
    return p.stdout


def _run_json(cmd: list[str]) -> dict[str, Any]:
    out = _run(cmd)
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
    """
    Accepts:
      - "3698"
      - "#3698"
      - "https://github.com/org/repo/pull/3698"
    Returns a PR ref suitable to pass to `gh pr view <ref>` and `gh pr diff <ref>`:
      - for number inputs: "3698"
      - for URL inputs: the same URL
    """
    s = arg.strip()

    # "#123" -> "123"
    if re.fullmatch(r"#\d+", s):
        return s.lstrip("#")

    # "123" -> "123"
    if re.fullmatch(r"\d+", s):
        return s

    # URL containing "/pull/<num>"
    m = re.search(r"/pull/(\d+)", s)
    if m:
        # gh accepts PR URL directly, keep it
        return s

    raise ValueError(f"Invalid PR reference: {arg!r}. Expected a number (e.g. 3698), #3698, or a PR URL.")


def _get_pr_view_json(pr_ref: Optional[str]) -> dict[str, Any]:
    fields = "number,title,url,headRefName,baseRefName,state,author,createdAt,updatedAt,additions,deletions,changedFiles,files"
    cmd = ["gh", "pr", "view"]
    if pr_ref:
        cmd.append(pr_ref)
    cmd += ["--json", fields]
    return _run_json(cmd)


def _get_pr_diff(pr_ref: Optional[str]) -> str:
    cmd = ["gh", "pr", "diff"]
    if pr_ref:
        cmd.append(pr_ref)
    return _run(cmd)


def main() -> None:
    pr_ref: Optional[str] = None

    if len(sys.argv) > 2:
        print("Usage: python3 scripts/fetch_pr_diff.py [pr_number|#pr_number|pr_url]", file=sys.stderr)
        sys.exit(2)

    if len(sys.argv) == 2:
        pr_ref = _parse_pr_ref(sys.argv[1])

    try:
        _ensure_gh_authenticated()
        pr_json = _get_pr_view_json(pr_ref)
        diff = _get_pr_diff(pr_ref)

        result = {
            "pr": pr_json,
            "diff": diff,
        }

        print(json.dumps(result, indent=2))
    except Exception as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
