---
description: Install a custom skill from a given repo
argument-hint: 'REMOTE_REPO="<owner>/<repo>"'
---
You receive REMOTE_REPO in the format <owner>/<repo>: $REMOTE_REPO.

For all the instructions and tasks below:
- Do not ask permission to run git commands locally or python scripts: run them.
- Do not ask for network access: it is allowed.

Environment constraints:
- Do NOT use Python `requests` (not installed).
- If you need HTTP, use ONE of:
   - `python3` + `urllib.request`, or
   - `curl`, or
   - `gh` CLI (preferred when interacting with GitHub).
- Prefer cloning the repo with `git` and reading files locally over calling GitHub APIs.
- Do NOT install dependencies (no pip).
- Prefer: `git clone --depth 1` then read files from disk.
- If you parse YAML in Python, use only the standard library (no PyYAML). If needed, parse with simple rules:
   - Read lines, ignore `---`, capture `name: ...`
   - When inside `metadata:`, capture `short-description: ...`

Task:
1) Look for custom skills in REMOTE_REPO (on Github) under `.codex/skills/`
    - A skill is a directory under `.codex/skills/`.
    - Each skill should have a `SKILL.md` file. If missing, skip it.
2) For each `SKILL.md`, treat the entire file as YAML (no markdown parsing).
   Extract:
   - Title: the YAML field `name`
   - Description: the YAML field `metadata.short-description`
     Fallback rules:
   - If `metadata.short-description` is missing, use the YAML field `description`.
   - If both are missing, use `No description`.
     Do NOT output any raw YAML or the `---` separators.
3) Output the list using exactly:
   `<index>. <skill_folder> - <Description>`
   (one item per line, index starts at 1)
4) If `.codex/skills` does not exist or contains no valid skills, say so clearly and exit the prompt
5) Ask the user which skill they want to use. Allow the user to select one by number or name.
6) Install the choosen skill in the current repo (not in ~/codex/skills!, really locally in the current repo/folder) from the github remote repo
7) After installing, write a provenance file inside the installed skill directory:
      Path: `.codex/skills/<skill_folder>/.installed-from.json`
      JSON fields:
    - remote_repo: "$REMOTE_REPO"
    - remote_ref: "main" (or the ref you used)
    - remote_path: ".codex/skills/<skill_folder>"
    - installed_commit: the commit SHA of the cloned repo (git rev-parse HEAD)
    - installed_at: current UTC timestamp in ISO-8601
      Use only standard tools (python3 stdlib is allowed) to write JSON.
