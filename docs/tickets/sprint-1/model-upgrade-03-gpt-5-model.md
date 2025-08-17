# Build Ticket: GPT-5 Integration & Breaking Change Handling

**Ticket ID**: MODEL-UPGRADE-03  
**Phase**: 3 - GPT-5 Release  
**Priority**: High  
**Estimated Effort**: 6-8 hours  
**Target Date**: Mid-2026 (upon GPT-5 availability)

## Overview

Integrate GPT-5-nano and GPT-5-mini models with full support for breaking parameter changes. This phase handles the `max_tokens` → `max_completion_tokens` migration and potential temperature constraints while implementing tiered pricing options.

## Background

GPT-5 series introduces breaking changes that would crash existing OpenAI implementations. Our Phase 1 architecture prepares for this, but Phase 3 requires careful handling of new parameters and potential temperature limitations.

## Critical Breaking Changes

1. **Parameter rename**: `max_tokens` → `max_completion_tokens`
2. **Temperature constraint**: Possibly fixed at 1.0 (unconfirmed)
3. **New parameters**: `verbosity`, `reasoning_effort`

## Acceptance Criteria

- [ ] GPT-5-nano and GPT-5-mini configurations working
- [ ] Breaking parameter changes handled gracefully
- [ ] Temperature constraint workarounds implemented
- [ ] All four models available in dropdown
- [ ] Tiered pricing visible (nano: $0.05/1K, mini: $0.25/1K)
- [ ] Performance metrics dashboard added
- [ ] Migration guide for users documented
- [ ] Zero crashes when switching between GPT-4 and GPT-5 models

## Technical Requirements

### 1. Add GPT-5 Configurations (`model_config.py`)

```python
MODEL_CONFIGS = {
    # Existing GPT-4 configs...

    "gpt-5-nano": {
        "model_name": "gpt-5-nano",
        "max_tokens_param": "max_completion_tokens",  # BREAKING CHANGE
        "max_tokens_value": 1000,
        "temperature": 1.0,  # May be constrained
        "supports_verbosity": True,
        "supports_reasoning": True,
        "verbosity_default": "low",
        "reasoning_effort": "low",
        "display_name": "GPT-5 Nano (Fast)",
        "cost_per_1k": 0.05,  # 67% cheaper than current!
        "tier": "economy"
    },
    "gpt-5-mini": {
        "model_name": "gpt-5-mini",
        "max_tokens_param": "max_completion_tokens",  # BREAKING CHANGE
        "max_tokens_value": 1000,
        "temperature": 1.0,
        "supports_verbosity": True,
        "supports_reasoning": True,
        "verbosity_default": "medium",
        "reasoning_effort": "medium",
        "display_name": "GPT-5 Mini (Premium)",
        "cost_per_1k": 0.25,  # 67% more expensive
        "tier": "premium"
    }
}
```

### 2. Enhanced Parameter Handling (`enhance.py`)

```python
def enhance_prompt(transcript, style="balanced", model_key=None):
    if model_key is None:
        config = load_config()
        model_key = config.get("selected_model", "gpt-5-nano")  # New default

    model_config = get_model_config(model_key)

    # Build base parameters
    params = {
        "model": model_config["model_name"],
        "messages": [
            {"role": "system", "content": get_enhanced_prompt(style, model_config)},
            {"role": "user", "content": transcript}
        ],
        "timeout": 15.0
    }

    # CRITICAL: Handle parameter name difference
    token_param = model_config["max_tokens_param"]
    params[token_param] = model_config["max_tokens_value"]

    # Handle temperature constraint
    if model_config.get("temperature_constrained", False):
        # Use verbosity to control output style instead of temperature
        params["temperature"] = 1.0
        params["verbosity"] = map_style_to_verbosity_strict(style)
    else:
        params["temperature"] = model_config["temperature"]

    # Add GPT-5 specific parameters
    if model_config.get("supports_verbosity"):
        verbosity_map = {
            "concise": "low",
            "balanced": "medium",
            "detailed": "high"
        }
        params["verbosity"] = verbosity_map.get(style, "medium")

    if model_config.get("supports_reasoning"):
        params["reasoning_effort"] = model_config.get("reasoning_effort", "low")

    # Execute with robust error handling
    return call_with_fallback(params, model_key)

def call_with_fallback(params, model_key):
    """Call API with automatic fallback on parameter errors"""
    try:
        response = client.chat.completions.create(**params)
        return response.choices[0].message.content.strip(), None

    except openai.BadRequestError as e:
        error_msg = str(e)

        # Handle max_tokens error specifically
        if "max_tokens" in error_msg and "max_completion_tokens" in error_msg:
            # Swap parameter names
            if "max_tokens" in params:
                params["max_completion_tokens"] = params.pop("max_tokens")
            elif "max_completion_tokens" in params:
                params["max_tokens"] = params.pop("max_completion_tokens")

            # Retry with swapped parameter
            response = client.chat.completions.create(**params)
            return response.choices[0].message.content.strip(), None

        # Handle temperature constraint error
        elif "temperature" in error_msg:
            params["temperature"] = 1.0  # Force to constraint
            response = client.chat.completions.create(**params)
            return response.choices[0].message.content.strip(), None

        # Unknown error - fall back to GPT-4o-mini
        else:
            print(f"GPT-5 error, falling back: {error_msg}")
            return enhance_prompt(transcript, style, "gpt-4o-mini")
```

### 3. Tiered UI with Cost Warnings (`main.py`)

```python
def create_model_selector(self):
    model_frame = Gtk.Frame()
    model_frame.set_label("AI Model")

    vbox = Gtk.VBox(spacing=5)

    # Model dropdown
    self.model_combo = Gtk.ComboBoxText()

    # Group models by tier
    economy_models = []
    standard_models = []
    premium_models = []

    for model_key, config in MODEL_CONFIGS.items():
        tier = config.get("tier", "standard")
        display = f"{config['display_name']} (${config['cost_per_1k']}/1K)"

        if tier == "economy":
            economy_models.append((model_key, display))
        elif tier == "premium":
            premium_models.append((model_key, display))
        else:
            standard_models.append((model_key, display))

    # Add with separators
    if economy_models:
        self.model_combo.append("", "── Economy ──")
        for key, display in economy_models:
            self.model_combo.append(key, f"  {display}")

    if standard_models:
        self.model_combo.append("", "── Standard ──")
        for key, display in standard_models:
            self.model_combo.append(key, f"  {display}")

    if premium_models:
        self.model_combo.append("", "── Premium ──")
        for key, display in premium_models:
            self.model_combo.append(key, f"  {display}")

    # Set default to GPT-5-nano (economy)
    saved_model = self.config.get("selected_model", "gpt-5-nano")
    self.model_combo.set_active_id(saved_model)
    self.model_combo.connect("changed", self.on_model_changed)

    vbox.pack_start(self.model_combo, False, False, 0)

    # Cost estimate label
    self.cost_estimate = Gtk.Label()
    self.update_cost_estimate()
    vbox.pack_start(self.cost_estimate, False, False, 0)

    # Performance indicator
    self.perf_label = Gtk.Label()
    self.update_performance_label()
    vbox.pack_start(self.perf_label, False, False, 0)

    model_frame.add(vbox)
    return model_frame

def on_model_changed(self, combo):
    """Handle model selection with cost warning"""
    model_key = combo.get_active_id()

    if not model_key:  # Separator selected
        combo.set_active_id(self.config.get("selected_model", "gpt-5-nano"))
        return

    old_model = self.config.get("selected_model", "gpt-5-nano")
    old_cost = MODEL_CONFIGS[old_model]["cost_per_1k"]
    new_cost = MODEL_CONFIGS[model_key]["cost_per_1k"]

    # Warn if switching to more expensive model
    if new_cost > old_cost * 2:
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.YES_NO,
            text=f"Cost Warning"
        )
        dialog.format_secondary_text(
            f"Switching to {MODEL_CONFIGS[model_key]['display_name']} will increase "
            f"costs by {int((new_cost/old_cost - 1) * 100)}%. Continue?"
        )
        response = dialog.run()
        dialog.destroy()

        if response != Gtk.ResponseType.YES:
            combo.set_active_id(old_model)
            return

    self.config["selected_model"] = model_key
    self.save_config()
    self.update_cost_estimate()
    self.update_performance_label()
```

### 4. Performance Monitoring Dashboard

```python
def create_performance_dashboard(self):
    """Create metrics dashboard for model comparison"""
    dashboard = Gtk.Window()
    dashboard.set_title("Model Performance Metrics")
    dashboard.set_default_size(600, 400)

    grid = Gtk.Grid()
    grid.set_column_spacing(10)
    grid.set_row_spacing(10)

    # Headers
    grid.attach(Gtk.Label("Model"), 0, 0, 1, 1)
    grid.attach(Gtk.Label("Uses"), 1, 0, 1, 1)
    grid.attach(Gtk.Label("Avg Latency"), 2, 0, 1, 1)
    grid.attach(Gtk.Label("Cost/1K"), 3, 0, 1, 1)
    grid.attach(Gtk.Label("Quality"), 4, 0, 1, 1)

    # Model stats
    stats = self.config.get("model_usage_stats", {})
    row = 1

    for model_key in ["gpt-4o-mini", "gpt-4.1-mini", "gpt-5-nano", "gpt-5-mini"]:
        if model_key in stats:
            data = stats[model_key]
            grid.attach(Gtk.Label(MODEL_CONFIGS[model_key]["display_name"]), 0, row, 1, 1)
            grid.attach(Gtk.Label(str(data["count"])), 1, row, 1, 1)
            grid.attach(Gtk.Label(f"{data['avg_latency']:.2f}s"), 2, row, 1, 1)
            grid.attach(Gtk.Label(f"${MODEL_CONFIGS[model_key]['cost_per_1k']}"), 3, row, 1, 1)

            # Quality score (based on enhancement success)
            quality = data.get("success_rate", 100)
            grid.attach(Gtk.Label(f"{quality}%"), 4, row, 1, 1)
            row += 1

    dashboard.add(grid)
    dashboard.show_all()
```

## Testing Checklist

- [ ] GPT-5-nano enhances successfully
- [ ] GPT-5-mini enhances with premium quality
- [ ] Switching between GPT-4 and GPT-5 models works
- [ ] Parameter mismatch errors handled gracefully
- [ ] Temperature constraint workaround effective
- [ ] Cost warnings appear for expensive models
- [ ] Performance dashboard shows accurate metrics
- [ ] Fallback to GPT-4o-mini on GPT-5 errors
- [ ] Verbosity parameter controls output length
- [ ] Reasoning effort affects response quality

## Migration Strategy

1. **Soft Launch**: Enable GPT-5-nano for power users
2. **Monitor**: Track error rates and quality metrics
3. **Gradual Rollout**: Enable for all users after 1 week
4. **Default Change**: Set GPT-5-nano as default after 2 weeks
5. **Premium Tier**: Offer GPT-5-mini as opt-in premium

## Files to Modify

1. `model_config.py` - Add GPT-5 configurations
2. `enhance.py` - Implement parameter handling and fallback
3. `main.py` - Add tiered UI and performance dashboard
4. `config.json` - Track usage metrics
5. `README.md` - Document breaking changes and migration
6. `CLAUDE.md` - Update with GPT-5 architecture notes

## Risk Mitigation

- **Parameter Errors**: Automatic retry with correct parameters
- **Temperature Issues**: Use verbosity as alternative control
- **Cost Overruns**: Warnings and default to cheapest model
- **Quality Drop**: Track metrics and allow model switching
- **API Failures**: Graceful fallback to GPT-4 models

## Success Metrics

- 80% of users adopt GPT-5-nano within 1 month
- 67% cost reduction for average user
- <1% error rate from parameter changes
- Quality scores maintain 90%+ satisfaction
- Zero application crashes from breaking changes

## Dependencies

- Phases 1 & 2 complete
- GPT-5 API access
- Updated OpenAI Python SDK
- User communication about changes

## Notes

- Most complex phase due to breaking changes
- Critical to test thoroughly before wide release
- Consider A/B testing with small user groups
- Prepare detailed migration guide for users
- Monitor closely for first month after release
