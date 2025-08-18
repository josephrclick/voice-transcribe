# GPT-5 Migration Guide

## Overview

This guide helps you transition from GPT-4 models to the new GPT-5 series, which offer significant cost savings and performance improvements. The application handles all breaking changes automatically, ensuring a smooth migration experience.

## Model Tiers

### 🟢 Economy Tier

- **GPT-5 Nano**: $0.05/1K tokens - 67% cheaper than GPT-4o-mini
- **GPT-4.1 Nano**: $0.03/1K tokens - 80% cheaper than GPT-4o-mini
- Best for: Quick enhancements, cost-conscious usage

### 🔵 Standard Tier

- **GPT-5 Mini**: $0.12/1K tokens - Balanced performance
- **GPT-4.1**: $0.07/1K tokens - 53% cheaper than GPT-4o-mini
- **GPT-4o Mini**: $0.15/1K tokens - Original model
- Best for: Regular daily use, quality enhancements

### 🟣 Premium Tier

- **GPT-5**: $0.30/1K tokens - Advanced reasoning
- Best for: Complex enhancements, maximum quality

## What's New in GPT-5

### Breaking Changes (Handled Automatically)

1. **Parameter Rename**: `max_tokens` → `max_completion_tokens`
   - The app automatically uses the correct parameter
   - No action required from users

2. **Temperature Constraints**: Limited to 0.1-0.9 range
   - Style control now uses verbosity parameter
   - Your enhancement preferences still work the same

3. **New Features**:
   - **Reasoning Effort**: Controls depth of analysis
   - **Verbosity**: Fine-grained output length control
   - **Enhanced Context**: Up to 1M token windows

## Migration Steps

### For New Users

1. **Default Selection**: GPT-5 Nano is now the default
2. **Cost Savings**: Immediate 67% reduction in API costs
3. **No Setup Required**: Just start using the app

### For Existing Users

#### Option 1: Automatic Migration (Recommended)

1. Open the application
2. You'll see the new tiered model selector
3. GPT-5 Nano will be pre-selected
4. Start recording - everything works seamlessly

#### Option 2: Manual Selection

1. Click the model dropdown
2. Choose your preferred tier:
   - Economy → for maximum savings
   - Standard → for balanced use
   - Premium → for advanced features
3. Confirm any cost warnings if switching to expensive models

## Cost Comparison

| Model        | Old Cost | New Cost | Savings     |
| ------------ | -------- | -------- | ----------- |
| GPT-4o-mini  | $0.15/1K | -        | Baseline    |
| GPT-4.1 Nano | -        | $0.03/1K | 80% cheaper |
| GPT-5 Nano   | -        | $0.05/1K | 67% cheaper |
| GPT-4.1      | -        | $0.07/1K | 53% cheaper |
| GPT-5 Mini   | -        | $0.12/1K | 20% cheaper |
| GPT-5        | -        | $0.30/1K | 100% more   |

## Performance Dashboard

Access the new performance dashboard with `Ctrl+D` to:

- Track usage by model
- Monitor costs in real-time
- Compare model performance
- View enhancement success rates

## FAQ

### Q: Will my existing prompts still work?

**A:** Yes! All your enhancement styles and preferences are preserved. The app translates them to GPT-5's new parameters automatically.

### Q: What if GPT-5 fails?

**A:** The app includes automatic fallback: GPT-5 → GPT-4.1 → GPT-4o-mini. You'll never experience a failed enhancement due to model issues.

### Q: Can I switch back to GPT-4?

**A:** Yes, all GPT-4 models remain available in the dropdown. You can switch anytime.

### Q: How do I know which model I'm using?

**A:** The current model is displayed in:

- The model dropdown (with tier and cost)
- The performance dashboard
- Session cost tracking in the header

### Q: Are there any features I'll lose?

**A:** No. GPT-5 models support all existing features plus new capabilities like reasoning effort control.

### Q: What about rate limits?

**A:** GPT-5 models have generous rate limits. The app handles any rate limiting automatically with intelligent retry logic.

## Troubleshooting

### Issue: "Parameter error" messages

**Solution:** The app auto-corrects parameter mismatches. If you see this briefly, it's normal - the retry succeeds immediately.

### Issue: Higher costs than expected

**Solution:**

1. Check your selected model in the dropdown
2. Open performance dashboard (`Ctrl+D`)
3. Switch to an economy tier model
4. GPT-5 Nano recommended for most use cases

### Issue: Different enhancement quality

**Solution:**

1. GPT-5 uses verbosity instead of temperature for style
2. Try adjusting your enhancement style:
   - Concise → Low verbosity
   - Balanced → Medium verbosity
   - Detailed → High verbosity

## Best Practices

1. **Start with GPT-5 Nano**: It's 67% cheaper and handles most tasks perfectly
2. **Use the Dashboard**: Monitor your usage patterns to optimize costs
3. **Upgrade Selectively**: Only use premium models for complex enhancements
4. **Enable Prompt Mode**: Only enhance when you need it to save costs
5. **Review Session Costs**: Check the header for real-time cost tracking

## Technical Details

### API Parameter Mapping

```python
# GPT-4 (old)
{
    "model": "gpt-4o-mini",
    "max_tokens": 1000,
    "temperature": 0.7
}

# GPT-5 (new)
{
    "model": "gpt-5-nano",
    "max_completion_tokens": 1000,
    "temperature": 0.5,  # Constrained range
    "reasoning_effort": "low",
    "verbosity": "medium"
}
```

### Fallback Chain

```
GPT-5 → GPT-4.1 → GPT-4o-mini
```

### Cost Calculation

```python
cost = (input_tokens / 1000) * input_rate + (output_tokens / 1000) * output_rate
```

## Support

If you experience any issues:

1. Check this migration guide
2. Review the performance dashboard for errors
3. Ensure your API key has GPT-5 access
4. Report issues at: https://github.com/josephrclick/voice-transcribe/issues

## Summary

The GPT-5 migration offers:

- ✅ **67% cost reduction** with GPT-5 Nano
- ✅ **Zero breaking changes** for users
- ✅ **Automatic fallback** for reliability
- ✅ **Enhanced features** like reasoning control
- ✅ **Full backward compatibility**

Simply update the app and start saving immediately!
