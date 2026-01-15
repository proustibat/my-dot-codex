#!/usr/bin/env python3
"""
Fetch a GitHub Issue (title/body/metadata + comments) by issue number using gh CLI.

Usage:
  python3 scripts/fetch_issue.py 123
  python3 scripts/fetch_issue.py "#123"

Requirements:
  - gh installed
  - `gh auth login` done
  - run inside a git repo that has the issue (or `gh` can resolve the repo context)

Output:
  Prints a JSON object to stdout with:
    - issue: {number, title, url, state, body, labels, assignees, author, createdAt, updatedAt}
    - comments: [{id, author, createdAt, updatedAt, body}, ...]
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from typing import Any


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
        raise RuntimeError(f"Failed to parse JSON output: {e}\nRaw:\n{out}") from e


def _ensure_gh_authenticated() -> None:
    try:
        _run(["gh", "auth", "status"])
    except Exception:
        raise RuntimeError("GitHub CLI is not authenticated. Run: gh auth login") from None


def _parse_issue_number(arg: str) -> int:
    s = arg.strip()
    s = s.lstrip("#")
    if not re.fullmatch(r"\d+", s):
        raise ValueError(f"Invalid issue number: {arg!r}. Expected something like 123 or #123.")
    n = int(s)
    if n < 1:
        raise ValueError("Issue number must be >= 1.")
    return n


def fetch_issue(issue_number: int) -> dict[str, Any]:
    """
    Use `gh issue view` JSON fields. This works well for most repos and includes comments.
    """
    fields = ",".join(
        [
            "number",
            "title",
            "url",
            "state",
            "body",
            "author",
            "createdAt",
            "updatedAt",
            "assignees",
            "labels",
            "comments",
        ]
    )

    payload = _run_json(["gh", "issue", "view", str(issue_number), "--json", fields])

    # Normalize the shape slightly (gh returns nested structures)
    issue = {
        "number": payload.get("number"),
        "title": payload.get("title"),
        "url": payload.get("url"),
        "state": payload.get("state"),
        "body": payload.get("body") or "",
        "author": (payload.get("author") or {}).get("login"),
        "createdAt": payload.get("createdAt"),
        "updatedAt": payload.get("updatedAt"),
        "assignees": [a.get("login") for a in (payload.get("assignees") or []) if isinstance(a, dict)],
        "labels": [l.get("name") for l in (payload.get("labels") or []) if isinstance(l, dict)],
    }

    comments_out: list[dict[str, Any]] = []
    for c in payload.get("comments") or []:
        if not isinstance(c, dict):
            continue
        comments_out.append(
            {
                "id": c.get("id"),
                "author": (c.get("author") or {}).get("login"),
                "createdAt": c.get("createdAt"),
                "updatedAt": c.get("updatedAt"),
                "body": c.get("body") or "",
            }
        )

    return {"issue": issue, "comments": comments_out}


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python3 scripts/fetch_issue.py <issue_number_or_#issue_number>", file=sys.stderr)
        sys.exit(2)

    try:
        issue_number = _parse_issue_number(sys.argv[1])
        _ensure_gh_authenticated()
        result = fetch_issue(issue_number)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
