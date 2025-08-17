# Build Ticket: Model-Agnostic Architecture Implementation

**Ticket ID**: MODEL-UPGRADE-01  
**Phase**: 1 - Immediate Actions  
**Priority**: High  
**Estimated Effort**: 4-6 hours  
**Target Date**: Immediate

## Overview

Implement a model-agnostic architecture for Voice Transcribe's Prompt Mode to prepare for future OpenAI model transitions. This foundational work will prevent breaking changes when GPT-4.1 and GPT-5 models are released.

## Background

Current implementation is hardcoded for GPT-4o-mini. GPT-5 series will introduce breaking parameter changes (`max_tokens` → `max_completion_tokens`) that would cause application failure without this abstraction layer.

## Acceptance Criteria

- [ ] Model configuration system implemented and working with current GPT-4o-mini
- [ ] Error handling catches and retries parameter mismatches
- [ ] UI has disabled model selector dropdown (visual only)
- [ ] Token usage tracking logs consumption to console
- [ ] All existing Prompt Mode functionality remains unchanged
- [ ] No user-visible changes except for disabled dropdown

## Technical Requirements

### 1. Create Model Configuration Module (`model_config.py`)

```python
MODEL_CONFIGS = {
    "gpt-4o-mini": {
        "model_name": "gpt-4o-mini",
        "max_tokens_param": "max_tokens",
        "max_tokens_value": 1000,
        "temperature": 0.3,
        "supports_verbosity": False,
        "supports_reasoning": False,
        "display_name": "GPT-4o Mini",
        "cost_per_1k": 0.15
    }
}

def get_model_config(model_key="gpt-4o-mini"):
    return MODEL_CONFIGS.get(model_key, MODEL_CONFIGS["gpt-4o-mini"])
```

### 2. Update `enhance.py`

- Import model configuration
- Refactor `enhance_prompt()` to use dynamic parameter building
- Add BadRequestError handling with parameter retry logic
- Add token counting using tiktoken library

```python
def enhance_prompt(transcript, style="balanced", model_key="gpt-4o-mini"):
    config = get_model_config(model_key)

    # Build parameters dynamically
    params = {
        "model": config["model_name"],
        "messages": [...],
        config["max_tokens_param"]: config["max_tokens_value"],
        "temperature": config["temperature"],
        "timeout": 15.0
    }

    try:
        response = client.chat.completions.create(**params)
        log_token_usage(response.usage)  # New tracking
        return response.choices[0].message.content.strip(), None
    except openai.BadRequestError as e:
        if "max_tokens" in str(e) and "max_completion_tokens" in str(e):
            # Handle GPT-5 parameter change
            params["max_completion_tokens"] = params.pop("max_tokens", 1000)
            response = client.chat.completions.create(**params)
            log_token_usage(response.usage)
            return response.choices[0].message.content.strip(), None
        raise
```

### 3. Add UI Model Selector (`main.py`)

- Create `create_model_selector()` method
- Add dropdown to settings area (below enhancement style)
- Set sensitivity to False (disabled state)
- Display model name with cost per 1K tokens

```python
def create_model_selector(self):
    model_frame = Gtk.Frame()
    model_frame.set_label("AI Model")

    self.model_combo = Gtk.ComboBoxText()
    self.model_combo.append("gpt-4o-mini", "GPT-4o Mini ($0.15/1K)")
    self.model_combo.set_active_id("gpt-4o-mini")
    self.model_combo.set_sensitive(False)  # Disabled for Phase 1

    model_frame.add(self.model_combo)
    return model_frame
```

### 4. Token Usage Tracking

- Add dependency: `tiktoken` to requirements.txt
- Create `log_token_usage()` function
- Store daily usage in config.json
- Log to console for Phase 1

```python
def log_token_usage(usage):
    """Track token usage for cost monitoring"""
    if usage:
        print(f"Tokens used - Input: {usage.prompt_tokens}, "
              f"Output: {usage.completion_tokens}, "
              f"Total: {usage.total_tokens}")
        # TODO: Phase 2 - Add persistent storage
```

## Testing Checklist

- [ ] Existing Prompt Mode works identically to current version
- [ ] Model dropdown appears but is disabled (grayed out)
- [ ] Console shows token usage after each enhancement
- [ ] Simulate BadRequestError - verify retry logic works
- [ ] All three enhancement styles (concise/balanced/detailed) work
- [ ] No performance degradation

## Files to Modify

1. Create new: `model_config.py`
2. Modify: `enhance.py` - Refactor enhance_prompt function
3. Modify: `main.py` - Add model selector UI
4. Modify: `requirements.txt` - Add tiktoken
5. Update: `CLAUDE.md` - Document new architecture

## Rollback Plan

If issues arise, revert to direct GPT-4o-mini implementation:

- Remove model_config import
- Restore hardcoded parameters in enhance.py
- Remove model selector from UI

## Success Metrics

- Zero user-reported issues after deployment
- Token usage logged for all enhancements
- Codebase ready for Phase 2 model additions

## Dependencies

- OpenAI Python SDK (already installed)
- tiktoken library (to be added)

## Notes

- This is foundation work - no user-visible benefits yet
- Critical for preventing future breaking changes
- Sets up infrastructure for cost optimization in Phase 2/3
