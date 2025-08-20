#!/usr/bin/env python3
"""
Test data generation utilities for comprehensive testing.

Provides deterministic generation of test data including fragmented transcripts,
timing patterns, and edge cases for thorough testing of punctuation processing.
"""

import random
import json
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict


@dataclass
class TranscriptEvent:
    """Represents a single transcript event from Deepgram"""
    text: str
    is_final: bool
    timestamp: float
    expected_output: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


class TestDataGenerator:
    """Generate deterministic test data for punctuation processing tests"""
    
    def __init__(self, seed: int = 42):
        """Initialize generator with optional seed for reproducibility"""
        self.seed = seed
        random.seed(seed)
        
        # Common test phrases
        self.complete_sentences = [
            "This is a complete sentence.",
            "The weather is nice today.",
            "I really enjoyed that movie we watched.",
            "Let's schedule a meeting for tomorrow.",
            "The project is progressing well.",
            "We need to review the documentation.",
            "Can you send me the report?",
            "That's an excellent suggestion!",
            "I'll have it ready by Friday.",
            "Thanks for your help with this."
        ]
        
        self.fragments = [
            "and then",
            "but wait",
            "so we",
            "the next",
            "which is",
            "that was",
            "for the",
            "with our",
            "to be",
            "as well"
        ]
        
        self.conjunctions = ["and", "but", "so", "however", "therefore", "moreover"]
        self.prepositions = ["in", "on", "at", "to", "from", "with", "for", "by"]
        
        self.abbreviations = [
            "Dr.", "Mr.", "Mrs.", "Ms.", "Prof.",
            "Jan.", "Feb.", "Mar.", "Apr.", "Aug.", "Sept.", "Oct.", "Nov.", "Dec.",
            "Inc.", "Corp.", "Ltd.", "Co.",
            "St.", "Ave.", "Blvd.", "Rd.",
            "U.S.", "U.K.", "E.U.",
            "a.m.", "p.m.", "etc.", "i.e.", "e.g."
        ]
        
        self.valid_single_words = [
            "Yes", "No", "Okay", "Sure", "Thanks",
            "Hello", "Goodbye", "Welcome", "Sorry", "Please"
        ]
    
    def generate_fragmented_samples(
        self, 
        base_sentences: Optional[List[str]] = None,
        fragment_levels: List[str] = ["light", "moderate", "heavy"]
    ) -> Dict[str, List[Dict]]:
        """Generate test data with various fragmentation patterns"""
        if base_sentences is None:
            base_sentences = self.complete_sentences[:5]
        
        samples = {}
        
        for level in fragment_levels:
            samples[level] = []
            
            for sentence in base_sentences:
                if level == "heavy":
                    fragmented = self._fragment_aggressively(sentence)
                elif level == "moderate":
                    fragmented = self._fragment_moderately(sentence)
                elif level == "light":
                    fragmented = self._fragment_lightly(sentence)
                else:
                    fragmented = sentence
                
                samples[level].append({
                    "original": sentence,
                    "fragmented": fragmented,
                    "expected_merge": self._clean_sentence(sentence)
                })
        
        return samples
    
    def _fragment_aggressively(self, sentence: str) -> str:
        """Fragment every 1-2 words"""
        words = sentence.replace('.', '').replace('!', '').replace('?', '').split()
        fragmented_parts = []
        
        i = 0
        while i < len(words):
            chunk_size = random.choice([1, 2])
            chunk = words[i:i+chunk_size]
            fragmented_parts.append(' '.join(chunk))
            i += chunk_size
        
        return '. '.join(fragmented_parts) + '.'
    
    def _fragment_moderately(self, sentence: str) -> str:
        """Fragment at natural break points"""
        words = sentence.replace('.', '').replace('!', '').replace('?', '').split()
        
        if len(words) < 4:
            return sentence
        
        # Find natural break points
        break_indices = []
        for i, word in enumerate(words):
            if i > 0 and (
                word.lower() in self.conjunctions or
                word.lower() in self.prepositions or
                i == len(words) // 2
            ):
                break_indices.append(i)
        
        if not break_indices:
            break_indices = [len(words) // 2]
        
        # Create fragments
        fragments = []
        last_index = 0
        for break_index in break_indices:
            if break_index > last_index:
                fragments.append(' '.join(words[last_index:break_index]))
                last_index = break_index
        
        if last_index < len(words):
            fragments.append(' '.join(words[last_index:]))
        
        return '. '.join(fragments) + '.'
    
    def _fragment_lightly(self, sentence: str) -> str:
        """Minimal fragmentation - split once at a natural point"""
        words = sentence.replace('.', '').replace('!', '').replace('?', '').split()
        
        if len(words) < 4:
            return sentence
        
        # Find one natural break point
        mid_point = len(words) // 2
        break_point = mid_point
        
        # Look for conjunction or preposition near midpoint
        for i in range(max(0, mid_point - 2), min(len(words), mid_point + 3)):
            if words[i].lower() in self.conjunctions or words[i].lower() in self.prepositions:
                break_point = i
                break
        
        part1 = ' '.join(words[:break_point])
        part2 = ' '.join(words[break_point:])
        
        return f"{part1}. {part2}."
    
    def _clean_sentence(self, sentence: str) -> str:
        """Clean up a sentence for expected output"""
        # Remove multiple spaces and ensure single period at end
        cleaned = ' '.join(sentence.split())
        if not cleaned.endswith(('.', '!', '?')):
            cleaned += '.'
        return cleaned
    
    def generate_transcript_stream(
        self,
        duration_seconds: int = 30,
        words_per_second: float = 2.5,
        fragment_probability: float = 0.3,
        pause_probability: float = 0.1
    ) -> List[TranscriptEvent]:
        """Generate a stream of transcript events simulating real speech"""
        events = []
        current_time = 0.0
        
        total_words = int(duration_seconds * words_per_second)
        words_generated = 0
        
        while words_generated < total_words:
            # Decide whether to generate fragment or complete sentence
            if random.random() < fragment_probability:
                text = random.choice(self.fragments)
                words_in_text = len(text.split())
            else:
                text = random.choice(self.complete_sentences)
                words_in_text = len(text.split())
            
            # Add the event
            events.append(TranscriptEvent(
                text=text,
                is_final=True,
                timestamp=current_time * 1000  # Convert to milliseconds
            ))
            
            words_generated += words_in_text
            
            # Update time with potential pause
            word_duration = words_in_text / words_per_second
            current_time += word_duration
            
            if random.random() < pause_probability:
                pause_duration = random.uniform(0.5, 2.0)
                current_time += pause_duration
        
        return events
    
    def generate_edge_cases(self) -> List[TranscriptEvent]:
        """Generate edge case transcript events"""
        edge_cases = []
        timestamp = 1000.0
        
        # Empty and whitespace
        edge_cases.append(TranscriptEvent("", True, timestamp))
        timestamp += 100
        edge_cases.append(TranscriptEvent("   ", True, timestamp))
        timestamp += 100
        edge_cases.append(TranscriptEvent("\t\n", True, timestamp))
        timestamp += 100
        
        # Single punctuation
        edge_cases.append(TranscriptEvent(".", True, timestamp))
        timestamp += 100
        edge_cases.append(TranscriptEvent("?", True, timestamp))
        timestamp += 100
        edge_cases.append(TranscriptEvent("!", True, timestamp))
        timestamp += 100
        
        # Abbreviations
        for abbr in self.abbreviations[:5]:
            edge_cases.append(TranscriptEvent(f"See {abbr}", True, timestamp))
            timestamp += 200
            edge_cases.append(TranscriptEvent("Smith", True, timestamp))
            timestamp += 200
        
        # Numbers and decimals
        edge_cases.append(TranscriptEvent("The value is 3.14", True, timestamp))
        timestamp += 200
        edge_cases.append(TranscriptEvent("Version 2.0.1", True, timestamp))
        timestamp += 200
        edge_cases.append(TranscriptEvent("$29.99", True, timestamp))
        timestamp += 200
        edge_cases.append(TranscriptEvent("1,234,567", True, timestamp))
        timestamp += 200
        
        # URLs and emails
        edge_cases.append(TranscriptEvent("Visit https://example.com", True, timestamp))
        timestamp += 200
        edge_cases.append(TranscriptEvent("for details", True, timestamp))
        timestamp += 100
        edge_cases.append(TranscriptEvent("Email user@example.com", True, timestamp))
        timestamp += 200
        
        # Special characters
        edge_cases.append(TranscriptEvent("Hello (world)", True, timestamp))
        timestamp += 200
        edge_cases.append(TranscriptEvent('"quoted text"', True, timestamp))
        timestamp += 200
        edge_cases.append(TranscriptEvent("Item #1", True, timestamp))
        timestamp += 200
        
        # Valid single words
        for word in self.valid_single_words[:5]:
            edge_cases.append(TranscriptEvent(word, True, timestamp))
            timestamp += 300
        
        # Very long text
        long_text = " ".join(["word" for _ in range(100)])
        edge_cases.append(TranscriptEvent(long_text, True, timestamp))
        timestamp += 1000
        
        # Rapid succession
        for i in range(10):
            edge_cases.append(TranscriptEvent(f"rapid{i}", True, timestamp))
            timestamp += 10  # Only 10ms between events
        
        return edge_cases
    
    def generate_timing_patterns(self) -> List[Tuple[str, List[TranscriptEvent]]]:
        """Generate various timing pattern scenarios"""
        patterns = []
        
        # Pattern 1: Rapid succession (should merge)
        rapid_events = [
            TranscriptEvent("Hello", True, 1000),
            TranscriptEvent("world", True, 1100),
            TranscriptEvent("today", True, 1200),
        ]
        patterns.append(("rapid_succession", rapid_events))
        
        # Pattern 2: Long pauses (should not merge)
        pause_events = [
            TranscriptEvent("First sentence", True, 1000),
            TranscriptEvent("Second sentence", True, 3000),
            TranscriptEvent("Third sentence", True, 5000),
        ]
        patterns.append(("long_pauses", pause_events))
        
        # Pattern 3: Mixed timing
        mixed_events = [
            TranscriptEvent("Quick", True, 1000),
            TranscriptEvent("succession", True, 1100),
            TranscriptEvent("Then a pause", True, 2500),
            TranscriptEvent("Another quick", True, 2600),
            TranscriptEvent("part", True, 2700),
        ]
        patterns.append(("mixed_timing", mixed_events))
        
        # Pattern 4: Near threshold timing
        threshold_events = [
            TranscriptEvent("Just under", True, 1000),
            TranscriptEvent("threshold", True, 1790),  # 790ms gap (under 800ms)
            TranscriptEvent("Just over", True, 2610),  # 820ms gap (over 800ms)
            TranscriptEvent("threshold", True, 3430),
        ]
        patterns.append(("near_threshold", threshold_events))
        
        return patterns
    
    def generate_real_world_scenarios(self) -> Dict[str, List[TranscriptEvent]]:
        """Generate realistic speech pattern scenarios"""
        scenarios = {}
        
        # Meeting transcription
        meeting = [
            TranscriptEvent("Good morning everyone", True, 1000),
            TranscriptEvent("Let's start today's meeting", True, 1500),
            TranscriptEvent("First item on the agenda", True, 3000),
            TranscriptEvent("Is the budget review", True, 3200),
            TranscriptEvent("Sarah can you", True, 5000),
            TranscriptEvent("Please share your screen", True, 5200),
            TranscriptEvent("And show us", True, 5400),
            TranscriptEvent("The quarterly numbers", True, 5600),
        ]
        scenarios["meeting"] = meeting
        
        # Technical dictation
        technical = [
            TranscriptEvent("Create a function", True, 1000),
            TranscriptEvent("Called process data", True, 1200),
            TranscriptEvent("That takes", True, 1400),
            TranscriptEvent("A pandas dataframe", True, 1600),
            TranscriptEvent("And returns", True, 1800),
            TranscriptEvent("The cleaned dataset", True, 2000),
            TranscriptEvent("Add error handling", True, 3000),
            TranscriptEvent("For missing values", True, 3200),
        ]
        scenarios["technical_dictation"] = technical
        
        # Conversational
        conversation = [
            TranscriptEvent("How are you", True, 1000),
            TranscriptEvent("I'm doing well", True, 2000),
            TranscriptEvent("thanks for asking", True, 2100),
            TranscriptEvent("What about you", True, 2300),
            TranscriptEvent("Pretty good", True, 3000),
            TranscriptEvent("just busy with work", True, 3100),
            TranscriptEvent("Yeah I understand", True, 4000),
            TranscriptEvent("It's been hectic", True, 4200),
        ]
        scenarios["conversation"] = conversation
        
        # Fast speech
        fast_speech = []
        base_time = 1000
        for i in range(20):
            fast_speech.append(TranscriptEvent(
                f"word{i}",
                True,
                base_time + i * 50  # 50ms between words (very fast)
            ))
        scenarios["fast_speech"] = fast_speech
        
        # Slow careful speech
        slow_speech = [
            TranscriptEvent("This", True, 1000),
            TranscriptEvent("is", True, 1500),
            TranscriptEvent("very", True, 2000),
            TranscriptEvent("carefully", True, 2500),
            TranscriptEvent("spoken", True, 3000),
            TranscriptEvent("text", True, 3500),
        ]
        scenarios["slow_speech"] = slow_speech
        
        return scenarios
    
    def save_test_data(self, filename: str, data: any) -> None:
        """Save test data to JSON file for golden testing"""
        if isinstance(data, list):
            # Convert TranscriptEvent objects to dicts
            if data and isinstance(data[0], TranscriptEvent):
                data = [event.to_dict() for event in data]
        elif isinstance(data, dict):
            # Convert any TranscriptEvent objects in dict values
            for key, value in data.items():
                if isinstance(value, list) and value and isinstance(value[0], TranscriptEvent):
                    data[key] = [event.to_dict() for event in value]
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_test_data(self, filename: str) -> any:
        """Load test data from JSON file"""
        with open(filename, 'r') as f:
            data = json.load(f)
        
        # Convert dicts back to TranscriptEvent objects where appropriate
        if isinstance(data, list) and data and isinstance(data[0], dict) and 'text' in data[0]:
            return [TranscriptEvent(**item) for item in data]
        elif isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, list) and value and isinstance(value[0], dict) and 'text' in value[0]:
                    data[key] = [TranscriptEvent(**item) for item in value]
        
        return data


def create_golden_test_fixtures():
    """Create golden test fixtures for regression testing"""
    generator = TestDataGenerator(seed=42)
    
    # Generate and save various test data sets
    fixtures_dir = "tests/fixtures"
    import os
    os.makedirs(fixtures_dir, exist_ok=True)
    
    # Fragmented samples
    fragmented = generator.generate_fragmented_samples()
    generator.save_test_data(f"{fixtures_dir}/fragmented_samples.json", fragmented)
    
    # Edge cases
    edge_cases = generator.generate_edge_cases()
    generator.save_test_data(f"{fixtures_dir}/edge_cases.json", edge_cases)
    
    # Timing patterns
    timing_patterns = generator.generate_timing_patterns()
    timing_data = {name: events for name, events in timing_patterns}
    generator.save_test_data(f"{fixtures_dir}/timing_patterns.json", timing_data)
    
    # Real world scenarios
    scenarios = generator.generate_real_world_scenarios()
    generator.save_test_data(f"{fixtures_dir}/real_world_scenarios.json", scenarios)
    
    # Transcript stream
    stream = generator.generate_transcript_stream(duration_seconds=60)
    generator.save_test_data(f"{fixtures_dir}/transcript_stream.json", stream)
    
    print(f"Generated test fixtures in {fixtures_dir}/")
    return fixtures_dir


if __name__ == "__main__":
    # Example usage
    generator = TestDataGenerator()
    
    # Generate fragmented samples
    samples = generator.generate_fragmented_samples()
    print("Fragmented Samples:")
    for level, data in samples.items():
        print(f"\n{level.upper()} fragmentation:")
        for sample in data[:2]:  # Show first 2 samples
            print(f"  Original: {sample['original']}")
            print(f"  Fragmented: {sample['fragmented']}")
            print()
    
    # Generate edge cases
    edge_cases = generator.generate_edge_cases()
    print("\nEdge Cases (first 5):")
    for event in edge_cases[:5]:
        print(f"  {event.timestamp}ms: '{event.text}'")
    
    # Generate timing patterns
    patterns = generator.generate_timing_patterns()
    print("\nTiming Patterns:")
    for name, events in patterns:
        print(f"\n{name}:")
        for event in events:
            print(f"  {event.timestamp}ms: '{event.text}'")
    
    # Create golden fixtures
    print("\n" + "="*50)
    create_golden_test_fixtures()