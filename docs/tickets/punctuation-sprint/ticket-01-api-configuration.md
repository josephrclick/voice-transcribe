# Ticket #01: Deepgram API Configuration Overhaul

**Priority**: P1 - Critical Fix  
**Assignee**: @api-integration-specialist  
**Sprint**: Punctuation Sprint  
**Estimated Effort**: 3 days

## Problem Statement

Current hardcoded Deepgram API configuration causes over-aggressive sentence segmentation:

- `punctuate=True` and `smart_format=True` are hardcoded
- Default 10ms endpointing threshold too sensitive
- No Voice Activity Detection (VAD) configuration
- Missing configurable utterance detection parameters

## Technical Details

**Root Cause Location**: `/home/joe/dev/projects/voice-transcribe-dev/deepgram_service.py:52-60`

```python
# Current problematic configuration
options = LiveOptions(
    model="nova-3",
    language="en-US",
    punctuate=True,        # ← Hardcoded: causes over-punctuation
    smart_format=True,     # ← Hardcoded: aggressive formatting
    encoding="linear16",
    sample_rate=16000,
    channels=1,
    # Missing: endpointing, utterance_end_ms, vad_events
)
```

## Solution Requirements

### 1. Make Punctuation Configurable

- Add `punctuation_sensitivity` parameter to `DeepgramService.__init__()`
- Support levels: "off", "minimal", "balanced", "aggressive"
- Map to appropriate Deepgram parameters

### 2. Implement Advanced Endpointing

- Add `endpointing` parameter (default: 300-500ms instead of 10ms)
- Add `utterance_end_ms` for gap detection
- Enable `vad_events=True` for Voice Activity Detection
- Add `interim_results=True` for real-time processing

### 3. Update LiveOptions Configuration

```python
def _get_live_options(self, punctuation_level="balanced", endpointing_ms=400):
    """Generate Deepgram LiveOptions based on user preferences."""

    # Punctuation mapping
    punctuation_config = {
        "off": {"punctuate": False, "smart_format": False},
        "minimal": {"punctuate": True, "smart_format": False},
        "balanced": {"punctuate": True, "smart_format": True},
        "aggressive": {"punctuate": True, "smart_format": True, "diarize": True}
    }

    config = punctuation_config.get(punctuation_level, punctuation_config["balanced"])

    return LiveOptions(
        model="nova-3",
        language="en-US",
        endpointing=endpointing_ms,  # Key fix: increase from 10ms default
        utterance_end_ms=1000,       # Detect longer pauses
        vad_events=True,             # Enable VAD
        interim_results=True,        # Required for utterance detection
        **config,                    # Apply punctuation settings
        encoding="linear16",
        sample_rate=16000,
        channels=1,
    )
```

## Implementation Tasks

### Phase 1: API Parameter Updates (1 day)

- [ ] Add configurable parameters to `DeepgramService.__init__()`
- [ ] Implement `_get_live_options()` method
- [ ] Update `_connect()` to use new configuration
- [ ] Test basic connectivity with new parameters

### Phase 2: Configuration Integration (1 day)

- [ ] Add punctuation settings to `config.json` schema
- [ ] Create migration for existing config files
- [ ] Add validation for parameter ranges
- [ ] Implement fallback values for invalid configs

### Phase 3: Testing & Validation (1 day)

- [ ] Unit tests for new parameter combinations
- [ ] Integration tests with live Deepgram API
- [ ] Performance testing with different endpointing values
- [ ] Validate VAD event handling

## Acceptance Criteria

1. **Configurable Punctuation**: Users can select punctuation sensitivity levels
2. **Proper Endpointing**: Default endpointing increased to 300-500ms range
3. **VAD Integration**: Voice Activity Detection events properly handled
4. **Backward Compatibility**: Existing installations upgraded smoothly
5. **Performance**: No degradation in transcription latency
6. **Error Handling**: Graceful fallback for unsupported parameter combinations

## Testing Scenarios

### Manual Test Cases

1. **Short Pause Test**: Record "Hello [0.2s pause] world" → Should remain one sentence
2. **Medium Pause Test**: Record "First sentence [0.8s pause] Second sentence" → Should split appropriately
3. **Long Pause Test**: Record statement with 2+ second pause → Should definitely split
4. **Rapid Speech**: Test with no pauses → Should not over-segment

### Automated Tests

```python
def test_punctuation_levels():
    """Test all punctuation sensitivity levels"""
    for level in ["off", "minimal", "balanced", "aggressive"]:
        service = DeepgramService(client, callback, punctuation_level=level)
        options = service._get_live_options()
        assert options.punctuate == expected_punctuate[level]

def test_endpointing_configuration():
    """Test endpointing parameter range"""
    service = DeepgramService(client, callback, endpointing_ms=500)
    options = service._get_live_options()
    assert options.endpointing == 500
```

## Dependencies

- **Blocks**: All other punctuation sprint tickets
- **Testing Dependencies**: Deepgram API test credits
- **Integration Dependencies**: Config system updates (Ticket #03)

## Risks & Mitigations

1. **Risk**: Changed API parameters break existing functionality
   - **Mitigation**: Extensive testing with fallback configuration

2. **Risk**: Deepgram API rate limits during testing
   - **Mitigation**: Use test environment with dedicated API credits

3. **Risk**: VAD events overwhelm processing pipeline
   - **Mitigation**: Implement event filtering and throttling

## Definition of Done

- [ ] All punctuation sensitivity levels implemented and tested
- [ ] Endpointing configuration working with 300-500ms default
- [ ] VAD events properly integrated
- [ ] Unit test coverage > 90% for new functionality
- [ ] Manual testing confirms reduced over-punctuation
- [ ] Documentation updated for new parameters
- [ ] Code review completed and approved
