# Unified AI Assistant Configuration

This directory contains the unified configuration for Claude Code, Gemini CLI, and OpenAI Codex CLI.

## Structure

```
.ai/
├── instructions.md    # Master instructions file (symlinked to all tools)
├── commands/          # Reusable command templates
├── rules/            # Workflow-specific rules
├── plans/            # Technical execution plans
├── docs/             # Project documentation
├── memories/         # Persistent context and memories
└── README.md         # This file
```

## Tool Configuration

### Claude Code

- Primary files: `CLAUDE.md` (symlink), `AGENTS.md` (symlink)
- Config directory: `.claude/`
- Git workflows: `.claude/rules.md`

### Gemini CLI

- Primary files: `GEMINI.md` (symlink), `AGENTS.md` (symlink)
- Config directory: `.gemini/`
- Settings: `.gemini/settings.json` (configured to use AGENTS.md)

### OpenAI Codex CLI

- Primary file: `AGENTS.md` (symlink)
- Config directory: `.codex/`
- Settings: `.codex/config.toml`

## Symlink Structure

All tools reference the same master instructions file:

```
CLAUDE.md -> .ai/instructions.md
GEMINI.md -> .ai/instructions.md
AGENTS.md -> .ai/instructions.md
```

## MCP Servers

Both Gemini CLI and Codex CLI are configured with:

- **Sequential Thinking**: For structured problem-solving
- **Context7**: For documentation lookups

## Updating Instructions

To update instructions for all tools:

1. Edit `.ai/instructions.md`
2. All symlinked files will automatically reflect changes
3. No need to update multiple files

## Benefits

1. **Single source of truth**: One file to maintain
2. **Tool flexibility**: Switch between tools seamlessly
3. **Consistent behavior**: All tools follow same rules
4. **Easy updates**: Change once, apply everywhere
5. **No lock-in**: Each tool still works independently

## GitHub Workflows

The `.github/workflows/` directory contains tool-agnostic workflows that work with all three assistants:

- CI/CD pipelines
- PR reviews
- Issue triage
- Code quality checks

## Usage

Simply launch your preferred tool:

```bash
# Claude Code
claude

# Gemini CLI
gemini

# Codex CLI
codex
```

Each tool will automatically use the unified configuration through the symlinks.
