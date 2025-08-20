# Ticket #05: Comprehensive Testing & Quality Assurance

**Priority**: P1 - Critical Quality Gate  
**Assignee**: @test-engineer  
**Sprint**: Punctuation Sprint  
**Estimated Effort**: 3 days

## Problem Statement

The punctuation sprint involves complex changes to core transcription, processing, and enhancement logic. Comprehensive testing is essential to ensure:

1. Reduced over-punctuation without losing legitimate sentence breaks
2. Real-time performance meets user expectations
3. All punctuation sensitivity levels work correctly
4. No regressions in existing functionality
5. Edge cases are handled gracefully

## Testing Strategy Overview

### 1. Multi-Layer Testing Approach

- **Unit Tests**: Individual component functionality
- **Integration Tests**: Component interaction verification
- **Performance Tests**: Real-time processing benchmarks
- **User Acceptance Tests**: End-to-end scenarios with real speech patterns
- **Regression Tests**: Ensure existing features unchanged

### 2. Test Data Categories

- **Controlled Fragments**: Artificially created over-punctuated samples
- **Real User Data**: Anonymized transcripts from actual usage
- **Edge Cases**: Empty inputs, special characters, very long/short segments
- **Performance Data**: High-frequency input streams

## Detailed Testing Plan

### Phase 1: Unit Testing (1 day)

#### A. DeepgramService Configuration Testing

**Target**: Ticket #01 implementation

```python
class TestDeepgramConfiguration:
    """Test Deepgram API configuration changes"""

    def test_punctuation_levels(self):
        """Test all punctuation sensitivity levels"""
        test_cases = [
            ("off", {"punctuate": False, "smart_format": False}),
            ("minimal", {"punctuate": True, "smart_format": False}),
            ("balanced", {"punctuate": True, "smart_format": True}),
            ("aggressive", {"punctuate": True, "smart_format": True, "diarize": True})
        ]

        for level, expected_config in test_cases:
            service = DeepgramService(mock_client, mock_callback, punctuation_level=level)
            options = service._get_live_options()

            assert options.punctuate == expected_config["punctuate"]
            assert options.smart_format == expected_config["smart_format"]

    def test_endpointing_configuration(self):
        """Test endpointing parameter handling"""
        # Test default value
        service = DeepgramService(mock_client, mock_callback)
        options = service._get_live_options()
        assert options.endpointing == 400  # Default 400ms

        # Test custom values
        for endpointing_ms in [200, 500, 800, 1000]:
            service = DeepgramService(mock_client, mock_callback, endpointing_ms=endpointing_ms)
            options = service._get_live_options()
            assert options.endpointing == endpointing_ms

    def test_vad_events_enabled(self):
        """Test Voice Activity Detection integration"""
        service = DeepgramService(mock_client, mock_callback)
        options = service._get_live_options()

        assert options.vad_events == True
        assert options.interim_results == True
        assert options.utterance_end_ms == 1000
```

#### B. Punctuation Processor Testing

**Target**: Ticket #02 implementation

```python
class TestPunctuationProcessor:
    """Test punctuation processing algorithms"""

    def test_fragment_detection_accuracy(self):
        """Test fragment scoring accuracy"""
        processor = PunctuationProcessor()

        # Obvious fragments (should score > 0.7)
        fragments = [
            "and then",
            "but wait",
            "so I",
            "world",  # single word
        ]

        for fragment in fragments:
            score = processor._calculate_fragment_score(fragment, 1000)
            assert score > 0.7, f"'{fragment}' should be detected as fragment"

        # Complete sentences (should score < 0.3)
        sentences = [
            "This is a complete sentence.",
            "Hello everyone, how are you today?",
            "Let's begin the meeting now.",
        ]

        for sentence in sentences:
            score = processor._calculate_fragment_score(sentence, 1000)
            assert score < 0.3, f"'{sentence}' should not be fragment"

    def test_timing_based_merging(self):
        """Test time-based fragment merging"""
        processor = PunctuationProcessor(merge_threshold_ms=800)

        # Rapid succession - should merge
        result1 = processor.process_transcript("Hello", True, 1000)
        result2 = processor.process_transcript("world", True, 1500)  # 500ms gap

        # First fragment should be held
        assert result1 is None or result1 == ""
        # Second should trigger merge
        assert "Hello world" in result2

        # Long pause - should not merge
        processor = PunctuationProcessor(merge_threshold_ms=800)
        result1 = processor.process_transcript("First sentence", True, 1000)
        result2 = processor.process_transcript("Second sentence", True, 3000)  # 2000ms gap

        assert result1 == "First sentence"
        assert result2 == "Second sentence"
```

#### C. Enhancement Module Testing

**Target**: Ticket #04 implementation

```python
class TestEnhancementFragmentProcessing:
    """Test enhancement with fragment processing"""

    def test_fragment_reconstruction(self):
        """Test fragment reconstruction before enhancement"""
        processor = FragmentProcessor()

        test_cases = [
            ("Hello. World. Today.", "Hello world today."),
            ("So I need. A function. That works.", "So I need a function that works."),
            ("Complete sentence. But this. Is broken.", "Complete sentence. But this is broken."),
        ]

        for input_text, expected in test_cases:
            result = processor.reconstruct_fragments(input_text)
            assert result == expected, f"Expected '{expected}', got '{result}'"

    @mock.patch('enhance.openai.OpenAI')
    def test_enhancement_with_fragments(self, mock_openai):
        """Test full enhancement pipeline with fragmented input"""
        # Mock OpenAI response
        mock_response = mock.MagicMock()
        mock_response.choices[0].message.content = "Create a Python function that reads CSV files."
        mock_openai.return_value.chat.completions.create.return_value = mock_response

        fragmented_input = "So I need. A Python function. That reads. CSV files."
        enhanced, error = enhance_prompt(fragmented_input, "balanced")

        assert error is None
        assert enhanced is not None
        assert "Python function" in enhanced
        assert "CSV" in enhanced
```

### Phase 2: Integration Testing (1 day)

#### A. End-to-End Transcript Flow

```python
class TestTranscriptIntegration:
    """Test complete transcript processing pipeline"""

    def test_fragmented_input_processing(self):
        """Test full pipeline from Deepgram to UI with fragmented input"""
        app = VoiceTranscribeApp()

        # Simulate fragmented Deepgram responses
        fragmented_inputs = [
            ("Hello", True, 1000),
            ("world", True, 1200),
            ("today", True, 1400),
            ("is", True, 1600),
            ("great", True, 1800),
        ]

        for text, is_final, timestamp in fragmented_inputs:
            app._update_live_transcript(text, is_final)

        # Check final UI state
        buffer = app.original_text_view.get_buffer()
        final_text = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)

        # Should be merged intelligently
        assert "Hello world today is great" in final_text
        # Should not have excessive periods
        assert final_text.count('.') <= 1

    def test_configuration_updates_during_recording(self):
        """Test changing punctuation settings during active recording"""
        app = VoiceTranscribeApp()

        # Start recording with default settings
        app._start_recording()
        assert app.deepgram_service.is_connected()

        # Change punctuation sensitivity
        app.punctuation_controls.sensitivity_scale.set_value(1)  # Minimal
        app._on_punctuation_setting_changed(None, 1)

        # Should gracefully restart service
        assert app.deepgram_service.is_connected()

        # Verify new settings applied
        options = app.deepgram_service._get_live_options()
        assert options.punctuate == True
        assert options.smart_format == False  # Minimal level
```

#### B. Performance Integration Tests

```python
class TestPerformanceIntegration:
    """Test real-time performance requirements"""

    def test_processing_latency(self):
        """Ensure processing meets real-time requirements"""
        processor = PunctuationProcessor()

        # Test with varying fragment loads
        test_inputs = [
            "Short fragment",
            "This. Is. A. Heavily. Fragmented. Input. That. Should. Still. Process. Quickly.",
            "Mixed input with some complete sentences. And some. Fragmented. Parts. Here and there.",
        ]

        for input_text in test_inputs:
            start_time = time.time()
            result = processor.process_transcript(input_text, True, start_time * 1000)
            processing_time = (time.time() - start_time) * 1000  # Convert to ms

            assert processing_time < 10, f"Processing took {processing_time}ms (limit: 10ms)"

    def test_high_frequency_input_handling(self):
        """Test handling rapid transcript updates"""
        app = VoiceTranscribeApp()

        # Simulate rapid-fire updates (typical in fast speech)
        rapid_inputs = [(f"word{i}", True, i * 100) for i in range(20)]

        start_time = time.time()
        for text, is_final, timestamp in rapid_inputs:
            app._update_live_transcript(text, is_final)
        total_time = time.time() - start_time

        # Should handle 20 updates in under 200ms
        assert total_time < 0.2, f"Rapid processing took {total_time}s"
```

### Phase 3: User Acceptance Testing (1 day)

#### A. Real Speech Pattern Testing

Create comprehensive test scenarios based on real-world usage:

```python
class TestRealWorldScenarios:
    """Test with realistic speech patterns and use cases"""

    def test_meeting_transcription_scenario(self):
        """Test typical meeting transcription with natural pauses"""
        meeting_transcript = """
        Good morning everyone. Let's start today's meeting.
        First item on the agenda. Is the budget review.
        Sarah can you. Please share your screen.
        And show us. The quarterly numbers.
        """

        # Process through pipeline
        processor = PunctuationProcessor()
        enhanced_transcript = processor.process_meeting_transcript(meeting_transcript)

        # Should merge appropriate fragments
        expected_phrases = [
            "Good morning everyone",
            "Let's start today's meeting",
            "First item on the agenda is the budget review",
            "Sarah can you please share your screen",
            "And show us the quarterly numbers"
        ]

        for phrase in expected_phrases:
            assert phrase.lower() in enhanced_transcript.lower()

    def test_coding_dictation_scenario(self):
        """Test technical dictation with code-related terms"""
        coding_transcript = """
        Create a function. Called process data.
        That takes. A pandas dataframe.
        And returns. The cleaned dataset.
        """

        # Should handle technical terms appropriately
        processed = process_technical_transcript(coding_transcript)

        assert "process_data" in processed or "process data" in processed
        assert "pandas DataFrame" in processed or "pandas dataframe" in processed
        assert "cleaned dataset" in processed
```

#### B. Edge Case Testing

```python
class TestEdgeCases:
    """Test edge cases and error conditions"""

    def test_empty_and_invalid_inputs(self):
        """Test handling of empty or invalid inputs"""
        processor = PunctuationProcessor()

        edge_cases = [
            "",  # Empty string
            "   ",  # Whitespace only
            ".",  # Single punctuation
            "Hello.",  # Single word with period
            "A. B. C. D. E.",  # Single letters
            "123. 456. 789.",  # Numbers only
        ]

        for input_text in edge_cases:
            # Should not crash
            result = processor.process_transcript(input_text, True, 1000)
            assert isinstance(result, (str, type(None)))

    def test_special_characters_and_formatting(self):
        """Test handling of special characters, URLs, emails"""
        special_inputs = [
            "Send email to user@example.com. Please include. The report.",
            "Visit https://example.com. For more. Information.",
            "The price is $29.99. But we can. Discuss discounts.",
        ]

        for input_text in special_inputs:
            result = process_transcript_with_specials(input_text)
            # Should preserve special formatting
            if "@" in input_text:
                assert "@" in result
            if "https://" in input_text:
                assert "https://" in result or "http" in result
            if "$" in input_text:
                assert "$" in result
```

## Test Data Management

### 1. Synthetic Test Data Generation

```python
def generate_fragmented_samples(base_sentences: List[str], fragment_levels: List[str]) -> Dict:
    """Generate test data with various fragmentation patterns"""

    samples = {}

    for level in fragment_levels:
        samples[level] = []

        for sentence in base_sentences:
            if level == "heavy":
                # Fragment every 1-2 words
                fragmented = fragment_aggressively(sentence)
            elif level == "moderate":
                # Fragment at natural break points
                fragmented = fragment_moderately(sentence)
            elif level == "light":
                # Minimal fragmentation
                fragmented = fragment_lightly(sentence)

            samples[level].append({
                "original": sentence,
                "fragmented": fragmented,
                "expected_merge": sentence
            })

    return samples
```

### 2. Performance Benchmarking

```python
class PerformanceBenchmarks:
    """Define performance benchmarks for the punctuation sprint"""

    BENCHMARKS = {
        "fragment_detection": 5,  # ms per transcript
        "merge_processing": 10,   # ms per merge operation
        "ui_update_latency": 16,  # ms (60fps requirement)
        "configuration_change": 100,  # ms for settings update
        "service_restart": 2000,  # ms for graceful restart
    }

    def run_all_benchmarks(self):
        """Run comprehensive performance testing"""
        results = {}

        for benchmark_name, max_time in self.BENCHMARKS.items():
            result = self._run_benchmark(benchmark_name)
            results[benchmark_name] = {
                "actual_time": result,
                "max_allowed": max_time,
                "passed": result <= max_time
            }

        return results
```

## Acceptance Criteria

### 1. Functional Requirements

- [ ] All punctuation sensitivity levels work as designed
- [ ] Fragment detection accuracy > 85% on test dataset
- [ ] Smart merging preserves user intent in > 95% of cases
- [ ] Configuration changes apply without data loss
- [ ] Enhancement quality improved for fragmented inputs

### 2. Performance Requirements

- [ ] Real-time processing < 10ms per transcript segment
- [ ] UI remains responsive during heavy processing
- [ ] Memory usage increase < 20% compared to baseline
- [ ] Service restart time < 2 seconds

### 3. Quality Requirements

- [ ] Zero critical bugs in core transcription flow
- [ ] No regressions in existing functionality
- [ ] Unit test coverage > 95% for new code
- [ ] Integration test coverage for all major workflows

## Test Environment Setup

### 1. Automated Test Infrastructure

```bash
# Setup test environment
python -m pytest tests/punctuation_sprint/ -v --cov=. --cov-report=html

# Performance testing
python -m pytest tests/performance/ --benchmark-only

# Integration testing with real API
DEEPGRAM_TEST_API_KEY=xxx python -m pytest tests/integration/
```

### 2. Manual Testing Checklist

- [ ] Install fresh on clean system
- [ ] Test with various microphone types
- [ ] Test in different noise environments
- [ ] Test with different speaking speeds
- [ ] Test configuration migration from v3.3
- [ ] Test all accessibility features still work

## Risk Mitigation

### 1. Rollback Plan

- Maintain feature flags for all new functionality
- Document rollback procedure for each component
- Create automated rollback scripts

### 2. Monitoring & Observability

- Add comprehensive logging for new processing steps
- Create dashboards for performance metrics
- Implement user feedback collection for quality assessment

## Definition of Done

- [ ] All unit tests pass with > 95% coverage
- [ ] All integration tests pass
- [ ] Performance benchmarks meet requirements
- [ ] Manual testing scenarios completed successfully
- [ ] Edge cases handled gracefully
- [ ] No regressions in existing functionality
- [ ] Documentation updated with testing procedures
- [ ] Test automation integrated into CI/CD pipeline
- [ ] Rollback procedures tested and documented
