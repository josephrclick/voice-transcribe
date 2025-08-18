# Developer Guidelines

## Code Standards

### Python Style

- **PEP 8** with 4-space indentation
- **Type hints** where they improve clarity
- **Naming**: `snake_case` for functions/variables, `PascalCase` for classes, `UPPER_SNAKE` for constants
- **Imports**: Standard library first, third-party, then local imports

### GTK3 Specific

- **Thread Safety**: All UI updates from worker threads must use `GLib.idle_add()`
- **Event Loop**: Keep audio/transcription in background threads; never block main GTK loop
- **CSS**: Match existing color palette and classes in `apply_css()`

### Error Handling

- **Graceful Degradation**: Network/API failures must not break core functionality
- **Security**: Never expose API keys in logs or error messages
- **Fallbacks**: Enhancement failures should leave original transcript available

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

### Commit Messages

Use conventional commits:

- `feat:` New features
- `fix:` Bug fixes
- `wip:` Work in progress
- `docs:` Documentation only
- `refactor:` Code restructuring
- `test:` Adding tests
- `chore:` Maintenance

### Pull Requests

Include in PR description:

- **Purpose**: What problem does this solve?
- **Changes**: Summary of modifications
- **Testing**: Steps to verify the changes
- **Screenshots**: For UI changes
- **Config Impact**: Any new environment variables or setup steps
