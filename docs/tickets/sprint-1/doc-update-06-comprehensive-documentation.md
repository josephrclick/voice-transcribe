# DOC-UPDATE-06: Comprehensive Documentation Update for Latest Features

## Ticket ID: DOC-UPDATE-06

## Phase: Sprint 1 - Post-Implementation Documentation

## Priority: High

## Dependencies: MODEL-UPGRADE-05 (Update Model Information), MODEL-UPGRADE-04 (Remove Cost Warnings)

## Summary

Update all project documentation (README.md, CLAUDE.md, AGENTS.md) to accurately reflect the current state after MODEL-UPGRADE-05 implementation, including flagship tier support, accurate model specifications, performance dashboard, and new keyboard shortcuts.

## Current State

- README.md model table contains outdated/incorrect specifications
- Missing documentation for Ctrl+D performance dashboard shortcut
- No mention of flagship tier models or enhanced model selection
- CLAUDE.md missing new keyboard shortcuts and features
- AGENTS.md lacks testing procedures for new dashboard and model features
- Documentation gaps between actual capabilities and user-facing information

## Target State

- Accurate model specifications table with correct context windows and output limits
- Complete keyboard shortcut documentation including Ctrl+D dashboard access
- Comprehensive performance dashboard documentation
- Updated development and testing procedures reflecting latest architecture
- Consistent terminology and feature descriptions across all documentation files

## Research Requirements

### 1. Current Model Specifications Audit

Based on code analysis in `model_config.py` and recent commits:

**Accurate Model Specifications:**

- GPT-4o Mini: 128K context, 4,096 output tokens, JSON support, Standard tier
- GPT-4.1 Nano: 1M context, 2,048 output tokens, JSON + Verbosity, Economy tier
- GPT-4.1 Mini: 1M context, 4,096 output tokens, JSON + Verbosity, Economy tier
- GPT-4.1: 1M context, 8,192 output tokens, JSON + Verbosity, Standard tier
- GPT-5 Nano: 400K context, 128,000 output tokens, All features, Economy tier
- GPT-5 Mini: 400K context, 128,000 output tokens, All features, Standard tier
- GPT-5: 400K context, 128,000 output tokens, All features, Flagship tier

**New Features Since Last Documentation Update:**

- Performance dashboard accessible via Ctrl+D
- Flagship tier model classification
- Enhanced model comparison interface
- Usage statistics tracking
- Automatic fallback chains
- Context window explanations (128K = ~96K words, 1M = ~750K words)

## Acceptance Criteria

- [ ] README.md model table reflects actual specifications from model_config.py
- [ ] All keyboard shortcuts documented (Ctrl+Q, Ctrl+Shift+Q, Ctrl+D)
- [ ] Performance dashboard section added to README.md
- [ ] CLAUDE.md updated with new shortcuts and development features
- [ ] AGENTS.md includes testing procedures for dashboard and model selection
- [ ] Consistent tone and style maintained across all documentation
- [ ] No technical inaccuracies in user-facing documentation
- [ ] Documentation supports both user and developer workflows

## Technical Requirements

### Files to Update

1. **README.md**
   - Add CI badge after title line (line 2) to showcase CI/CD practices
   - Replace model specifications table (lines 140-153)
   - Add Ctrl+D keyboard shortcut (line 214)
   - Add Performance Dashboard section (after line 162)
   - Update stack description to mention flagship tier models (lines 36-37)

2. **CLAUDE.md**
   - Add Ctrl+D to keyboard shortcuts section (after line 83)
   - Update API key comments to reference dashboard (line 102)

3. **AGENTS.md**
   - Add dashboard testing procedures (after line 33)
   - Include model selection testing for all tiers
   - Add GPT-5 specific testing notes

### Detailed Documentation Updates

#### README.md Changes

**Add CI Badge (After line 1, before line 3):**

```markdown
# Voice Transcribe v3.2 🎤

[![CI Pipeline](https://github.com/josephrclick/voice-transcribe/actions/workflows/ci.yml/badge.svg?branch=dev)](https://github.com/josephrclick/voice-transcribe/actions/workflows/ci.yml)

A delightfully simple voice-to-text tool for Linux that just works™. Click button, speak thoughts, get text. Now with ✨ Prompt Mode ✨ for AI-enhanced transcripts!
```

**New Model Specifications Table (Replace lines 140-153):**

```markdown
## Available Models

| Model        | Context Window | Max Output | Features        | Tier     | Best For         |
| ------------ | -------------- | ---------- | --------------- | -------- | ---------------- |
| GPT-4o Mini  | 128K           | 4,096      | JSON            | Standard | Quick edits      |
| GPT-4.1 Nano | 1M             | 2,048      | JSON, Verbosity | Economy  | High volume      |
| GPT-4.1 Mini | 1M             | 4,096      | JSON, Verbosity | Economy  | Longer texts     |
| GPT-4.1      | 1M             | 8,192      | JSON, Verbosity | Standard | Professional     |
| GPT-5 Nano   | 400K           | 128,000    | All features    | Economy  | Fast processing  |
| GPT-5 Mini   | 400K           | 128,000    | All features    | Standard | Creative writing |
| GPT-5        | 400K           | 128,000    | All features    | Flagship | Complex tasks    |

- **Flagship tier models** offer advanced reasoning capabilities
- **Context windows**: 128K = ~96K words, 400K = ~300K words, 1M = ~750K words
- **All models** include automatic fallback chains for reliability
- Model selection persists between sessions with intelligent fallback handling
```

**New Performance Dashboard Section (Add after line 162):**

```markdown
### 📊 Performance Dashboard

Access comprehensive model information and usage statistics with **Ctrl+D**:

- **Model Specifications**: Detailed context windows, output limits, and feature support matrix
- **Performance Metrics**: Real-time speed comparisons and latency estimates
- **Usage Statistics**: Session costs and model usage tracking across all tiers
- **Tier Classifications**: Economy, Standard, and Flagship model comparisons
- **Context Explanations**: Human-readable descriptions of model capabilities

The dashboard helps you choose the optimal model for specific use cases and understand the trade-offs between speed, capability, and cost.
```

**Updated Keyboard Shortcuts (Update line 214):**

```markdown
### ⌨️ Keyboard Shortcuts

- **Ctrl+Q**: Toggle recording (works globally with desktop setup)
- **Ctrl+Shift+Q**: Toggle Prompt Mode instantly
- **Ctrl+D**: Open Performance Dashboard with comprehensive model information
```

#### CLAUDE.md Changes

**Add Ctrl+D Shortcut (After line 83):**

```markdown
# Toggle mode for keyboard shortcuts

./voice-transcribe toggle

# Access performance dashboard

Ctrl+D # Opens model specifications and usage statistics
```

#### AGENTS.md Changes

**Enhanced Manual Testing Procedures (Add after line 33):**

```markdown
4. **Dashboard Access**: Test Ctrl+D shortcut → verify model specifications display correctly
5. **Model Selection**: Test all tiers (Economy/Standard/Flagship) → verify fallback chains work
6. **Performance Metrics**: Verify dashboard shows accurate context windows and output limits
7. **GPT-5 Features**: Test reasoning effort and verbosity parameters → verify no API errors
8. **Tier Indicators**: Verify visual tier badges (🟢🔵🟣🟡) display correctly in UI
```

## Implementation Order

1. **README.md** (Priority 1):
   - Add CI badge after title to showcase CI/CD best practices
   - Update model specifications table with accurate data
   - Add keyboard shortcuts documentation
   - Add performance dashboard section
   - Update feature descriptions

2. **CLAUDE.md** (Priority 2):
   - Add Ctrl+D keyboard shortcut
   - Update development workflow references

3. **AGENTS.md** (Priority 3):
   - Add comprehensive testing procedures
   - Include tier-specific testing notes

## Testing Checklist

- [ ] CI badge displays correctly and links to GitHub Actions workflow
- [ ] CI badge shows current dev branch status (passing/failing)
- [ ] All model specifications match actual model_config.py values
- [ ] Context window conversions accurate (tokens to words)
- [ ] Keyboard shortcuts documented work as described
- [ ] Performance dashboard accessible and functional via Ctrl+D
- [ ] Documentation tone consistent across all files
- [ ] No broken internal links or references
- [ ] Screenshots/examples align with current UI
- [ ] Testing procedures cover all new features

## Documentation Style Guidelines

- **Tone**: Friendly but professional, matching existing README.md style
- **Technical Accuracy**: All specifications must match actual code implementation
- **User Focus**: Prioritize user-facing features over implementation details
- **Consistency**: Use established terminology (Prompt Mode, Performance Dashboard, etc.)
- **Accessibility**: Include context explanations for technical terms

## Validation Requirements

### Cross-Reference Validation

- [ ] Model specifications in README.md match model_config.py exactly
- [ ] Keyboard shortcuts in documentation work in actual application
- [ ] Feature descriptions align with actual UI elements
- [ ] Version numbers and capabilities are current

### User Experience Validation

- [ ] New users can follow documentation to understand all features
- [ ] Developers can use CLAUDE.md and AGENTS.md for effective contribution
- [ ] No outdated information that could confuse users

## Success Metrics

- Zero discrepancies between documentation and actual application behavior
- Complete feature coverage for MODEL-UPGRADE-05 implementation
- Consistent user experience from documentation to application usage
- Developer onboarding efficiency improved with accurate AGENTS.md

## Dependencies

- MODEL-UPGRADE-05 must be fully implemented and tested
- Performance dashboard must be stable and accessible via Ctrl+D
- All model specifications finalized in model_config.py
- No breaking changes planned for documented features

## Notes

- CI badge uses dev branch status to reflect active development practices
- CI badge demonstrates commitment to quality assurance and modern development workflows
- Context window explanations based on ~0.75 words per token ratio
- Performance metrics should reflect actual user experience testing
- Tier colors and badges match UI implementation in main.py
- Keep flagship tier explanation clear but not overly technical
- Coordinate with any future model additions to maintain accuracy

## Rollback Plan

- Git revert to previous documentation versions if inaccuracies discovered
- Documentation changes are non-breaking and don't affect application functionality
- Can update incrementally if testing reveals issues

## Future Considerations

- Monitor for OpenAI API changes that might affect documented specifications
- Consider automated validation of documentation against actual code
- Plan documentation updates for upcoming model additions (GPT-5 improvements)
- Evaluate need for video tutorials or interactive guides
