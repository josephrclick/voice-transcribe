# CLAUDE.md

## Git Workflow Automation

This project uses automated Git workflows. When you see these trigger phrases, follow the automated workflow in `.claude/rules.md`:

- **"git-start [description]"** - Start new feature branch
- **"git-review"** - Finalize work and create PR
- **"save" or "checkpoint"** - Quick WIP commit and push
- **"status"** - Show PR and CI status

**IMPORTANT**: Always read `.claude/rules.md` first for complete workflow rules, safety measures, and recovery commands.

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

## Essential Dev Commands

### Quick Start

```bash
# Run with auto-venv activation
./voice-transcribe

# Or manually
source venv/bin/activate && python main.py

# Toggle mode for keyboard shortcuts
./voice-transcribe toggle
```

### Testing

```bash
# Unit tests
python -m pytest tests/test_deepgram_service.py

# Manual smoke test checklist:
# 1. Record 3s audio → verify transcript + word count
# 2. Toggle Prompt Mode → verify enhancement or fallback
# 3. Test both copy buttons + auto-paste
```

### Configuration

- **API Keys**: Add to `.env` (never commit)
  ```
  DEEPGRAM_API_KEY=your_key_here
  OPENAI_API_KEY=sk-your_key_here  # Optional for Prompt Mode
  ```
- **Preferences**: Auto-saved to `config.json` (don't edit manually)

## Threading Safety Notes

- All UI updates MUST use `GLib.idle_add()` when called from worker threads
- Audio/transcription runs in background threads to avoid blocking GTK main loop
- Enhancement failures should not affect original transcript availability

For complete setup, architecture details, and user features, see `README.md`.
