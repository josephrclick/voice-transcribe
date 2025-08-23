# AI Assistant Instructions

This document provides unified instructions for Claude Code, Gemini CLI, and OpenAI Codex CLI.

## Git Workflow Automation

This project uses automated Git workflows. When you see these trigger phrases, follow the automated workflow:

- **"git-start [description]"** - Start new feature branch
- **"git-review"** - Finalize work and create PR
- **"save" or "checkpoint"** - Quick WIP commit and push
- **"status"** - Show PR and CI status

**IMPORTANT**: See Git Workflow section below for complete workflow rules, safety measures, and recovery commands.

## Developer Guidelines

### Code Standards

#### Python Style

- **PEP 8** with 4-space indentation
- **Type hints** where they improve clarity
- **Naming**: `snake_case` for functions/variables, `PascalCase` for classes, `UPPER_SNAKE` for constants
- **Imports**: Standard library first, third-party, then local imports

#### GTK3 Specific

- **Thread Safety**: All UI updates from worker threads must use `GLib.idle_add()`
- **Event Loop**: Keep audio/transcription in background threads; never block main GTK loop
- **CSS**: Match existing color palette and classes in `apply_css()`

#### Error Handling

- **Graceful Degradation**: Network/API failures must not break core functionality
- **Security**: Never expose API keys in logs or error messages
- **Fallbacks**: Enhancement failures should leave original transcript available

## Git Workflow Automation Details

### Command Triggers

#### Starting Work

**"git-start [description]"**

1. `git checkout dev && git pull origin dev`
2. `git checkout -b feat/[description-kebab-case]`
3. `git push -u origin feat/[description-kebab-case]`

**IMPORTANT:** git-start ONLY creates the branch and begins work. Do NOT create pull requests during git-start. Pull requests should only be created when user explicitly triggers "git-review".

#### Quick Saves

**"save" or "checkpoint"**

- `git add . && git commit -m "wip: [current state description]" && git push`

#### Finishing Work

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

### Conventional Commit Types

- **feat:** New feature
- **fix:** Bug fix
- **wip:** Work in progress (checkpoints)
- **docs:** Documentation only
- **style:** Formatting, no logic change
- **refactor:** Code restructuring
- **test:** Adding tests
- **chore:** Maintenance

### Safety Rules

1. **NEVER** commit directly to `main` or `dev`
2. **ALWAYS** pull before creating new branch
3. **PUSH** after every 2-3 commits for rollback points
4. **WIP COMMITS** when uncertain about changes

### Recovery Commands

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

## Code Analysis Tools (MCP Tree-Sitter)

**IMPORTANT**: Use these tools instead of grep/find for all code searching and analysis:

### 1. Search Code (`mcp__tree-sitter__search_code`)

Use for finding functions, classes, variables by name with fuzzy matching:

```python
# Find all transcription-related functions
search_code(query="transcribe", types=["function"])

# Fuzzy search for similar names
search_code(query="enhance", fuzzyThreshold=20)
```

### 2. Find Usage (`mcp__tree-sitter__find_usage`)

Track where any identifier is used throughout the codebase:

```python
# Find all calls to a function
find_usage(identifier="process_audio")

# Track variable usage
find_usage(identifier="config", exactMatch=true)
```

### 3. Analyze Code (`mcp__tree-sitter__analyze_code`)

Run quality checks before commits and after major changes:

```python
# Full project analysis
analyze_code(
projectId="voice-transcribe-dev",
analysisTypes=["quality", "deadcode"],
scope="project"
)

# Check specific file
analyze_code(
projectId="voice-transcribe-dev",
analysisTypes=["quality"],
scope="file",
target="enhance.py"
)
```

**When to use these tools:**

- **Before refactoring**: Use `find_usage` to understand impact
- **During development**: Use `search_code` instead of grep to navigate
- **After changes**: Run `analyze_code` to catch issues early
- **For debugging**: Use `find_usage` to trace execution paths

## Testing Strategy

### Manual Testing (Primary)

Since this is a desktop audio app, manual smoke testing is essential:

1. **Basic Flow**: Launch → record 3s → verify transcript and word count
2. **Prompt Mode**: Toggle via checkbox or Ctrl+Shift+Q → verify enhancement or fallback
3. **Copy/Paste**: Test both copy buttons → verify clipboard and auto-paste (X11/Wayland)
4. **Dashboard Access**: Test Ctrl+D shortcut → verify model specifications display correctly
5. **Model Selection**: Test all tiers (Economy/Standard/Flagship) → verify fallback chains work
6. **Performance Metrics**: Verify dashboard shows accurate context windows and output limits
7. **GPT-5 Features**: Test reasoning effort and verbosity parameters → verify no API errors
8. **Tier Indicators**: Verify visual tier badges display correctly in UI
9. **Edge Cases**: Network failures, API timeouts, invalid audio input

### Unit Tests (Supplementary)

```bash
python -m pytest tests/test_deepgram_service.py
```

Focus on testable components like API integration, audio processing, and configuration handling.

## Essential Dev Commands

### Quick Start

```bash
# Run with auto-venv activation
./voice-transcribe

# Or manually
source venv/bin/activate && python main.py

# Toggle mode for keyboard shortcuts
./voice-transcribe toggle

# Access performance dashboard
# Ctrl+D # Opens model specifications and usage statistics
```

### Configuration

- **API Keys**: Add to `.env` (never commit)
```
DEEPGRAM_API_KEY=your_key_here
OPENAI_API_KEY=sk-your_key_here  # Optional for Prompt Mode + Dashboard
```
- **Preferences**: Auto-saved to `config.json` (don't edit manually)

## Security Guidelines

### API Key Management

- **Environment Variables**: Store in `.env` (git-ignored)
- **No Hardcoding**: Never commit secrets or put them in config files
- **Error Handling**: API failures should not leak credentials in logs

### Configuration

- **User Preferences**: `config.json` for UI settings only (auto-generated)
- **Validation**: Sanitize all user inputs, especially file paths and commands

## Commit Guidelines

### Branch Strategy

- **Target Branch**: `dev` for all PRs
- **Feature Branches**: Use conventional naming (`feat/description`, `fix/bug-name`)
- **Scope**: Keep changes focused and reversible

### Pull Requests

Include in PR description:

- **Purpose**: What problem does this solve?
- **Changes**: Summary of modifications
- **Testing**: Steps to verify the changes
- **Screenshots**: For UI changes
- **Config Impact**: Any new environment variables or setup steps

For complete setup, architecture details, and user features, see `README.md`.
