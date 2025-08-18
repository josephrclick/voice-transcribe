# Claude Code Git Rules - Solo Developer Workflow

## AUTOMATED BEHAVIORS

### Starting Work

When I say "git-start [description]":

1. Ensure we're on dev: `git checkout dev && git pull origin dev`
2. Create feature branch: `git checkout -b feat/[description-kebab-case]`
3. Push branch to set upstream: `git push -u origin feat/[description-kebab-case]`

### During Development

**Auto-commit every significant change:**

- After creating a new file → `git add . && git commit -m "feat: add [filename]"`
- After fixing a bug → `git add . && git commit -m "fix: [what was fixed]"`
- After refactoring → `git add . && git commit -m "refactor: [what was changed]"`

**Quick saves (my most used):**
When I say "save" or "checkpoint":

- `git add . && git commit -m "wip: [description of current state]" && git push`

### Finishing Work

When I say "git-review":

1. Final commit: `git add . && git commit -m "feat: complete [branch-name-humanized]"`
2. Push: `git push`
3. Create PR: `gh pr create --base dev --fill --web`
   (--fill uses commit messages for PR description, --web opens browser)

## COMMIT MESSAGE RULES

Always use conventional commits (automated):

- feat: New feature
- fix: Bug fix
- wip: Work in progress (for checkpoints)
- docs: Documentation only
- style: Formatting, no code change
- refactor: Code restructuring
- test: Adding tests
- chore: Maintenance

## SAFETY RULES

1. NEVER commit directly to 'main' or 'dev'
2. Always pull before creating a new branch
3. Push after every 2-3 commits (more rollback points)
4. If uncertain about changes, create a "wip:" commit

## SHORTCUTS

- "save" = quick commit and push with WIP message
- "git-review" = finalize and create PR
- "git-start fix for [bug]" = create fix/[bug] branch
- "daily" = commit as "wip: daily checkpoint - [date]"

## CHECK STATUS

When I say "status":

1. Show PR status: `gh pr status`
2. Show recent action runs: `gh run list --limit 3`
3. If any failed, show: `gh run view`

When I say "sprint status":

1. Use GitHub MCP to read all sprint-related issues
2. Use CLI to show PR statuses
3. Combine into comprehensive report

When I say "why failed":

- `gh run view --log-failed`

## AUTOMATED CHECKS

After each push, automatically:

1. Wait 10 seconds
2. Check status: `gh run list --limit 1`
3. If failed, show: `gh run view --log-failed`
4. Suggest fix based on error

## Build reports

When I say "generate build report":

1. Get PR details: `gh pr view --json title,body,commits`
2. Get CI results: `gh run view`
3. Create report at: docs/build-reports/$(date +%Y%m%d)-[feature].md
4. Include:
   - Features implemented
   - Tests added
   - Performance metrics
   - Issues encountered
   - Next steps

## RECOVERY COMMANDS

When I say "undo last commit":

- `git reset --soft HEAD~1`

When I say "abort merge":

- `git merge --abort`

When I say "stash and switch":

1. `git stash`
2. `git checkout dev`
3. Note: "Changes stashed. Run 'git stash pop' to restore"

When I say "fresh start":

1. `git stash`
2. `git checkout dev`
3. `git pull origin dev`
4. `git checkout -b feat/fresh-start`
