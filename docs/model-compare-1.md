# OpenAI Model Parameter Comparison Report

Voice Transcribe Prompt Mode - Model Migration Analysis

## Executive Summary

This report analyzes the parameter differences between OpenAI's GPT-4o-mini (current implementation) and the upcoming GPT-4.1/GPT-5 models for Voice Transcribe's Prompt Mode feature. Key findings indicate breaking changes in the GPT-5 series, particularly the replacement of `max_tokens` with `max_completion_tokens` and temperature constraints. A model-agnostic architecture is recommended to handle these differences gracefully.

## Current Implementation (GPT-4o-mini)

### Parameters in Use (enhance.py)

```python
# Current parameters from enhance.py:76-84
model="gpt-4o-mini"
messages=[...]
max_tokens=1000
temperature=0.3
timeout=15.0
```

### GPT-4o-mini Supported Parameters

- **model**: String identifying the model
- **messages**: Array of message objects with role and content
- **max_tokens**: Maximum tokens to generate (1-4096)
- **temperature**: Sampling temperature (0.0-2.0, typically 0-1)
- **timeout**: Request timeout in seconds
- **top_p**: Nucleus sampling (0-1)
- **frequency_penalty**: Reduce repetition (-2.0 to 2.0)
- **presence_penalty**: Encourage new topics (-2.0 to 2.0)
- **stop**: Stop sequences (up to 4)
- **stream**: Enable streaming responses
- **response_format**: JSON mode configuration
- **tools**: Function calling definitions
- **seed**: Deterministic sampling

## GPT-4.1 Expected Parameters

Based on OpenAI's incremental versioning pattern, GPT-4.1 is expected to maintain backward compatibility with GPT-4o-mini while adding enhancements:

### Likely Parameters

- All GPT-4o-mini parameters retained
- **max_tokens**: Still supported (maintaining compatibility)
- **temperature**: Same range (0.0-2.0)
- **Enhanced context**: Possibly increased from 128K to 256K tokens
- **reasoning_effort**: Potential new parameter for o1-style reasoning
- **verbosity**: Control response length (low/medium/high)

### Migration Impact

- **Minimal code changes required**
- **Direct drop-in replacement likely**
- **Cost reduction: 53% on input ($0.07/1M vs $0.15/1M)**

## GPT-5 Series Breaking Changes

### Critical Parameter Changes

#### 1. max_tokens → max_completion_tokens

```python
# GPT-4o-mini/GPT-4.1 (current)
response = client.chat.completions.create(
    model="gpt-4o-mini",
    max_tokens=1000,  # ✓ Works
    ...
)

# GPT-5 series (breaking change)
response = client.chat.completions.create(
    model="gpt-5-mini",
    max_completion_tokens=1000,  # ✓ New parameter name
    # max_tokens=1000,  # ✗ Raises BadRequestError
    ...
)
```

**Error if using old parameter:**

```
litellm.BadRequestError: OpenAIException - Unsupported parameter:
'max_tokens' is not supported with this model.
Use 'max_completion_tokens' instead.
```

#### 2. Temperature Constraints (Unconfirmed)

Reports suggest GPT-5 models may have temperature limitations:

- **Possible constraint**: Temperature fixed at 1.0
- **Alternative**: Limited range (0.8-1.2)
- **Impact**: Reduced control over output consistency

**Concern for Voice Transcribe**:

- Current setting: `temperature=0.3` for consistency
- GPT-5: May produce more varied outputs
- Mitigation: Use `verbosity` and `reasoning_effort` parameters

### New GPT-5 Parameters

#### verbosity

Controls response length and detail:

```python
verbosity="low"     # Concise, direct answers
verbosity="medium"  # Balanced responses (default)
verbosity="high"    # Comprehensive, detailed answers
```

#### reasoning_effort

Controls computational depth:

```python
reasoning_effort="low"      # Fast, simple responses
reasoning_effort="medium"   # Standard processing
reasoning_effort="high"     # Deep reasoning (slower, more expensive)
```

#### Extended Context Windows

- **Standard**: 256K tokens
- **Extended**: Up to 1M tokens (with special configuration)
- **Comparison**: 4x larger than GPT-4-turbo

## Model-Agnostic Implementation Strategy

### Recommended Architecture

```python
# config.py or .env
MODEL_CONFIGS = {
    "gpt-4o-mini": {
        "model_name": "gpt-4o-mini",
        "max_tokens_param": "max_tokens",
        "max_tokens_value": 1000,
        "temperature": 0.3,
        "supports_verbosity": False,
        "supports_reasoning": False
    },
    "gpt-4.1-mini": {
        "model_name": "gpt-4.1-mini",
        "max_tokens_param": "max_tokens",
        "max_tokens_value": 1000,
        "temperature": 0.3,
        "supports_verbosity": True,
        "supports_reasoning": False
    },
    "gpt-5-mini": {
        "model_name": "gpt-5-mini",
        "max_tokens_param": "max_completion_tokens",
        "max_tokens_value": 1000,
        "temperature": 1.0,  # If constrained
        "supports_verbosity": True,
        "supports_reasoning": True,
        "verbosity": "low",  # Maps to "concise" style
        "reasoning_effort": "low"
    },
    "gpt-5-nano": {
        "model_name": "gpt-5-nano",
        "max_tokens_param": "max_completion_tokens",
        "max_tokens_value": 1000,
        "temperature": 1.0,
        "supports_verbosity": True,
        "supports_reasoning": True,
        "verbosity": "low",
        "reasoning_effort": "low"
    }
}

# Enhanced enhance.py implementation
def enhance_prompt(transcript: str, style: str = "balanced", model_key: str = "gpt-4o-mini"):
    config = MODEL_CONFIGS[model_key]

    # Build parameters dynamically
    params = {
        "model": config["model_name"],
        "messages": [
            {"role": "system", "content": ENHANCEMENT_PROMPTS[style]},
            {"role": "user", "content": transcript}
        ],
        config["max_tokens_param"]: config["max_tokens_value"],
        "temperature": config["temperature"],
        "timeout": 15.0
    }

    # Add model-specific parameters
    if config.get("supports_verbosity"):
        verbosity_map = {
            "concise": "low",
            "balanced": "medium",
            "detailed": "high"
        }
        params["verbosity"] = verbosity_map.get(style, "medium")

    if config.get("supports_reasoning"):
        params["reasoning_effort"] = config.get("reasoning_effort", "low")

    try:
        response = client.chat.completions.create(**params)
        return response.choices[0].message.content.strip(), None
    except openai.BadRequestError as e:
        # Handle parameter incompatibility
        if "max_tokens" in str(e) and "max_completion_tokens" in str(e):
            # Retry with corrected parameter
            params["max_completion_tokens"] = params.pop("max_tokens", 1000)
            response = client.chat.completions.create(**params)
            return response.choices[0].message.content.strip(), None
        raise
```

### UI Integration

```python
# main.py additions for model selection
def create_model_selector(self):
    """Create model selection dropdown"""
    model_frame = Gtk.Frame()
    model_frame.set_label("AI Model")

    model_combo = Gtk.ComboBoxText()
    model_combo.set_entry_text_column(0)

    # Add available models
    for model_key, config in MODEL_CONFIGS.items():
        display_name = f"{config['model_name']} (${self.get_model_cost(model_key)}/1K)"
        model_combo.append(model_key, display_name)

    model_combo.set_active_id(self.config.get("selected_model", "gpt-4o-mini"))
    model_combo.connect("changed", self.on_model_changed)

    model_frame.add(model_combo)
    return model_frame

def get_model_cost(self, model_key):
    """Return formatted cost per 1K tokens"""
    costs = {
        "gpt-4o-mini": "0.15",
        "gpt-4.1-mini": "0.07",
        "gpt-5-mini": "0.25",
        "gpt-5-nano": "0.05"
    }
    return costs.get(model_key, "N/A")
```

## Implementation Recommendations

### Phase 1: Immediate Actions

1. **Abstract parameter handling** - Create model configuration dictionary
2. **Add fallback logic** - Handle BadRequestError for parameter mismatches
3. **UI preparation** - Add model selector dropdown (disabled initially)
4. **Cost tracking** - Implement token usage monitoring

### Phase 2: GPT-4.1 Release (Q1 2026)

1. **Add GPT-4.1 configuration** - Simple config addition
2. **Enable UI selector** - Allow users to choose model
3. **A/B testing** - Compare performance vs GPT-4o-mini
4. **Monitor costs** - Validate expected savings

### Phase 3: GPT-5 Release (Mid-2026)

1. **Add GPT-5 configurations** - Handle new parameters
2. **Temperature workaround** - If constrained, use verbosity for control
3. **Tiered pricing** - Offer GPT-5-nano as default, GPT-5-mini as premium
4. **Performance monitoring** - Track latency and quality metrics

## Risk Mitigation

### Temperature Constraint Impact

If GPT-5 enforces `temperature=1.0`:

- **Risk**: Less consistent prompt enhancements
- **Mitigation**:
  - Use `verbosity="low"` for concise style
  - Implement prompt engineering to request consistency
  - Consider post-processing to normalize outputs

### Breaking Changes

- **Risk**: Application breaks when switching models
- **Mitigation**:
  - Try-catch blocks around API calls
  - Automatic parameter translation
  - Fallback to previous model on errors

### Cost Overruns

- **Risk**: GPT-5-mini costs 67% more than GPT-4o-mini
- **Mitigation**:
  - Default to GPT-5-nano (67% cheaper)
  - Implement usage quotas
  - Show cost estimates in UI

## Testing Strategy

### Compatibility Matrix

```
Model         | max_tokens | max_completion_tokens | temperature | verbosity
-------------|------------|----------------------|-------------|----------
gpt-4o-mini  | ✓          | ✗                    | 0.0-2.0     | ✗
gpt-4.1-mini | ✓          | ?                    | 0.0-2.0     | ✓
gpt-5-mini   | ✗          | ✓                    | 1.0 only?   | ✓
gpt-5-nano   | ✗          | ✓                    | 1.0 only?   | ✓
```

### Test Cases

1. **Parameter compatibility** - Verify each model accepts correct parameters
2. **Error handling** - Confirm graceful fallback on parameter errors
3. **Output quality** - Compare enhancement quality across models
4. **Cost tracking** - Validate token usage and billing
5. **Latency** - Measure response times for each model

## Conclusion

The transition from GPT-4o-mini to GPT-5 models requires careful handling of breaking parameter changes, particularly the `max_tokens` → `max_completion_tokens` rename and potential temperature constraints. By implementing a model-agnostic architecture now, Voice Transcribe can seamlessly support multiple models, allowing users to choose based on their cost-performance preferences. The recommended approach prioritizes backward compatibility while preparing for future model capabilities, ensuring a smooth migration path as new models become available.

## References

1. OpenAI Python SDK Documentation (Context7)
2. LiteLLM Issue #13381 - GPT-5 max_tokens parameter change
3. OpenAI GPT-5 Developer Announcement (August 7, 2025)
4. Cursor IDE GPT-5 API Guide (August 2025)
5. Current Voice Transcribe implementation (enhance.py:76-84)
