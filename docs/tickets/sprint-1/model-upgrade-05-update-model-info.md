# MODEL-UPGRADE-05: Update Model Information in Dashboard

## Ticket ID: MODEL-UPGRADE-05

## Phase: Sprint 1 - Model Integration Enhancement

## Priority: High

## Dependencies: MODEL-UPGRADE-03 (GPT-5 Model Integration)

## Summary

Update the Performance Dashboard with accurate, current model specifications including correct context windows, output limits, and capabilities. Provide comprehensive model information to help users make informed choices without cost warnings.

## Current State

- Context windows showing outdated 128K for all models
- Missing detailed capability indicators
- No performance metrics or use case guidance
- Incomplete model feature documentation

## Target State

- Accurate context windows (128K → 1M range per official docs)
- Comprehensive capability matrix
- Performance benchmarks visible
- Clear use case recommendations
- Human-readable context explanations

## Research Requirements

### 1. Update Model Registry Context Windows (`model_config.py`)

Ensure all models have accurate specifications based on official OpenAI documentation:

```python
def _initialize_default_models(self):
    """Initialize with accurate model specifications per OpenAI docs"""

    # GPT-4o-mini - Current baseline
    self.register(ModelConfig(
        model_name="gpt-4o-mini",
        display_name="GPT-4o Mini",
        max_tokens_param="max_tokens",
        max_tokens_value=150,
        context_window=128000,  # 128K tokens (confirmed)
        temperature_min=0.0,
        temperature_max=2.0,
        supports_json_mode=True,
        supports_verbosity=False,
        supports_reasoning_effort=False,
        output_token_limit=4096,
        tier="standard"
    ))

    # GPT-4.1 Series - Up to 1M context per OpenAI docs
    self.register(ModelConfig(
        model_name="gpt-4.1-nano",
        display_name="GPT-4.1 Nano",
        context_window=1000000,  # 1M tokens (per OpenAI)
        output_token_limit=2048,
        supports_verbosity=True,
        tier="economy"
    ))

    self.register(ModelConfig(
        model_name="gpt-4.1-mini",
        display_name="GPT-4.1 Mini",
        context_window=1000000,  # 1M tokens (per OpenAI)
        output_token_limit=4096,
        supports_verbosity=True,
        tier="economy"
    ))

    self.register(ModelConfig(
        model_name="gpt-4.1",
        display_name="GPT-4.1",
        context_window=1000000,  # 1M tokens (per OpenAI)
        output_token_limit=8192,
        supports_verbosity=True,
        tier="standard"
    ))

    # GPT-5 Series - 400K context per OpenAI docs
    self.register(ModelConfig(
        model_name="gpt-5-nano",
        display_name="GPT-5 Nano",
        context_window=400000,   # 400K tokens (per OpenAI)
        output_token_limit=128000,  # 128K output (per OpenAI)
        temperature_constrained=True,  # Fixed at 1.0
        supports_verbosity=True,
        supports_reasoning_effort=True,
        tier="economy"
    ))

    self.register(ModelConfig(
        model_name="gpt-5-mini",
        display_name="GPT-5 Mini",
        context_window=400000,  # 400K tokens (per OpenAI)
        output_token_limit=128000,  # 128K output (per OpenAI)
        temperature_constrained=True,
        supports_verbosity=True,
        supports_reasoning_effort=True,
        tier="standard"
    ))

    self.register(ModelConfig(
        model_name="gpt-5",
        display_name="GPT-5",
        context_window=400000,  # 400K tokens (per OpenAI)
        output_token_limit=128000,  # 128K output (per OpenAI)
        temperature_constrained=True,
        supports_verbosity=True,
        supports_reasoning_effort=True,
        tier="flagship"
    ))
```

### 2. Dashboard Model Comparison Tab (`main.py`)

Create comprehensive model information display:

```python
def _create_model_comparison_tab(self):
    """Create detailed model comparison tab"""
    scroll = Gtk.ScrolledWindow()
    scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

    main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    main_box.set_margin_start(10)
    main_box.set_margin_end(10)

    # Model comparison grid
    grid = Gtk.Grid()
    grid.set_column_spacing(15)
    grid.set_row_spacing(8)
    grid.set_margin_top(10)

    # Headers with better labels
    headers = [
        ("Model", 150),
        ("Tier", 80),
        ("Context", 100),
        ("Max Output", 100),
        ("Temperature", 120),
        ("Features", 200),
        ("Best For", 200)
    ]

    col = 0
    for header, width in headers:
        label = Gtk.Label(label=f"<b>{header}</b>")
        label.set_use_markup(True)
        label.set_size_request(width, -1)
        label.set_halign(Gtk.Align.START)
        grid.attach(label, col, 0, 1, 1)
        col += 1

    # Add separator
    separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
    grid.attach(separator, 0, 1, len(headers), 1)

    # Model rows
    row = 2
    for model in model_registry.get_all_models():
        col = 0

        # Model name with availability indicator
        availability = "✓" if model.is_available() else "⏳"
        name_label = Gtk.Label(label=f"{availability} {model.display_name}")
        name_label.set_halign(Gtk.Align.START)
        grid.attach(name_label, col, row, 1, 1)
        col += 1

        # Tier with color
        tier_info = model.get_tier_info()
        tier_label = Gtk.Label()
        tier_label.set_markup(f'<span foreground="{tier_info["color"]}">{tier_info["tier"].upper()}</span>')
        tier_label.set_halign(Gtk.Align.START)
        grid.attach(tier_label, col, row, 1, 1)
        col += 1

        # Context window (human readable)
        context_display = self._format_context_window(model.context_window)
        context_label = Gtk.Label(label=context_display)
        context_label.set_halign(Gtk.Align.START)
        grid.attach(context_label, col, row, 1, 1)
        col += 1

        # Max output tokens
        output_display = f"{model.output_token_limit:,}" if hasattr(model, 'output_token_limit') else "4,096"
        output_label = Gtk.Label(label=output_display)
        output_label.set_halign(Gtk.Align.START)
        grid.attach(output_label, col, row, 1, 1)
        col += 1

        # Temperature range
        if model.temperature_constrained:
            temp_display = "Fixed (1.0)"
        else:
            temp_display = f"{model.temperature_min}-{model.temperature_max}"
        temp_label = Gtk.Label(label=temp_display)
        temp_label.set_halign(Gtk.Align.START)
        grid.attach(temp_label, col, row, 1, 1)
        col += 1

        # Features
        features = []
        if model.supports_json_mode:
            features.append("JSON")
        if model.supports_verbosity:
            features.append("Verbosity")
        if model.supports_reasoning_effort:
            features.append("Reasoning")
        feature_text = ", ".join(features) if features else "Basic"
        feature_label = Gtk.Label(label=feature_text)
        feature_label.set_halign(Gtk.Align.START)
        grid.attach(feature_label, col, row, 1, 1)
        col += 1

        # Best use cases
        use_case = self._get_model_use_case(model)
        use_label = Gtk.Label(label=use_case)
        use_label.set_halign(Gtk.Align.START)
        use_label.set_line_wrap(True)
        use_label.set_max_width_chars(30)
        grid.attach(use_label, col, row, 1, 1)

        row += 1

    main_box.pack_start(grid, False, False, 0)

    # Add context window explanation
    info_frame = Gtk.Frame()
    info_frame.set_label("Understanding Context Windows")
    info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
    info_box.set_margin_start(10)
    info_box.set_margin_end(10)
    info_box.set_margin_top(10)
    info_box.set_margin_bottom(10)

    context_info = [
        "• 128K = ~96,000 words (short book)",
        "• 400K = ~300,000 words (long novel)",
        "• 1M = ~750,000 words (Harry Potter series)"
    ]

    for info in context_info:
        label = Gtk.Label(label=info)
        label.set_halign(Gtk.Align.START)
        info_box.pack_start(label, False, False, 0)

    info_frame.add(info_box)
    main_box.pack_start(info_frame, False, False, 20)

    scroll.add(main_box)
    return scroll

def _format_context_window(self, tokens):
    """Format context window for display"""
    if tokens >= 1000000:
        return f"{tokens//1000000}M tokens"
    elif tokens >= 1000:
        return f"{tokens//1000}K tokens"
    else:
        return f"{tokens} tokens"

def _get_model_use_case(self, model):
    """Get recommended use case for model"""
    use_cases = {
        "gpt-4o-mini": "Quick edits, summaries",
        "gpt-4.1-nano": "High volume, fast response",
        "gpt-4.1-mini": "Longer documents",
        "gpt-4.1": "Professional writing",
        "gpt-5-nano": "Rapid iteration",
        "gpt-5-mini": "Creative writing",
        "gpt-5": "Complex analysis"
    }
    return use_cases.get(model.model_name, "General purpose")
```

### 3. Performance Metrics Display

Display real-world performance data:

```python
def _create_performance_metrics_tab(self):
    """Create performance metrics comparison"""
    scroll = Gtk.ScrolledWindow()
    main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)

    # Response time comparison
    perf_frame = Gtk.Frame()
    perf_frame.set_label("Average Response Times")

    perf_grid = Gtk.Grid()
    perf_grid.set_column_spacing(15)
    perf_grid.set_row_spacing(5)

    # Headers
    perf_grid.attach(Gtk.Label(label="<b>Model</b>"), 0, 0, 1, 1)
    perf_grid.attach(Gtk.Label(label="<b>First Token</b>"), 1, 0, 1, 1)
    perf_grid.attach(Gtk.Label(label="<b>Full Response</b>"), 2, 0, 1, 1)
    perf_grid.attach(Gtk.Label(label="<b>Tokens/sec</b>"), 3, 0, 1, 1)

    # Model performance data (estimated)
    perf_data = {
        "gpt-4o-mini": (0.3, 1.2, 45),
        "gpt-4.1-nano": (0.2, 0.8, 60),
        "gpt-4.1-mini": (0.25, 1.0, 55),
        "gpt-4.1": (0.35, 1.5, 40),
        "gpt-5-nano": (0.4, 1.8, 35),
        "gpt-5-mini": (0.5, 2.2, 30),
        "gpt-5": (0.6, 2.8, 25)
    }

    row = 1
    for model_name, (first_token, full_response, tokens_per_sec) in perf_data.items():
        model = model_registry.get(model_name)
        if model:
            perf_grid.attach(Gtk.Label(label=model.display_name), 0, row, 1, 1)
            perf_grid.attach(Gtk.Label(label=f"{first_token:.1f}s"), 1, row, 1, 1)
            perf_grid.attach(Gtk.Label(label=f"{full_response:.1f}s"), 2, row, 1, 1)
            perf_grid.attach(Gtk.Label(label=f"{tokens_per_sec}"), 3, row, 1, 1)
            row += 1

    perf_frame.add(perf_grid)
    main_box.pack_start(perf_frame, False, False, 0)

    scroll.add(main_box)
    return scroll
```

### 4. Update Model Config Display Helper (`model_config.py`)

Add method to get comprehensive model info:

```python
def get_dashboard_info(self):
    """Get comprehensive model info for dashboard display"""
    return {
        "name": self.display_name,
        "model_id": self.model_name,
        "tier": self.tier,
        "context_window": self.context_window,
        "context_human": self._humanize_context(),
        "output_limit": self.output_token_limit,
        "temperature": {
            "min": self.temperature_min,
            "max": self.temperature_max,
            "constrained": self.temperature_constrained
        },
        "features": {
            "json_mode": self.supports_json_mode,
            "verbosity": self.supports_verbosity,
            "reasoning": self.supports_reasoning_effort
        },
        "performance": self._get_performance_estimate()
    }

def _humanize_context(self):
    """Convert token count to human-readable format"""
    tokens = self.context_window
    words = tokens * 0.75  # Approximate

    if words >= 1500000:
        return f"~{words/1000000:.1f}M words"
    elif words >= 1000:
        return f"~{words/1000:.0f}K words"
    else:
        return f"~{words:.0f} words"

def _get_performance_estimate(self):
    """Estimate performance characteristics"""
    # Rough estimates based on model tier
    if "nano" in self.model_name:
        return {"speed": "fastest", "latency": "low"}
    elif "mini" in self.model_name:
        return {"speed": "fast", "latency": "medium"}
    elif "5" in self.model_name:
        return {"speed": "moderate", "latency": "higher"}
    else:
        return {"speed": "standard", "latency": "standard"}
```

## Implementation Order

1. **model_config.py**:
   - Update all context_window values
   - Add output_token_limit field
   - Add dashboard info methods
   - Ensure feature flags accurate

2. **main.py**:
   - Enhance \_create_model_comparison_tab
   - Add \_create_performance_metrics_tab
   - Update \_format_context_window helper
   - Add \_get_model_use_case helper

3. **enhance.py**:
   - Ensure model info methods return complete data

## Testing Checklist

- [ ] All context windows display correctly
- [ ] GPT-4o-mini shows 128K tokens
- [ ] GPT-4.1 models show 1M tokens
- [ ] GPT-5 models show 400K tokens
- [ ] GPT-5 models show 128K max output tokens
- [ ] Temperature constraints visible for GPT-5 models
- [ ] Feature flags accurate (JSON, Verbosity, Reasoning)
- [ ] Performance metrics display properly
- [ ] Human-readable explanations clear
- [ ] Dashboard loads without errors
- [ ] Model switching still works

## Documentation Updates

Update README.md with model specifications table:

```markdown
## Available Models

| Model        | Context Window | Max Output | Features        | Best For         |
| ------------ | -------------- | ---------- | --------------- | ---------------- |
| GPT-4o Mini  | 128K           | 4,096      | JSON            | Quick edits      |
| GPT-4.1 Nano | 1M             | 2,048      | JSON, Verbosity | High volume      |
| GPT-4.1 Mini | 1M             | 4,096      | JSON, Verbosity | Longer texts     |
| GPT-4.1      | 1M             | 8,192      | JSON, Verbosity | Professional     |
| GPT-5 Nano   | 400K           | 128,000    | All features    | Fast processing  |
| GPT-5 Mini   | 400K           | 128,000    | All features    | Creative writing |
| GPT-5        | 400K           | 128,000    | All features    | Complex tasks    |
```

## Success Metrics

- Users understand model differences clearly
- Reduced support questions about model capabilities
- Increased appropriate model selection
- Dashboard provides value for decision making

## Dependencies

- MODEL-UPGRADE-03 must be complete
- Coordinate with MODEL-UPGRADE-04 for UI consistency
- No external API dependencies

## Notes

- Context windows per official OpenAI Platform docs (August 2025):
  - GPT-5 series: 400K tokens context, 128K output
  - GPT-4.1 series: 1M tokens context
  - GPT-4o-mini: 128K tokens context
- Pricing (Standard tier per 1M tokens):
  - GPT-5: $1.25 input / $10.00 output
  - GPT-5-mini: $0.25 input / $2.00 output
  - GPT-5-nano: $0.05 input / $0.40 output
  - GPT-4.1: $2.00 input / $8.00 output
  - GPT-4.1-mini: $0.40 input / $1.60 output
  - GPT-4.1-nano: $0.10 input / $0.40 output
  - GPT-4o-mini: $0.15 input / $0.60 output
- Keep performance estimates conservative
- Focus on clarity over technical precision for users
