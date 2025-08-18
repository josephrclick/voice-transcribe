# MODEL-UPGRADE-04: Remove Model Cost Warnings and Feedback

## Ticket ID: MODEL-UPGRADE-04

## Phase: Sprint 1 - Model Integration Enhancement

## Priority: Medium

## Dependencies: MODEL-UPGRADE-03 (GPT-5 Model Integration)

## Summary

Remove all cost-related warnings, modals, and feedback when users select different models for Prompt Mode. Simplify the model selection experience to be seamless and immediate without interrupting the user flow with cost considerations.

## Current Behavior

- When switching between models, users see warning dialogs about potential costs
- Cost warnings appear for premium models (GPT-4.1, GPT-5)
- Modal dialogs interrupt the workflow when selecting higher-tier models
- Cost feedback is prominent in the UI

## Desired Behavior

- Model selection should be instant and seamless
- No cost warnings or confirmation dialogs
- Silent tracking of usage for dashboard purposes only
- Focus on model capabilities rather than costs

## Acceptance Criteria

- [ ] All cost warning dialogs removed from model selection flow
- [ ] Model switching happens immediately without confirmation
- [ ] Cost tracking continues silently in background for dashboard
- [ ] Model tier badges remain but without cost emphasis
- [ ] No regression in model selection functionality
- [ ] Dashboard still displays usage statistics (without warnings)

## Technical Requirements

### Files to Modify

1. **enhance.py**
   - Remove `_show_cost_warning_dialog()` method
   - Simplify `on_model_changed()` to switch models directly
   - Remove cost-related strings from MODEL_CONFIG
   - Keep usage tracking but remove user-facing warnings

2. **main.py** (if applicable)
   - Remove any cost-related tooltips or status messages
   - Update model dropdown to not show cost indicators

### Code Changes

```python
# enhance.py - Simplified model change handler
def on_model_changed(self, combo):
    """Handle model selection change without cost warnings."""
    model_iter = combo.get_active_iter()
    if model_iter:
        model = combo.get_model()
        selected_model = model[model_iter][0]

        # Direct model switch without warnings
        self.selected_model = selected_model
        self.config['selected_model'] = selected_model
        self.save_config()

        # Update UI to reflect new model
        self.update_model_badge()

        # Silent usage tracking for dashboard
        self._track_model_usage(selected_model)
```

```python
# Remove these methods/sections:
- _show_cost_warning_dialog()
- _calculate_estimated_cost()
- Any "cost", "pricing", "expensive" references in user-facing strings
```

### Model Configuration Updates

```python
MODEL_CONFIG = {
    "gpt-5": {
        "name": "GPT-5",
        "tier": "flagship",
        "context_window": 2000000,
        # Remove: "cost_warning": True,
        # Remove: "hourly_rate": "$$$",
    },
    # Similar for other models
}
```

## Testing Checklist

- [ ] Switch between all available models rapidly
- [ ] Verify no dialogs or warnings appear
- [ ] Confirm model selection is immediate
- [ ] Check dashboard still shows usage stats
- [ ] Test with both standard and premium models
- [ ] Verify config.json updates correctly
- [ ] Ensure no console errors during model switching

## UX Considerations

- Users want fast, uninterrupted workflow
- Cost concerns can be addressed in documentation/onboarding
- Dashboard provides usage visibility without being intrusive
- Focus shifts to model capabilities and performance

## Rollback Plan

- Git revert to previous version if issues arise
- Config compatibility maintained (no breaking changes)
- Can re-enable warnings via feature flag if needed

## Success Metrics

- Zero user interruptions during model selection
- Reduced time to switch models (<100ms)
- No increase in support tickets about unexpected costs
- Improved user satisfaction scores

## Notes

- Keep backend cost tracking for billing/analytics
- Consider adding cost info to settings/preferences instead
- Document model tiers in help documentation
- Coordinate with MODEL-UPGRADE-05 for dashboard updates
