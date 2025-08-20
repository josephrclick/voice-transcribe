#!/usr/bin/env python3
"""
Unit tests for FragmentProcessor class
Tests fragment detection and reconstruction logic
"""

import sys
import os
import unittest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from enhance import FragmentProcessor


class TestFragmentProcessor(unittest.TestCase):
    """Test suite for FragmentProcessor functionality"""
    
    def setUp(self):
        """Initialize processor for each test"""
        self.processor = FragmentProcessor()
    
    def test_basic_fragment_merging(self):
        """Test basic fragment merging"""
        fragmented = "Hello. World. Today. Is. Great."
        result = self.processor.reconstruct_fragments(fragmented)
        # Should merge these short fragments
        self.assertLess(result.count('.'), fragmented.count('.'))
        self.assertIn("hello", result.lower())
        self.assertIn("world", result.lower())
    
    def test_mixed_content(self):
        """Test mixed complete sentences and fragments"""
        mixed = "This is a complete sentence. But this. Is fragmented. Another complete sentence here."
        result = self.processor.reconstruct_fragments(mixed)
        # Should preserve complete sentences while merging fragments
        self.assertIn("This is a complete sentence", result)
        self.assertNotIn(". Is fragmented.", result)
    
    def test_abbreviation_preservation(self):
        """Test that abbreviations are not merged incorrectly"""
        text = "I met Dr. Smith. He said hello."
        result = self.processor.reconstruct_fragments(text)
        # Should preserve Dr. and not merge incorrectly
        self.assertIn("Dr.", result)
        self.assertEqual(text, result)  # Should remain unchanged
    
    def test_list_preservation(self):
        """Test that list items are preserved"""
        text = "1. First item. 2. Second item. 3. Third item."
        result = self.processor.reconstruct_fragments(text)
        # Should preserve list structure
        self.assertIn("1.", result)
        self.assertIn("2.", result)
        self.assertIn("3.", result)
    
    def test_valid_single_sentences(self):
        """Test that valid single-word sentences are preserved"""
        text = "Yes. No. Okay. The meeting is tomorrow."
        result = self.processor.reconstruct_fragments(text)
        # Should preserve valid single sentences
        self.assertIn("Yes.", result)
        self.assertIn("No.", result)
        self.assertIn("Okay.", result)
    
    def test_conjunction_starting_fragments(self):
        """Test fragments starting with conjunctions"""
        fragmented = "We need to finish. And then. We can leave."
        result = self.processor.reconstruct_fragments(fragmented)
        # Should merge conjunction-starting fragments
        self.assertLess(result.count('.'), fragmented.count('.'))
    
    def test_lowercase_following_period(self):
        """Test fragments with lowercase after period"""
        fragmented = "The project. is going. well today."
        result = self.processor.reconstruct_fragments(fragmented)
        # Should merge when lowercase follows period
        self.assertNotIn(". is", result)
        self.assertNotIn(". well", result)
    
    def test_preposition_ending_fragments(self):
        """Test fragments ending with prepositions"""
        fragmented = "We went to. The store. Yesterday evening."
        result = self.processor.reconstruct_fragments(fragmented)
        # Should merge fragments ending with prepositions
        self.assertNotIn("to.", result)
        self.assertIn("went to", result.lower())
    
    def test_decimal_preservation(self):
        """Test that decimal numbers are preserved"""
        text = "The value is 3.14 and the version is 2.0.1."
        result = self.processor.reconstruct_fragments(text)
        # Should preserve decimals and version numbers
        self.assertIn("3.14", result)
        self.assertIn("2.0.1", result)
    
    def test_url_preservation(self):
        """Test that URLs are preserved"""
        text = "Visit https://example.com for more info."
        result = self.processor.reconstruct_fragments(text)
        # Should preserve URL
        self.assertIn("https://example.com", result)
    
    def test_question_exclamation_preservation(self):
        """Test that ? and ! boundaries are preserved"""
        text = "How are you? Great! Let's start."
        result = self.processor.reconstruct_fragments(text)
        # Should preserve question and exclamation marks
        self.assertIn("?", result)
        self.assertIn("!", result)
    
    def test_empty_input(self):
        """Test handling of empty input"""
        result = self.processor.reconstruct_fragments("")
        self.assertEqual(result, "")
        
        result = self.processor.reconstruct_fragments("   ")
        self.assertEqual(result, "")
    
    def test_no_fragments(self):
        """Test input with no fragments"""
        text = "This is a complete sentence with no fragments."
        result = self.processor.reconstruct_fragments(text)
        self.assertEqual(text, result)
    
    def test_complex_fragmented_input(self):
        """Test complex real-world fragmented input"""
        fragmented = "So I need. A Python function. That reads. CSV files. And removes. Duplicate rows."
        result = self.processor.reconstruct_fragments(fragmented)
        # Should significantly reduce fragment count
        self.assertLess(result.count('.'), fragmented.count('.'))
        # Should preserve key terms
        self.assertIn("python", result.lower())
        self.assertIn("csv", result.lower())
        self.assertIn("duplicate", result.lower())
    
    def test_time_preservation(self):
        """Test that times are preserved"""
        text = "The meeting is at 3:30 p.m. tomorrow."
        result = self.processor.reconstruct_fragments(text)
        # Should preserve time format
        self.assertIn("3:30", result)
        self.assertIn("p.m.", result)
    
    def test_month_abbreviation_preservation(self):
        """Test that month abbreviations are preserved"""
        text = "The event is on Jan. 15th."
        result = self.processor.reconstruct_fragments(text)
        # Should preserve month abbreviation
        self.assertIn("Jan.", result)
    
    def test_initials_preservation(self):
        """Test that initials in names are preserved"""
        text = "Written by J. K. Rowling."
        result = self.processor.reconstruct_fragments(text)
        # Should preserve initials
        self.assertEqual(text, result)
    
    def test_heavy_fragmentation(self):
        """Test heavily fragmented input"""
        fragmented = "Good. Morning. Everyone. Let's. Start. The. Meeting."
        result = self.processor.reconstruct_fragments(fragmented)
        # Should merge most fragments
        self.assertLessEqual(result.count('.'), 2)  # At most 2 sentences
        self.assertIn("good morning", result.lower())
    
    def test_partial_fragmentation(self):
        """Test partially fragmented input"""
        text = "Good morning everyone. Let's start. The meeting today."
        result = self.processor.reconstruct_fragments(text)
        # Should handle partial fragmentation gracefully
        self.assertIn("Good morning everyone", result)
    
    def test_is_valid_standalone_method(self):
        """Test the _is_valid_standalone method directly"""
        # Valid standalones
        self.assertTrue(self.processor._is_valid_standalone("Yes."))
        self.assertTrue(self.processor._is_valid_standalone("Dr. Smith"))
        self.assertTrue(self.processor._is_valid_standalone("1. First item"))
        self.assertTrue(self.processor._is_valid_standalone("https://example.com"))
        
        # Invalid standalones (fragments)
        self.assertFalse(self.processor._is_valid_standalone("World."))
        self.assertFalse(self.processor._is_valid_standalone("Is."))
        self.assertFalse(self.processor._is_valid_standalone(""))
    
    def test_should_merge_with_next_method(self):
        """Test the _should_merge_with_next method directly"""
        # Should merge
        self.assertTrue(self.processor._should_merge_with_next("Hello.", "world today"))
        self.assertTrue(self.processor._should_merge_with_next("We went to.", "The store"))
        self.assertTrue(self.processor._should_merge_with_next("Start.", "and then continue"))
        
        # Should not merge
        self.assertFalse(self.processor._should_merge_with_next("How are you?", "Great!"))
        self.assertFalse(self.processor._should_merge_with_next("Complete sentence.", "Another sentence."))
        self.assertFalse(self.processor._should_merge_with_next("", "Next"))


if __name__ == "__main__":
    unittest.main()