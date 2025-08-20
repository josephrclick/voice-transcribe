# Git Workflow Automation - Solo Developer

## Command Triggers

### Starting Work

**"git-start [description]"**

1. `git checkout dev && git pull origin dev`
2. `git checkout -b feat/[description-kebab-case]`
3. `git push -u origin feat/[description-kebab-case]`

**IMPORTANT:** git-start ONLY creates the branch and begins work. Do NOT create pull requests during git-start. Pull requests should only be created when user explicitly triggers "git-review".

### Quick Saves

**"save" or "checkpoint"**

- `git add . && git commit -m "wip: [current state description]" && git push`

### Finishing Work

**"git-review"** or **"git-review #[issue-number]"**

1. `git add . && git commit -m "feat: complete [feature-name]"`
2. `git push`
3. `gh pr create --base dev --fill --web`
4. If issue number provided, add "Closes #[issue-number]" to PR description

**IMPORTANT:**

- git-review is the ONLY command that should create pull requests
- This command is only executed when user explicitly says "git-review" - never automatically after git-start or other commands
- If user provides issue number (e.g., "git-review #35"), include "Closes #[issue-number]" at the end of the PR description
- If unsure of the proper issue number to close, skip the "Closes" phrase entirely

### Status Checks

**"status"**

1. `gh pr status`
2. `gh run list --limit 3`
3. If failed: `gh run view`

**"why failed"**

- `gh run view --log-failed`

## Auto-Commit Patterns

Commit after every significant change:

- New file → `git add . && git commit -m "feat: add [filename]"`
- Bug fix → `git add . && git commit -m "fix: [what was fixed]"`
- Refactor → `git add . && git commit -m "refactor: [what changed]"`

## Conventional Commit Types

- **feat:** New feature
- **fix:** Bug fix
- **wip:** Work in progress (checkpoints)
- **docs:** Documentation only
- **style:** Formatting, no logic change
- **refactor:** Code restructuring
- **test:** Adding tests
- **chore:** Maintenance

## Safety Rules

1. **NEVER** commit directly to `main` or `dev`
2. **ALWAYS** pull before creating new branch
3. **PUSH** after every 2-3 commits for rollback points
4. **WIP COMMITS** when uncertain about changes

## Recovery Commands

**"undo last commit"**

- `git reset --soft HEAD~1`

**"abort merge"**

- `git merge --abort`

**"stash and switch"**

1. `git stash`
2. `git checkout dev`
3. Note: "Run 'git stash pop' to restore changes"

**"fresh start"**

1. `git stash`
2. `git checkout dev && git pull origin dev`
3. `git checkout -b feat/fresh-start`

## Post-Push Automation

After each push, automatically:

1. Wait 10 seconds
2. `gh run list --limit 1`
3. If failed: `gh run view --log-failed` + suggest fix
