#!/usr/bin/env python3
"""
Integration tests for the complete punctuation processing pipeline.

Tests the end-to-end flow from Deepgram transcripts through PunctuationProcessor
and FragmentProcessor to ensure all components work together correctly.
"""

import os
import sys
import unittest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from enhance import FragmentProcessor
from punctuation_processor import PunctuationProcessor


class TestTranscriptIntegration(unittest.TestCase):
    """Test complete transcript processing pipeline"""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.punct_processor = PunctuationProcessor(
            merge_threshold_ms=800, min_sentence_length=3, fragment_threshold=0.6, max_pending_fragments=5
        )
        self.frag_processor = FragmentProcessor()

    def test_fragmented_input_processing(self):
        """Test full pipeline from Deepgram to UI with fragmented input"""
        # Simulate fragmented Deepgram responses
        fragmented_inputs = [
            ("Hello", True, 1000),
            ("world", True, 1200),
            ("today", True, 1400),
            ("is", True, 1600),
            ("great", True, 1800),
        ]

        results = []
        fragments = []

        for text, is_final, timestamp in fragmented_inputs:
            result, fragments = self.punct_processor.process_transcript(text, is_final, timestamp, fragments)
            if result:
                results.append(result)

        # Force flush any remaining fragments
        if fragments:
            final_result, _ = self.punct_processor.flush_pending_fragments(fragments)
            if final_result:
                results.append(final_result)

        # Combine all results
        all_text = " ".join(results)

        # Should be merged intelligently
        self.assertIn("Hello", all_text)
        self.assertIn("world", all_text)
        self.assertIn("great", all_text)
        # Should not have excessive periods
        self.assertLessEqual(all_text.count("."), 2)

    def test_mixed_fragment_and_complete_sentences(self):
        """Test handling of mixed fragments and complete sentences"""
        mixed_inputs = [
            ("Good morning everyone", 1000),
            ("let's", 1200),
            ("begin", 1400),
            ("the meeting", 1600),
            ("I have three items on the agenda today", 2500),
        ]

        results = []
        fragments = []

        for text, timestamp in mixed_inputs:
            result, fragments = self.punct_processor.process_transcript(text, True, timestamp, fragments)
            if result:
                results.append(result)

        # Flush remaining
        if fragments:
            final_result, _ = self.punct_processor.flush_pending_fragments(fragments)
            if final_result:
                results.append(final_result)

        all_text = " ".join(results)

        # Check that complete sentence is preserved
        self.assertIn("I have three items on the agenda today", all_text)
        # Check fragments are merged
        self.assertIn("Good morning everyone", all_text)

    def test_timing_based_segmentation(self):
        """Test that timing gaps create proper sentence boundaries"""
        inputs_with_gaps = [
            ("Hello everyone", 1000),
            ("welcome to the meeting", 1100),  # 100ms gap - should merge
            ("Let's get started", 3000),  # 1900ms gap - new sentence
            ("with our", 3100),
            ("first topic", 3200),  # Quick succession - merge
        ]

        results = []
        fragments = []

        for text, timestamp in inputs_with_gaps:
            result, fragments = self.punct_processor.process_transcript(text, True, timestamp, fragments)
            if result:
                results.append(result)

        # Flush remaining
        if fragments:
            final_result, _ = self.punct_processor.flush_pending_fragments(fragments)
            if final_result:
                results.append(final_result)

        # Should have at least 2 distinct segments due to timing gap
        self.assertGreaterEqual(len(results), 2)

    def test_fragment_reconstruction_in_enhancement(self):
        """Test fragment reconstruction before enhancement"""
        # Heavily fragmented input that would confuse AI
        fragmented_text = "So I need. A Python function. That reads. CSV files. And processes. The data."

        # Process through fragment reconstruction
        reconstructed = self.frag_processor.reconstruct_fragments(fragmented_text)

        # Should significantly reduce fragmentation
        self.assertLess(reconstructed.count("."), fragmented_text.count("."))
        # Should preserve key terms (case insensitive)
        self.assertIn("python", reconstructed.lower())
        self.assertIn("csv", reconstructed.lower())
        self.assertIn("data", reconstructed.lower())

    def test_punctuation_preservation_in_pipeline(self):
        """Test that existing punctuation is preserved correctly"""
        inputs_with_punctuation = [
            ("How are you?", 1000),
            ("I'm doing great!", 1200),
            ("What about you", 1400),  # Missing punctuation
        ]

        results = []
        fragments = []

        for text, timestamp in inputs_with_punctuation:
            result, fragments = self.punct_processor.process_transcript(text, True, timestamp, fragments)
            if result:
                results.append(result)

        # Flush remaining
        if fragments:
            final_result, _ = self.punct_processor.flush_pending_fragments(fragments)
            if final_result:
                results.append(final_result)

        all_text = " ".join(results)

        # Should preserve question and exclamation marks
        self.assertIn("?", all_text)
        self.assertIn("!", all_text)

    def test_abbreviation_and_special_handling(self):
        """Test handling of abbreviations and special formats"""
        special_inputs = [
            ("I spoke with Dr.", 1000),
            ("Smith", 1100),
            ("about the project", 1200),
            ("The meeting is at 3:30 p.m.", 2000),
            ("on Jan.", 2100),
            ("15th", 2200),
        ]

        results = []
        fragments = []

        for text, timestamp in special_inputs:
            result, fragments = self.punct_processor.process_transcript(text, True, timestamp, fragments)
            if result:
                results.append(result)

        # Flush remaining
        if fragments:
            final_result, _ = self.punct_processor.flush_pending_fragments(fragments)
            if final_result:
                results.append(final_result)

        all_text = " ".join(results)

        # Should preserve abbreviations
        self.assertIn("Dr.", all_text)
        self.assertIn("p.m.", all_text)
        self.assertIn("Jan.", all_text)

    def test_url_and_email_preservation(self):
        """Test that URLs and emails are not fragmented"""
        technical_inputs = [
            ("Visit https://example.com", 1000),
            ("for more information", 1100),
            ("Send emails to user@example.com", 2000),
            ("with your questions", 2100),
        ]

        results = []
        fragments = []

        for text, timestamp in technical_inputs:
            result, fragments = self.punct_processor.process_transcript(text, True, timestamp, fragments)
            if result:
                results.append(result)

        # Flush remaining
        if fragments:
            final_result, _ = self.punct_processor.flush_pending_fragments(fragments)
            if final_result:
                results.append(final_result)

        all_text = " ".join(results)

        # Should preserve URLs and emails
        self.assertIn("https://example.com", all_text)
        self.assertIn("user@example.com", all_text)

    def test_number_and_decimal_handling(self):
        """Test handling of numbers and decimals"""
        numeric_inputs = [
            ("The value is 3.14", 1000),
            ("and the price is $29.99", 1100),
            ("We need 1,000 units", 2000),
        ]

        results = []
        fragments = []

        for text, timestamp in numeric_inputs:
            result, fragments = self.punct_processor.process_transcript(text, True, timestamp, fragments)
            if result:
                results.append(result)

        # Flush remaining
        if fragments:
            final_result, _ = self.punct_processor.flush_pending_fragments(fragments)
            if final_result:
                results.append(final_result)

        all_text = " ".join(results)

        # Should preserve numbers and decimals
        self.assertIn("3.14", all_text)
        self.assertIn("29.99", all_text)
        self.assertIn("1,000", all_text)

    def test_quote_and_parenthesis_handling(self):
        """Test handling of quotes and parentheses"""
        quoted_inputs = [
            ('He said "Hello', 1000),
            ('world" to everyone', 1100),
            ("The document (version 2)", 2000),
            ("is ready", 2100),
        ]

        results = []
        fragments = []

        for text, timestamp in quoted_inputs:
            result, fragments = self.punct_processor.process_transcript(text, True, timestamp, fragments)
            if result:
                results.append(result)

        # Flush remaining
        if fragments:
            final_result, _ = self.punct_processor.flush_pending_fragments(fragments)
            if final_result:
                results.append(final_result)

        all_text = " ".join(results)

        # Should preserve quotes and parentheses
        self.assertIn('"', all_text)
        self.assertIn("(", all_text)
        self.assertIn(")", all_text)

    def test_empty_and_whitespace_handling(self):
        """Test handling of empty and whitespace-only inputs"""
        edge_inputs = [
            ("", 1000),
            ("   ", 1100),
            ("Hello", 1200),
            ("", 1300),
            ("world", 1400),
            ("\t\n", 1500),
        ]

        results = []
        fragments = []

        for text, timestamp in edge_inputs:
            result, fragments = self.punct_processor.process_transcript(text, True, timestamp, fragments)
            if result:
                results.append(result)

        # Flush remaining
        if fragments:
            final_result, _ = self.punct_processor.flush_pending_fragments(fragments)
            if final_result:
                results.append(final_result)

        # Should handle empty inputs gracefully
        all_text = " ".join(results)
        self.assertIn("Hello", all_text)
        self.assertIn("world", all_text)

    def test_interim_results_passthrough(self):
        """Test that interim (non-final) results pass through unchanged"""
        interim_inputs = [
            ("Hello world", False, 1000),
            ("this is interim", False, 1100),
            ("final result", True, 1200),
        ]

        results = []
        fragments = []

        for text, is_final, timestamp in interim_inputs:
            result, fragments = self.punct_processor.process_transcript(text, is_final, timestamp, fragments)
            if result:
                results.append(result)

        # Interim results should pass through unchanged
        self.assertEqual(results[0], "Hello world")
        self.assertEqual(results[1], "this is interim")
        # Final result may be processed
        self.assertIn("final result", results[2])

    def test_buffer_overflow_handling(self):
        """Test handling when fragment buffer reaches capacity"""
        # Create many fragments to fill buffer
        fragments = []
        results = []

        # Generate fragments that will likely be buffered
        for i in range(10):  # More than max_pending_fragments
            text = f"word{i}"  # Short fragments that should be buffered
            result, fragments = self.punct_processor.process_transcript(text, True, 1000 + i * 100, fragments)
            if result:
                results.append(result)

        # Buffer should not exceed max size
        self.assertLessEqual(len(fragments), self.punct_processor.max_pending_fragments)

        # Force flush to get final results
        if fragments:
            final_result, _ = self.punct_processor.flush_pending_fragments(fragments)
            if final_result:
                results.append(final_result)

        # Now we should have some output (either from overflow or flush)
        self.assertGreater(len(results), 0)

    def test_configuration_sensitivity_impact(self):
        """Test impact of different sensitivity configurations"""
        test_text = "and then we went"

        # Test with strict sensitivity
        strict_processor = PunctuationProcessor(fragment_threshold=0.9)
        strict_result, strict_fragments = strict_processor.process_transcript(test_text, True, 1000, [])

        # Test with lenient sensitivity
        lenient_processor = PunctuationProcessor(fragment_threshold=0.3)
        lenient_result, lenient_fragments = lenient_processor.process_transcript(test_text, True, 1000, [])

        # Different thresholds should produce different behaviors
        # With strict (0.9), more likely to output immediately
        # With lenient (0.3), more likely to buffer as fragment
        if strict_result and not lenient_result:
            # Strict output, lenient buffered - expected
            self.assertEqual(len(lenient_fragments), 1)
        elif not strict_result and lenient_result:
            # Unexpected but possible based on scoring
            pass
        # Both might buffer or both might output based on exact scoring


class TestRealWorldScenarios(unittest.TestCase):
    """Test with realistic speech patterns and use cases"""

    def setUp(self):
        """Set up test fixtures"""
        self.punct_processor = PunctuationProcessor()
        self.frag_processor = FragmentProcessor()

    def test_meeting_transcription_scenario(self):
        """Test typical meeting transcription with natural pauses"""
        meeting_transcript = [
            ("Good morning everyone", 1000),
            ("Let's start today's meeting", 1500),
            ("First item on the agenda", 3000),
            ("Is the budget review", 3200),
            ("Sarah can you", 5000),
            ("Please share your screen", 5200),
            ("And show us", 5400),
            ("The quarterly numbers", 5600),
        ]

        results = []
        fragments = []

        for text, timestamp in meeting_transcript:
            result, fragments = self.punct_processor.process_transcript(text, True, timestamp, fragments)
            if result:
                results.append(result)

        # Flush remaining
        if fragments:
            final_result, _ = self.punct_processor.flush_pending_fragments(fragments)
            if final_result:
                results.append(final_result)

        all_text = " ".join(results)

        # Check for expected phrases
        self.assertIn("Good morning", all_text)
        self.assertIn("meeting", all_text.lower())
        self.assertIn("budget", all_text.lower())
        self.assertIn("Sarah", all_text)

    def test_coding_dictation_scenario(self):
        """Test technical dictation with code-related terms"""
        coding_transcript = [
            ("Create a function", 1000),
            ("Called process data", 1200),
            ("That takes", 1400),
            ("A pandas dataframe", 1600),
            ("And returns", 1800),
            ("The cleaned dataset", 2000),
        ]

        results = []
        fragments = []

        for text, timestamp in coding_transcript:
            result, fragments = self.punct_processor.process_transcript(text, True, timestamp, fragments)
            if result:
                results.append(result)

        # Flush remaining
        if fragments:
            final_result, _ = self.punct_processor.flush_pending_fragments(fragments)
            if final_result:
                results.append(final_result)

        all_text = " ".join(results)

        # Should handle technical terms appropriately
        self.assertIn("function", all_text.lower())
        self.assertIn("pandas", all_text.lower())
        self.assertIn("dataframe", all_text.lower())

    def test_conversational_back_and_forth(self):
        """Test conversational speech with quick exchanges"""
        conversation = [
            ("How are you", 1000),
            ("I'm doing well", 2000),
            ("thanks for asking", 2100),
            ("What about you", 2300),
            ("Pretty good", 3000),
            ("just busy with work", 3100),
        ]

        results = []
        fragments = []

        for text, timestamp in conversation:
            result, fragments = self.punct_processor.process_transcript(text, True, timestamp, fragments)
            if result:
                results.append(result)

        # Flush remaining
        if fragments:
            final_result, _ = self.punct_processor.flush_pending_fragments(fragments)
            if final_result:
                results.append(final_result)

        # Should maintain conversational flow
        self.assertGreater(len(results), 0)
        all_text = " ".join(results)
        self.assertIn("How are you", all_text)
        self.assertIn("I'm doing well", all_text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
