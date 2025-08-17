# Build Ticket: GPT-4.1 Integration & Model Selection

**Ticket ID**: MODEL-UPGRADE-02  
**Phase**: 2 - GPT-4.1 Release  
**Priority**: Medium  
**Estimated Effort**: 2-3 hours  
**Target Date**: Q1 2026 (upon GPT-4.1 availability)

## Overview

Add GPT-4.1-mini support and enable user model selection in Voice Transcribe's Prompt Mode. This phase activates the model-agnostic architecture from Phase 1 and delivers immediate cost savings (53% reduction on input tokens).

## Background

GPT-4.1-mini is expected to maintain backward compatibility while offering significant cost reduction ($0.07/1M input vs $0.15/1M for GPT-4o-mini). Phase 1 architecture makes this a simple configuration addition.

## Acceptance Criteria

- [ ] GPT-4.1-mini configuration added and working
- [ ] Model selector dropdown enabled in UI
- [ ] User selection persists in config.json
- [ ] Seamless switching between GPT-4o-mini and GPT-4.1-mini
- [ ] Cost savings visible in UI ($0.07 vs $0.15 per 1K)
- [ ] A/B testing metrics collected
- [ ] Documentation updated with model comparison

## Technical Requirements

### 1. Add GPT-4.1 Configuration (`model_config.py`)

```python
MODEL_CONFIGS = {
    "gpt-4o-mini": {
        # Existing config...
    },
    "gpt-4.1-mini": {
        "model_name": "gpt-4.1-mini",
        "max_tokens_param": "max_tokens",
        "max_tokens_value": 1000,
        "temperature": 0.3,
        "supports_verbosity": True,  # New feature
        "supports_reasoning": False,
        "display_name": "GPT-4.1 Mini",
        "cost_per_1k": 0.07  # 53% cheaper!
    }
}
```

### 2. Enable Model Selector (`main.py`)

```python
def create_model_selector(self):
    model_frame = Gtk.Frame()
    model_frame.set_label("AI Model")

    self.model_combo = Gtk.ComboBoxText()

    # Populate available models
    for model_key, config in MODEL_CONFIGS.items():
        if model_key in ["gpt-4o-mini", "gpt-4.1-mini"]:  # Phase 2 models
            display = f"{config['display_name']} (${config['cost_per_1k']}/1K)"
            self.model_combo.append(model_key, display)

    # Load saved preference
    saved_model = self.config.get("selected_model", "gpt-4o-mini")
    self.model_combo.set_active_id(saved_model)
    self.model_combo.set_sensitive(True)  # Enable for Phase 2
    self.model_combo.connect("changed", self.on_model_changed)

    model_frame.add(self.model_combo)
    return model_frame

def on_model_changed(self, combo):
    """Handle model selection change"""
    model_key = combo.get_active_id()
    self.config["selected_model"] = model_key
    self.save_config()

    # Log for A/B testing
    print(f"Model switched to: {model_key}")
    self.track_model_usage(model_key)
```

### 3. Update Enhancement Call (`enhance.py`)

```python
def enhance_prompt(transcript, style="balanced", model_key=None):
    # Use provided model or fall back to saved preference
    if model_key is None:
        config = load_config()
        model_key = config.get("selected_model", "gpt-4o-mini")

    model_config = get_model_config(model_key)

    # Handle new verbosity parameter for GPT-4.1
    if model_config.get("supports_verbosity"):
        params["verbosity"] = map_style_to_verbosity(style)

    # Rest of implementation...
```

### 4. A/B Testing Metrics

```python
def track_model_usage(self, model_key):
    """Track model usage for A/B testing"""
    usage_stats = self.config.get("model_usage_stats", {})

    # Initialize if needed
    if model_key not in usage_stats:
        usage_stats[model_key] = {
            "count": 0,
            "total_tokens": 0,
            "avg_latency": 0,
            "user_rating": []
        }

    usage_stats[model_key]["count"] += 1
    self.config["model_usage_stats"] = usage_stats
    self.save_config()

def compare_models_performance(self):
    """Generate A/B test comparison report"""
    stats = self.config.get("model_usage_stats", {})

    for model, data in stats.items():
        print(f"\n{model} Performance:")
        print(f"  Uses: {data['count']}")
        print(f"  Avg Latency: {data['avg_latency']:.2f}s")
        print(f"  Cost/1K: ${MODEL_CONFIGS[model]['cost_per_1k']}")
```

### 5. Cost Display Enhancement

```python
def update_cost_display(self):
    """Show estimated cost savings"""
    current_model = self.config.get("selected_model", "gpt-4o-mini")
    tokens_used = self.config.get("total_tokens_month", 0)

    current_cost = (tokens_used / 1000) * MODEL_CONFIGS[current_model]["cost_per_1k"]

    # Show savings if using GPT-4.1
    if current_model == "gpt-4.1-mini":
        old_cost = (tokens_used / 1000) * 0.15
        savings = old_cost - current_cost
        self.cost_label.set_text(f"Monthly savings: ${savings:.2f}")
```

## Testing Checklist

- [ ] GPT-4.1-mini successfully enhances prompts
- [ ] Model switching works without app restart
- [ ] Preference persists after app restart
- [ ] Both models produce quality enhancements
- [ ] Verbosity parameter works with GPT-4.1
- [ ] Cost calculations are accurate
- [ ] A/B metrics collected correctly
- [ ] Fallback to GPT-4o-mini if GPT-4.1 fails

## Migration Steps

1. Deploy update with GPT-4.1 config
2. Test with small user group
3. Monitor error rates and latency
4. Enable for all users if stable
5. Set GPT-4.1 as default after validation

## Files to Modify

1. `model_config.py` - Add GPT-4.1 configuration
2. `main.py` - Enable model selector, add tracking
3. `enhance.py` - Handle verbosity parameter
4. `config.json` - Auto-updated with selection
5. `README.md` - Document new model option

## Rollback Plan

If GPT-4.1 issues arise:

- Set default back to GPT-4o-mini in config
- Disable GPT-4.1 option in dropdown
- No code rollback needed due to Phase 1 architecture

## Success Metrics

- 50% of users switch to GPT-4.1 within first week
- 53% reduction in API costs
- No increase in enhancement latency
- User satisfaction maintained or improved
- Zero critical errors from model switching

## Dependencies

- Phase 1 must be complete
- GPT-4.1-mini API availability
- OpenAI account supports new model

## Notes

- First user-visible benefit of model architecture
- Monitor closely for quality differences
- Consider making GPT-4.1 default after 2 weeks if stable
- Prepare messaging about cost savings for users
