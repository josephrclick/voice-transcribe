#!/usr/bin/env python3
"""
User acceptance tests for real-world speech scenarios.

These tests validate the punctuation processing system against realistic
speech patterns and use cases that users encounter in daily usage.
"""

import unittest
import sys
import os
from typing import List, Tuple

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from punctuation_processor import PunctuationProcessor
from enhance import FragmentProcessor
from test_data_generator import TestDataGenerator, TranscriptEvent


class TestUserAcceptanceScenarios(unittest.TestCase):
    """Test realistic user scenarios with expected behaviors"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.punct_processor = PunctuationProcessor()
        self.frag_processor = FragmentProcessor()
        self.data_generator = TestDataGenerator(seed=42)
    
    def process_transcript_stream(self, events: List[TranscriptEvent]) -> str:
        """Process a stream of transcript events and return final text"""
        results = []
        fragments = []
        
        for event in events:
            result, fragments = self.punct_processor.process_transcript(
                event.text, event.is_final, event.timestamp, fragments
            )
            if result:
                results.append(result)
        
        # Flush any remaining fragments
        if fragments:
            final_result, _ = self.punct_processor.flush_pending_fragments(fragments)
            if final_result:
                results.append(final_result)
        
        return " ".join(results)
    
    def test_business_meeting_scenario(self):
        """Test transcription of a typical business meeting"""
        meeting_events = [
            TranscriptEvent("Good morning everyone", True, 1000),
            TranscriptEvent("thank you for joining", True, 1200),
            TranscriptEvent("today's quarterly review", True, 1400),
            TranscriptEvent("Let me start by", True, 3000),
            TranscriptEvent("reviewing our key metrics", True, 3200),
            TranscriptEvent("Revenue is up", True, 5000),
            TranscriptEvent("fifteen percent", True, 5200),
            TranscriptEvent("from last quarter", True, 5400),
            TranscriptEvent("However", True, 7000),
            TranscriptEvent("we need to address", True, 7200),
            TranscriptEvent("the supply chain issues", True, 7400),
        ]
        
        result = self.process_transcript_stream(meeting_events)
        
        # Should maintain professional structure
        self.assertIn("Good morning everyone", result)
        self.assertIn("Revenue is up", result)
        # Should not have excessive fragmentation
        self.assertLess(result.count('.'), 6)
        # Key business terms preserved
        self.assertIn("quarterly review", result.lower())
        self.assertIn("supply chain", result.lower())
    
    def test_technical_support_call(self):
        """Test technical support conversation"""
        support_events = [
            TranscriptEvent("Hello", True, 1000),
            TranscriptEvent("I'm having trouble", True, 2000),
            TranscriptEvent("with my computer", True, 2200),
            TranscriptEvent("It keeps freezing", True, 2400),
            TranscriptEvent("when I open", True, 2600),
            TranscriptEvent("multiple applications", True, 2800),
            TranscriptEvent("Have you tried", True, 4000),
            TranscriptEvent("restarting it", True, 4200),
            TranscriptEvent("Yes", True, 5000),
            TranscriptEvent("several times", True, 5200),
            TranscriptEvent("but the problem", True, 5400),
            TranscriptEvent("persists", True, 5600),
        ]
        
        result = self.process_transcript_stream(support_events)
        
        # Should handle technical terms
        self.assertIn("computer", result.lower())
        self.assertIn("applications", result.lower())
        # Should preserve question structure
        self.assertIn("Have you tried", result)
        # Single word responses should be preserved
        self.assertIn("Yes", result)
    
    def test_medical_consultation(self):
        """Test medical consultation with abbreviations"""
        medical_events = [
            TranscriptEvent("The patient visited Dr.", True, 1000),
            TranscriptEvent("Smith", True, 1100),
            TranscriptEvent("on Jan.", True, 1300),
            TranscriptEvent("15th", True, 1400),
            TranscriptEvent("Blood pressure was", True, 2000),
            TranscriptEvent("120 over 80", True, 2200),
            TranscriptEvent("Temperature 98.6", True, 3000),
            TranscriptEvent("degrees", True, 3200),
            TranscriptEvent("Prescribed 500 mg", True, 4000),
            TranscriptEvent("twice daily", True, 4200),
        ]
        
        result = self.process_transcript_stream(medical_events)
        
        # Should preserve medical abbreviations
        self.assertIn("Dr.", result)
        self.assertIn("Jan.", result)
        # Should preserve numbers and measurements
        self.assertIn("120", result)
        self.assertIn("98.6", result)
        self.assertIn("500 mg", result)
    
    def test_educational_lecture(self):
        """Test educational lecture with structured content"""
        lecture_events = [
            TranscriptEvent("Today we'll discuss", True, 1000),
            TranscriptEvent("three main topics", True, 1200),
            TranscriptEvent("First", True, 3000),
            TranscriptEvent("the history of", True, 3200),
            TranscriptEvent("artificial intelligence", True, 3400),
            TranscriptEvent("Second", True, 5000),
            TranscriptEvent("current applications", True, 5200),
            TranscriptEvent("in healthcare", True, 5400),
            TranscriptEvent("and education", True, 5600),
            TranscriptEvent("Third", True, 7000),
            TranscriptEvent("future developments", True, 7200),
            TranscriptEvent("and ethical considerations", True, 7400),
        ]
        
        result = self.process_transcript_stream(lecture_events)
        
        # Should preserve structure markers
        self.assertIn("First", result)
        self.assertIn("Second", result)
        self.assertIn("Third", result)
        # Should maintain topic coherence
        self.assertIn("artificial intelligence", result.lower())
        self.assertIn("healthcare", result.lower())
        self.assertIn("ethical considerations", result.lower())
    
    def test_casual_conversation(self):
        """Test casual conversation with colloquialisms"""
        casual_events = [
            TranscriptEvent("Hey", True, 1000),
            TranscriptEvent("what's up", True, 1200),
            TranscriptEvent("Not much", True, 2000),
            TranscriptEvent("just hanging out", True, 2200),
            TranscriptEvent("Cool", True, 3000),
            TranscriptEvent("wanna grab", True, 3200),
            TranscriptEvent("some coffee", True, 3400),
            TranscriptEvent("Sure", True, 4000),
            TranscriptEvent("let's go", True, 4200),
        ]
        
        result = self.process_transcript_stream(casual_events)
        
        # Should handle casual language
        self.assertIn("Hey", result)
        self.assertIn("what's up", result.lower())
        # Should preserve informal responses
        self.assertIn("Cool", result)
        self.assertIn("Sure", result)
    
    def test_customer_service_interaction(self):
        """Test customer service phone interaction"""
        service_events = [
            TranscriptEvent("Thank you for calling", True, 1000),
            TranscriptEvent("customer service", True, 1200),
            TranscriptEvent("How may I", True, 1400),
            TranscriptEvent("help you today", True, 1600),
            TranscriptEvent("I need to", True, 3000),
            TranscriptEvent("return an item", True, 3200),
            TranscriptEvent("I purchased online", True, 3400),
            TranscriptEvent("Certainly", True, 5000),
            TranscriptEvent("I can help", True, 5200),
            TranscriptEvent("with that", True, 5400),
            TranscriptEvent("May I have", True, 5600),
            TranscriptEvent("your order number", True, 5800),
        ]
        
        result = self.process_transcript_stream(service_events)
        
        # Should maintain polite phrasing
        self.assertIn("Thank you for calling", result)
        self.assertIn("How may I help you", result)
        # Should handle service terminology
        self.assertIn("order number", result.lower())
    
    def test_news_broadcast_style(self):
        """Test news broadcast style speech"""
        news_events = [
            TranscriptEvent("Breaking news", True, 1000),
            TranscriptEvent("this morning", True, 1200),
            TranscriptEvent("The stock market", True, 2000),
            TranscriptEvent("opened higher", True, 2200),
            TranscriptEvent("following reports", True, 2400),
            TranscriptEvent("of strong earnings", True, 2600),
            TranscriptEvent("Meanwhile", True, 4000),
            TranscriptEvent("in Washington", True, 4200),
            TranscriptEvent("lawmakers continue", True, 4400),
            TranscriptEvent("to debate", True, 4600),
            TranscriptEvent("the new bill", True, 4800),
        ]
        
        result = self.process_transcript_stream(news_events)
        
        # Should maintain news structure
        self.assertIn("Breaking news", result)
        self.assertIn("Meanwhile", result)
        # Should preserve proper nouns
        self.assertIn("Washington", result)
        # Should maintain formal tone
        self.assertIn("stock market", result.lower())
    
    def test_recipe_instructions(self):
        """Test recipe/instructional content"""
        recipe_events = [
            TranscriptEvent("First", True, 1000),
            TranscriptEvent("preheat the oven", True, 1200),
            TranscriptEvent("to 350 degrees", True, 1400),
            TranscriptEvent("Next", True, 3000),
            TranscriptEvent("mix together", True, 3200),
            TranscriptEvent("2 cups flour", True, 3400),
            TranscriptEvent("1 cup sugar", True, 3600),
            TranscriptEvent("and half a teaspoon", True, 3800),
            TranscriptEvent("of salt", True, 4000),
            TranscriptEvent("Then", True, 5000),
            TranscriptEvent("add the wet ingredients", True, 5200),
        ]
        
        result = self.process_transcript_stream(recipe_events)
        
        # Should preserve instructional markers
        self.assertIn("First", result)
        self.assertIn("Next", result)
        self.assertIn("Then", result)
        # Should preserve measurements
        self.assertIn("350 degrees", result)
        self.assertIn("2 cups", result)
        self.assertIn("1 cup", result)
    
    def test_legal_dictation(self):
        """Test legal/formal dictation"""
        legal_events = [
            TranscriptEvent("Pursuant to", True, 1000),
            TranscriptEvent("Section 5", True, 1200),
            TranscriptEvent("subsection A", True, 1400),
            TranscriptEvent("of the agreement", True, 1600),
            TranscriptEvent("The party", True, 3000),
            TranscriptEvent("of the first part", True, 3200),
            TranscriptEvent("hereinafter referred to as", True, 3400),
            TranscriptEvent("the Client", True, 3600),
            TranscriptEvent("agrees to", True, 4000),
            TranscriptEvent("the following terms", True, 4200),
        ]
        
        result = self.process_transcript_stream(legal_events)
        
        # Should preserve legal terminology
        self.assertIn("Pursuant to", result)
        self.assertIn("subsection", result.lower())
        self.assertIn("hereinafter", result.lower())
        # Should maintain formal structure
        self.assertIn("party of the first part", result.lower())
    
    def test_sports_commentary(self):
        """Test sports commentary style"""
        sports_events = [
            TranscriptEvent("And he shoots", True, 1000),
            TranscriptEvent("he scores", True, 1100),
            TranscriptEvent("What a goal", True, 1300),
            TranscriptEvent("The crowd", True, 2000),
            TranscriptEvent("goes wild", True, 2100),
            TranscriptEvent("That's his", True, 3000),
            TranscriptEvent("third goal", True, 3100),
            TranscriptEvent("this game", True, 3200),
            TranscriptEvent("Unbelievable", True, 4000),
        ]
        
        result = self.process_transcript_stream(sports_events)
        
        # Should handle excitement and short phrases
        self.assertIn("he shoots", result.lower())
        self.assertIn("he scores", result.lower())
        # Should preserve exclamations
        self.assertIn("What a goal", result)
        self.assertIn("Unbelievable", result)
    
    def test_interruptions_and_corrections(self):
        """Test handling of interruptions and self-corrections"""
        correction_events = [
            TranscriptEvent("The meeting is at", True, 1000),
            TranscriptEvent("wait no", True, 1200),
            TranscriptEvent("sorry", True, 1300),
            TranscriptEvent("it's at three", True, 1500),
            TranscriptEvent("not two", True, 1700),
            TranscriptEvent("I mean", True, 3000),
            TranscriptEvent("let me check", True, 3200),
            TranscriptEvent("yes three o'clock", True, 3400),
        ]
        
        result = self.process_transcript_stream(correction_events)
        
        # Should handle corrections naturally
        self.assertIn("wait", result.lower())
        self.assertIn("sorry", result.lower())
        # Should preserve the corrected information
        self.assertIn("three", result.lower())
    
    def test_multilingual_terms(self):
        """Test handling of foreign words and phrases"""
        multilingual_events = [
            TranscriptEvent("The restaurant", True, 1000),
            TranscriptEvent("has a certain", True, 1200),
            TranscriptEvent("je ne sais quoi", True, 1400),
            TranscriptEvent("The menu includes", True, 2000),
            TranscriptEvent("pasta al dente", True, 2200),
            TranscriptEvent("and crème brûlée", True, 2400),
            TranscriptEvent("Very haute cuisine", True, 3000),
        ]
        
        result = self.process_transcript_stream(multilingual_events)
        
        # Should preserve foreign phrases
        self.assertIn("je ne sais quoi", result.lower())
        self.assertIn("al dente", result.lower())
        self.assertIn("crème brûlée", result.lower())


class TestEdgeCaseHandling(unittest.TestCase):
    """Test edge cases and error conditions in real usage"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.punct_processor = PunctuationProcessor()
        self.frag_processor = FragmentProcessor()
    
    def test_very_long_continuous_speech(self):
        """Test handling of very long continuous speech without pauses"""
        # Generate 100 words without significant pauses
        words = [f"word{i}" for i in range(100)]
        long_text = " ".join(words)
        
        result, fragments = self.punct_processor.process_transcript(
            long_text, True, 1000, []
        )
        
        # Should handle long input without error
        self.assertIsNotNone(result or fragments)
        
        # Process through fragment reconstruction
        if result:
            reconstructed = self.frag_processor.reconstruct_fragments(result)
            self.assertIsNotNone(reconstructed)
    
    def test_rapid_fire_single_words(self):
        """Test rapid succession of single words"""
        results = []
        fragments = []
        
        # 50 single words in rapid succession (20ms apart)
        for i in range(50):
            result, fragments = self.punct_processor.process_transcript(
                f"word{i}", True, 1000 + i * 20, fragments
            )
            if result:
                results.append(result)
        
        # Flush remaining
        if fragments:
            final_result, _ = self.punct_processor.flush_pending_fragments(fragments)
            if final_result:
                results.append(final_result)
        
        # Should produce coherent output
        all_text = " ".join(results)
        self.assertGreater(len(all_text), 0)
        # Should merge many of the rapid-fire words
        self.assertLessEqual(len(results), 50)
    
    def test_alternating_languages(self):
        """Test code-switching between languages (simulated)"""
        mixed_events = [
            ("Hello everyone", 1000),
            ("Bonjour", 1500),
            ("How are you", 2000),
            ("Comment allez-vous", 2500),
            ("Let's begin", 3000),
            ("Commençons", 3500),
        ]
        
        results = []
        fragments = []
        
        for text, timestamp in mixed_events:
            result, fragments = self.punct_processor.process_transcript(
                text, True, timestamp, fragments
            )
            if result:
                results.append(result)
        
        # Should handle language switches
        all_text = " ".join(results)
        self.assertIn("Hello", all_text)
        self.assertIn("Bonjour", all_text)
    
    def test_numbers_only_input(self):
        """Test input consisting only of numbers"""
        numeric_events = [
            ("123", 1000),
            ("456", 1200),
            ("789", 1400),
            ("3.14159", 2000),
            ("2.71828", 2200),
        ]
        
        results = []
        fragments = []
        
        for text, timestamp in numeric_events:
            result, fragments = self.punct_processor.process_transcript(
                text, True, timestamp, fragments
            )
            if result:
                results.append(result)
        
        # Flush remaining
        if fragments:
            final_result, _ = self.punct_processor.flush_pending_fragments(fragments)
            if final_result:
                results.append(final_result)
        
        all_text = " ".join(results)
        # Should preserve numbers
        self.assertIn("123", all_text)
        self.assertIn("3.14159", all_text)
    
    def test_special_characters_stress_test(self):
        """Test various special characters and symbols"""
        special_events = [
            ("Hello @user", 1000),
            ("#trending topic", 1200),
            ("50% off", 1400),
            ("$99.99", 1600),
            ("C++ programming", 1800),
            ("A/B testing", 2000),
            ("24/7 support", 2200),
        ]
        
        results = []
        fragments = []
        
        for text, timestamp in special_events:
            result, fragments = self.punct_processor.process_transcript(
                text, True, timestamp, fragments
            )
            if result:
                results.append(result)
        
        all_text = " ".join(results)
        # Should preserve special characters
        self.assertIn("@", all_text)
        self.assertIn("#", all_text)
        self.assertIn("%", all_text)
        self.assertIn("$", all_text)
        self.assertIn("++", all_text)
        self.assertIn("/", all_text)


if __name__ == '__main__':
    unittest.main(verbosity=2)