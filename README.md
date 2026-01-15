Install Codex prompts
=====================

This repository includes two Codex prompt files that you can install locally
on a new machine with a single command.

Single-command installer
------------------------

Run this single command (copy-paste into a shell). It creates `~/.codex/prompts`,
downloads the two prompt files from `proustibat/my-dot-codex` (branch `main`),
and prints a success message.
```shell
mkdir -p "$HOME/.codex/prompts"

failed=0
for f in install-custom-skill-from-github-repo.md update-installed-skills.md; do
  url="https://raw.githubusercontent.com/proustibat/my-dot-codex/main/.codex/prompts/$f"
  echo "Downloading $f..."
  if ! curl -fsSL -o "$HOME/.codex/prompts/$f" "$url"; then
    echo "  → Failed to download $f (HTTP error or network problem)"
    failed=1
  fi
done

if [ "$failed" -eq 1 ]; then
  echo "One or more downloads failed. Run the following to debug the URLs:"
  echo "  curl -I https://raw.githubusercontent.com/proustibat/my-dot-codex/main/.codex/prompts/install-custom-skill-from-github-repo.md"
  echo "  curl -I https://raw.githubusercontent.com/proustibat/my-dot-codex/main/.codex/prompts/update-installed-skills.md"
else
  echo "Prompts installed to $HOME/.codex/prompts"
fi
```

How to run the prompts
----------------------

Below are minimal examples showing how to invoke each prompt with a `codex` runner
that accepts environment variables.

1) In Codex CLI, run 
```shell
/prompts install-custom-skill-from-github-repo REMOTE_REPO="<owner>/<repo>"
```
(Interactive) The prompt will list available skills under `.codex/skills/` in the remote repo,
ask you to choose one (by number or folder name), then install it into your current repository
under `.codex/skills/<skill_folder>/`.

2) Check or apply updates for installed skills, in Codex CLI run:
```shell
/prompts update-installed-skills MODE="CHECK_ONLY"
```
or
```shell
/prompts update-installed-skills MODE="APPLY"
```

`CHECK_ONLY` prints a status report for each installed skill. `APPLY` will create backups,
replace outdated skills with the remote version, and update provenance files.