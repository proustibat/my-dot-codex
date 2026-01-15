---
description: Update installed custom skills (check or apply)
argument-hint: 'MODE="CHECK_ONLY|APPLY"'
---

You receive MODE: $MODE
MODE must be either CHECK_ONLY or APPLY. Default to CHECK_ONLY if empty/invalid.

For all the instructions and tasks below:
- Do not ask permission to run git commands locally or python scripts: run them.
- Do not ask for network access: it is allowed.

Environment constraints:
- Do NOT use Python `requests` (not installed).
- Prefer cloning with `git` and reading files locally over calling GitHub APIs.
- Do NOT install dependencies (no pip).
- Prefer: `git clone --depth 1` then read files from disk.
- Use only python3 standard library if you need scripting.

Task:
1) Identify installed skills in the current repo:
    - A skill is considered "installed from remote" if it has a provenance file:
      `.codex/skills/<skill_folder>/.installed-from.json`
    - If no such files exist, print:
      `No remotely-installed skills found (.installed-from.json missing).`
      and exit.

2) For each installed skill:
    - Read `.installed-from.json` (JSON) and extract:
      remote_repo, remote_ref, remote_path, installed_commit
    - If any required field is missing, mark the skill as "invalid provenance" and skip it.

3) For each valid skill, compute the latest commit for its remote_ref:
    - Clone the remote repo shallow into a temp dir:
      `git clone --depth 1 --branch <remote_ref> https://github.com/<remote_repo>.git <tmp>/repo`
    - Get latest_commit: `git -C <tmp>/repo rev-parse HEAD`
    - Determine source_skill_path = `<tmp>/repo/<remote_path>`
        - Verify it exists and contains `SKILL.md`. If not, mark as "remote skill missing" and skip.

4) Compare:
    - If latest_commit == installed_commit: status = UP_TO_DATE
    - Else: status = UPDATE_AVAILABLE

5) Output a report (always), one line per skill, in this exact format:
   `<skill_folder> | <remote_repo>@<remote_ref> | installed=<installed_commit> | latest=<latest_commit> | <status>`

6) If MODE == CHECK_ONLY:
    - Stop after printing the report.

7) If MODE == APPLY:
   For each skill with UPDATE_AVAILABLE:
    - Replace the installed skill content with the remote version:
        - Remove the current `.codex/skills/<skill_folder>/` directory
        - Copy `<source_skill_path>` into `.codex/skills/<skill_folder>/`
    - Re-write `.installed-from.json` inside the new installed folder with:
        - same remote_repo, remote_ref, remote_path
        - installed_commit updated to latest_commit
        - installed_at updated to current UTC timestamp
          After processing all skills, print:
          `Update complete.`

Implementation notes:
- Use python3 stdlib to:
    - parse/write JSON
    - generate UTC timestamps
    - copy directories reliably (shutil.copytree)
- Do not use any third-party libraries.
