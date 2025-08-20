# Ticket #02: Post-Processing Punctuation Pipeline

**Priority**: P2 - High Impact  
**Assignee**: @algorithm-architect  
**Sprint**: Punctuation Sprint  
**Estimated Effort**: 4 days

## Problem Statement

Even with improved API configuration, some over-punctuation may still occur. We need intelligent post-processing to detect and merge inappropriately split sentences before they reach the UI.

## Technical Details

**Integration Point**: `/home/joe/dev/projects/voice-transcribe-dev/main.py:1485+` (`_update_live_transcript`)

Current flow has no intelligence between Deepgram response and UI update:

```python
def _update_live_transcript(self, text, is_final):
    """Update the transcript view with partial and final results."""
    # Direct pass-through - no processing!
    if is_final:
        buffer.insert(end_iter, " ")
        self.confirmed_text += text + " "  # ← Accumulates fragmented sentences
```

## Solution Architecture

### 1. Sentence Fragment Detection Engine

Create intelligent detection for fragmented sentences based on:

- **Length Analysis**: Sentences < 3 words likely fragments
- **Capitalization Patterns**: Detect mid-sentence caps
- **Timing Analysis**: Track pause duration between segments
- **Grammatical Structure**: Identify incomplete clauses

### 2. Smart Merge Algorithm

Implement context-aware merging:

```python
class PunctuationProcessor:
    def __init__(self, merge_threshold_ms=800, min_sentence_length=3):
        self.merge_threshold_ms = merge_threshold_ms
        self.min_sentence_length = min_sentence_length
        self.pending_fragments = []
        self.last_final_time = None

    def process_transcript(self, text: str, is_final: bool, timestamp: float) -> str:
        """Process transcript with intelligent punctuation handling."""

        if not is_final:
            return text  # Pass through interim results

        # Analyze for potential fragment
        fragment_score = self._calculate_fragment_score(text, timestamp)

        if fragment_score > 0.7:  # Likely fragment
            self.pending_fragments.append((text, timestamp))
            return self._try_merge_fragments()
        else:
            # Standalone sentence - flush any pending fragments
            result = self._flush_pending_fragments() + text
            self.pending_fragments.clear()
            return result

    def _calculate_fragment_score(self, text: str, timestamp: float) -> float:
        """Calculate probability that text is a sentence fragment."""
        score = 0.0

        # Length analysis (0-30 points)
        word_count = len(text.split())
        if word_count < 3:
            score += 0.3
        elif word_count < 6:
            score += 0.1

        # Timing analysis (0-40 points)
        if self.last_final_time and timestamp - self.last_final_time < self.merge_threshold_ms:
            score += 0.4

        # Capitalization analysis (0-20 points)
        if text and not text[0].isupper():
            score += 0.2

        # Grammar analysis (0-10 points)
        if self._lacks_main_clause(text):
            score += 0.1

        return min(score, 1.0)
```

### 3. Integration with Transcript Flow

Modify the transcript handling pipeline:

```python
class VoiceTranscribeApp:
    def __init__(self):
        # ... existing init ...
        self.punctuation_processor = PunctuationProcessor(
            merge_threshold_ms=800,  # Configurable
            min_sentence_length=3
        )

    def _update_live_transcript(self, text, is_final):
        """Enhanced transcript update with punctuation processing."""

        # Process through punctuation pipeline
        processed_text = self.punctuation_processor.process_transcript(
            text, is_final, time.time() * 1000
        )

        if not processed_text:
            return False  # Fragment held for merging

        # Continue with existing UI update logic
        buffer = self.original_text_view.get_buffer()
        # ... rest of existing method unchanged ...
```

## Implementation Tasks

### Phase 1: Core Algorithm Development (2 days)

- [ ] Create `PunctuationProcessor` class
- [ ] Implement fragment detection scoring system
- [ ] Build smart merge algorithm with timing consideration
- [ ] Add configuration parameters for tuning

### Phase 2: Integration & Testing (1.5 days)

- [ ] Integrate processor into `_update_live_transcript`
- [ ] Add configuration options to `config.json`
- [ ] Create comprehensive test suite with edge cases
- [ ] Performance optimization for real-time processing

### Phase 3: Advanced Features (0.5 days)

- [ ] Add user-configurable sensitivity settings
- [ ] Implement learning from user corrections
- [ ] Add debug logging for troubleshooting

## Acceptance Criteria

1. **Fragment Detection**: Accurately identify sentence fragments (>85% accuracy)
2. **Smart Merging**: Merge appropriate fragments without losing intentional sentence breaks
3. **Performance**: Process transcripts in <10ms (real-time requirement)
4. **Configurability**: Users can adjust merge sensitivity
5. **Robustness**: Handle edge cases (empty strings, special characters, long pauses)

## Testing Strategy

### Unit Tests

```python
def test_fragment_detection():
    processor = PunctuationProcessor()

    # Test obvious fragments
    assert processor._calculate_fragment_score("and then", 1000) > 0.7
    assert processor._calculate_fragment_score("but wait", 500) > 0.7

    # Test complete sentences
    assert processor._calculate_fragment_score("This is a complete sentence.", 1000) < 0.3

def test_merge_timing():
    processor = PunctuationProcessor(merge_threshold_ms=800)

    # Test rapid succession (should merge)
    result1 = processor.process_transcript("Hello world", True, 1000)
    result2 = processor.process_transcript("and goodbye", True, 1500)

    # Test long pause (should not merge)
    result3 = processor.process_transcript("New sentence", True, 3000)
```

### Integration Tests

```python
def test_transcript_flow_integration():
    """Test full integration with transcript update flow"""
    app = VoiceTranscribeApp()

    # Simulate fragmented input
    app._update_live_transcript("Hello", True)
    app._update_live_transcript("world", True)

    # Verify merged output in UI
    buffer_text = app.original_text_view.get_buffer().get_text()
    assert "Hello world" in buffer_text
```

### Manual Test Scenarios

1. **Rapid Fire**: "Hello. World. Today. Is. Great." → Should merge appropriately
2. **Mixed Content**: "Good morning everyone [pause] Let's begin the meeting [pause] First item" → Should handle varied timing
3. **Edge Cases**: Empty strings, special characters, numbers, URLs

## Configuration Schema

Add to `config.json`:

```json
{
  "punctuation_processing": {
    "enabled": true,
    "merge_threshold_ms": 800,
    "min_sentence_length": 3,
    "fragment_sensitivity": "balanced", // "strict", "balanced", "lenient"
    "learning_enabled": false // Future enhancement
  }
}
```

## Dependencies

- **Requires**: Ticket #01 (API Configuration) - Need timing data from VAD events
- **Blocks**: Ticket #03 (User Controls) - Provides backend for UI settings
- **Integration**: Enhancement module (may need to handle fragmented input better)

## Performance Considerations

1. **Memory Usage**: Keep fragment buffer size limited (max 5 pending fragments)
2. **Processing Speed**: Target <10ms processing time per transcript segment
3. **Thread Safety**: Ensure processor is thread-safe for GTK integration

## Risks & Mitigations

1. **Risk**: Over-aggressive merging loses intentional sentence breaks
   - **Mitigation**: Conservative default settings, extensive testing

2. **Risk**: Processing delay affects real-time feel
   - **Mitigation**: Optimize algorithm, async processing if needed

3. **Risk**: Complex edge cases break the algorithm
   - **Mitigation**: Comprehensive test coverage, fallback to pass-through

## Definition of Done

- [ ] PunctuationProcessor class implemented and tested
- [ ] Integration with transcript flow working seamlessly
- [ ] Unit test coverage > 95% for processor logic
- [ ] Manual testing shows significant reduction in fragmented sentences
- [ ] Performance benchmarks meet <10ms requirement
- [ ] Configuration system integrated
- [ ] Documentation updated with algorithm details
- [ ] Code review completed
