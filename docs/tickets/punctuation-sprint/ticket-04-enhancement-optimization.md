# Ticket #04: Enhancement Module Optimization for Fragmented Input

**Priority**: P4 - Enhancement Quality  
**Assignee**: @nlp-specialist  
**Sprint**: Punctuation Sprint  
**Estimated Effort**: 2 days

## Problem Statement

The OpenAI enhancement module in `enhance.py` may receive fragmented sentence inputs due to over-punctuation issues. Current prompts don't account for this scenario, potentially producing suboptimal enhancements when working with broken sentence fragments.

## Technical Details

**Integration Point**: `/home/joe/dev/projects/voice-transcribe-dev/enhance.py:31-50` (Enhancement prompts)

**Current Enhancement Flow**:

```python
# enhance.py:56 - enhance_prompt function receives fragmented input
def enhance_prompt(transcript: str, style: str = "balanced"):
    # Current prompts assume clean, complete sentences
    # May struggle with: "Hello. World. Today. Is. Great."
    # Should produce: "Hello world, today is great!"
```

**Problem Scenarios**:

1. **Over-segmented input**: "Good morning. Everyone. Let's start. The meeting."
2. **Fragment chains**: "So I need. A Python function. That reads. CSV files."
3. **Mixed quality**: "This is a complete sentence. But this. Is fragmented."

## Solution Architecture

### 1. Enhanced Pre-processing

Add intelligent fragment detection and reconstruction before enhancement:

```python
class FragmentProcessor:
    """Pre-process fragmented transcripts before OpenAI enhancement"""

    def __init__(self):
        self.fragment_patterns = [
            r'\.\s+[a-z]',  # Period followed by lowercase (likely fragment)
            r'\.\s+\w{1,3}\s+\.',  # Very short segments
            r'\.\s+(And|But|Or|So)\s+',  # Conjunctions starting new "sentences"
        ]

    def reconstruct_fragments(self, transcript: str) -> str:
        """Intelligently merge sentence fragments before enhancement"""

        # Split into segments
        segments = re.split(r'\.(\s+)', transcript)

        reconstructed = []
        current_sentence = ""

        for segment in segments:
            if self._is_likely_fragment(segment):
                # Merge with current sentence
                if current_sentence:
                    current_sentence += " " + segment.lower()
                else:
                    current_sentence = segment
            else:
                # Complete previous sentence and start new one
                if current_sentence:
                    reconstructed.append(current_sentence.strip() + ".")
                current_sentence = segment.strip()

        # Don't forget the last sentence
        if current_sentence:
            reconstructed.append(current_sentence.strip() + ".")

        return " ".join(reconstructed)

    def _is_likely_fragment(self, segment: str) -> bool:
        """Determine if a segment is likely a sentence fragment"""
        segment = segment.strip()

        # Very short segments are likely fragments
        if len(segment.split()) < 3:
            return True

        # Starts with lowercase (continuation)
        if segment and segment[0].islower():
            return True

        # Starts with conjunction
        if re.match(r'^(and|but|or|so|then|now)\s', segment.lower()):
            return True

        return False
```

### 2. Fragment-Aware Enhancement Prompts

Update system prompts to handle fragmented input explicitly:

```python
ENHANCED_PROMPTS = {
    "concise": """You are a prompt optimization expert. The following voice transcript may contain over-punctuated sentence fragments due to transcription errors.

First, intelligently merge any fragments that should be part of the same sentence. Then rewrite as a clear, concise prompt for an AI assistant.

Remove filler words, fix grammar, merge fragments naturally, and structure it for maximum clarity while preserving the user's intent. Keep it brief but complete.

Example input: "So I need. A Python function. That reads. CSV files."
Example output: "Create a Python function that reads CSV files."
""",

    "balanced": """You are a prompt optimization expert. This voice transcript may contain fragmented sentences due to transcription punctuation errors.

Your task:
1. Identify and merge sentence fragments that belong together
2. Fix grammar and remove filler words
3. Add helpful context and structure
4. Clarify ambiguous requests
5. Preserve the user's intent and tone

Make it clear and effective without being overly verbose. Focus on creating a cohesive, well-structured prompt from potentially fragmented input.

Example: "Good morning. Everyone. Let's discuss. The project timeline." → "Good morning everyone, let's discuss the project timeline."
""",

    "detailed": """You are a prompt optimization expert. The input transcript likely contains over-punctuated sentence fragments due to voice transcription errors.

Process this transcript by:
1. Intelligently merging sentence fragments into coherent thoughts
2. Fixing all grammar and transcription errors
3. Adding relevant context and background
4. Breaking down complex requests into clear steps
5. Suggesting additional details that might be helpful
6. Structuring for maximum AI comprehension

Be thorough but maintain focus on the user's goal. Transform fragmented input into a comprehensive, well-structured prompt.

Note: Input may look like "So I want. To create. A machine learning. Model that. Predicts customer. Behavior." - merge these fragments into natural, flowing sentences.
"""
}
```

### 3. Enhanced Token Estimation

Update token estimation to account for fragment processing:

```python
def estimate_tokens_with_fragments(text: str) -> int:
    """Enhanced token estimation accounting for fragment processing overhead"""
    base_tokens = len(text) // 4

    # Add overhead for fragment processing
    fragment_count = text.count('. ') + text.count('? ') + text.count('! ')
    if fragment_count > 10:  # High fragmentation
        overhead = base_tokens * 0.2  # 20% overhead for processing
    elif fragment_count > 5:
        overhead = base_tokens * 0.1  # 10% overhead
    else:
        overhead = 0

    return int(base_tokens + overhead)
```

## Implementation Tasks

### Phase 1: Fragment Detection & Pre-processing (1 day)

- [ ] Create `FragmentProcessor` class with reconstruction logic
- [ ] Implement pattern-based fragment detection
- [ ] Add intelligent merging algorithms
- [ ] Create unit tests for fragment scenarios

### Phase 2: Enhanced Prompts & Integration (0.5 days)

- [ ] Update all enhancement style prompts with fragment awareness
- [ ] Integrate `FragmentProcessor` into `enhance_prompt` function
- [ ] Update token estimation for fragment overhead
- [ ] Test with sample fragmented inputs

### Phase 3: Quality Assurance & Tuning (0.5 days)

- [ ] Create comprehensive test scenarios with real fragmented data
- [ ] Fine-tune fragment detection patterns
- [ ] Optimize processing performance
- [ ] Add logging for fragment processing analytics

## Integration with Main Enhancement Flow

```python
def enhance_prompt(transcript: str, style: str = "balanced", model_key: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    """Enhanced version with fragment processing"""

    # Quick validation
    if not transcript or not transcript.strip():
        return None, "Empty transcript"

    # NEW: Pre-process fragments
    fragment_processor = FragmentProcessor()
    processed_transcript = fragment_processor.reconstruct_fragments(transcript)

    # Log fragment processing for analytics
    if processed_transcript != transcript:
        logger.info(f"Fragment processing applied: {len(transcript.split('.'))} → {len(processed_transcript.split('.'))} segments")

    # Use processed transcript for enhancement
    if style not in ENHANCED_PROMPTS:
        style = "balanced"

    # Enhanced token estimation
    if estimate_tokens_with_fragments(processed_transcript) > 3000:
        return None, "Transcript too long for enhancement"

    # Continue with existing enhancement logic...
    messages = [
        {"role": "system", "content": ENHANCED_PROMPTS[style]},
        {"role": "user", "content": processed_transcript}  # Use processed version
    ]

    # ... rest of existing function unchanged ...
```

## Testing Strategy

### Unit Tests for Fragment Processing

```python
def test_fragment_reconstruction():
    processor = FragmentProcessor()

    # Test basic fragment merging
    fragmented = "Hello. World. Today. Is. Great."
    result = processor.reconstruct_fragments(fragmented)
    assert result == "Hello world today is great."

    # Test mixed content
    mixed = "This is complete. But this. Is fragmented. Another complete sentence."
    result = processor.reconstruct_fragments(mixed)
    expected = "This is complete. But this is fragmented. Another complete sentence."
    assert result == expected

def test_fragment_detection():
    processor = FragmentProcessor()

    # Short fragments
    assert processor._is_likely_fragment("World") == True
    assert processor._is_likely_fragment("and then") == True

    # Complete thoughts
    assert processor._is_likely_fragment("This is a complete sentence") == False
```

### Integration Tests with Real Data

```python
def test_enhancement_with_fragments():
    """Test full enhancement pipeline with fragmented input"""

    fragmented_input = "So I need. A Python function. That reads. CSV files. And removes. Duplicate rows."
    enhanced, error = enhance_prompt(fragmented_input, "balanced")

    assert error is None
    assert "python function" in enhanced.lower()
    assert "csv" in enhanced.lower()
    assert "duplicate" in enhanced.lower()
    # Should be more coherent than original
    assert enhanced.count('.') < fragmented_input.count('.')
```

### Manual Test Scenarios

1. **Heavy Fragmentation**: "Good. Morning. Everyone. Let's. Start. The. Meeting."
2. **Partial Fragmentation**: "Good morning everyone. Let's start. The meeting today."
3. **No Fragmentation**: "Good morning everyone, let's start the meeting today."
4. **Mixed Quality**: "Complete sentence here. But this. Is very. Fragmented input."

## Performance Considerations

1. **Processing Overhead**: Fragment processing adds ~5-10ms per transcript
2. **Memory Usage**: Minimal additional memory for pattern matching
3. **Token Efficiency**: Better enhancement quality may justify slightly higher token usage

## Configuration Options

Add to config schema:

```json
{
  "enhancement_settings": {
    "fragment_processing_enabled": true,
    "fragment_sensitivity": "balanced", // "strict", "balanced", "lenient"
    "merge_threshold": 3, // minimum words to avoid merging
    "debug_fragment_processing": false // log fragment operations
  }
}
```

## Dependencies

- **Integrates with**: Ticket #02 (Post-processing) - May receive less fragmented input if post-processing works well
- **Complements**: Ticket #01 (API Configuration) - Provides fallback quality improvement
- **No Blockers**: Can be implemented independently

## Expected Outcomes

1. **Quality Improvement**: Enhanced prompts should be more coherent from fragmented input
2. **User Experience**: Users get better enhancement results even with over-punctuated transcripts
3. **Robustness**: Enhancement module handles edge cases more gracefully
4. **Analytics**: Better insight into fragment patterns for future improvements

## Definition of Done

- [ ] FragmentProcessor class implemented with robust reconstruction logic
- [ ] All enhancement prompts updated with fragment awareness
- [ ] Integration with enhance_prompt function working seamlessly
- [ ] Unit test coverage > 95% for fragment processing logic
- [ ] Integration tests confirm improved enhancement quality
- [ ] Performance benchmarks meet acceptable overhead limits
- [ ] Configuration options implemented and tested
- [ ] Documentation updated with fragment processing details
- [ ] Code review completed and approved
