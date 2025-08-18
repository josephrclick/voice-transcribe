# CLAUDE.md

## Git Workflow Automation

This project uses automated Git workflows. When you see these trigger phrases, follow the automated workflow in `.claude/rules.md`:

- **"git-start [description]"** - Start new feature branch
- **"git-review"** - Finalize work and create PR
- **"save" or "checkpoint"** - Quick WIP commit and push
- **"status"** - Show PR and CI status

**IMPORTANT**: Always read `.claude/rules.md` first for complete workflow rules, safety measures, and recovery commands.

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
