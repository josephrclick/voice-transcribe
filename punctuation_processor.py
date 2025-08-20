"""
Post-processing punctuation pipeline for intelligent sentence fragment detection and merging.

This module provides the PunctuationProcessor class which analyzes transcript segments
to detect sentence fragments and merge them appropriately before display.
"""

import time
import re
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class FragmentCandidate:
    """Represents a transcript fragment that may need merging."""
    text: str
    timestamp: float
    fragment_score: float


class PunctuationProcessor:
    """
    Intelligent post-processing for transcript punctuation and sentence fragmentation.
    
    This processor analyzes incoming transcript segments to detect sentence fragments
    and merge them appropriately, reducing over-punctuation from speech-to-text APIs.
    
    The processor uses a weighted scoring system based on:
    - Length analysis (short segments are likely fragments)
    - Capitalization patterns (mid-sentence caps indicate fragments)
    - Timing analysis (rapid succession suggests continuation)
    - Grammatical structure (incomplete clauses and conjunctions)
    """
    
    # Fragment detection patterns
    CONJUNCTION_STARTERS = {
        'and', 'but', 'or', 'so', 'yet', 'for', 'nor', 'however', 'therefore',
        'meanwhile', 'furthermore', 'moreover', 'nevertheless', 'nonetheless'
    }
    
    PREPOSITION_STARTERS = {
        'in', 'on', 'at', 'by', 'with', 'from', 'to', 'of', 'for', 'about',
        'under', 'over', 'through', 'during', 'before', 'after', 'since'
    }
    
    INCOMPLETE_ENDINGS = {
        'the', 'a', 'an', 'my', 'your', 'his', 'her', 'its', 'our', 'their',
        'this', 'that', 'these', 'those', 'some', 'many', 'few', 'all', 'most'
    }
    
    def __init__(self, 
                 merge_threshold_ms: float = 800.0,
                 min_sentence_length: int = 3,
                 fragment_threshold: float = 0.7,
                 max_pending_fragments: int = 5):
        """
        Initialize the punctuation processor.
        
        Args:
            merge_threshold_ms: Maximum time gap (ms) to consider for merging
            min_sentence_length: Minimum words for a complete sentence
            fragment_threshold: Score threshold for fragment detection (0-1)
            max_pending_fragments: Maximum fragments to keep in buffer
        """
        self.merge_threshold_ms = merge_threshold_ms
        self.min_sentence_length = min_sentence_length
        self.fragment_threshold = fragment_threshold
        self.max_pending_fragments = max_pending_fragments
        
        # Scoring weights for fragment detection
        self.weights = {
            'length': 0.25,      # Short segments are likely fragments
            'timing': 0.30,      # Rapid succession suggests continuation
            'capitalization': 0.15,  # Mid-sentence caps indicate fragments
            'grammar': 0.30      # Incomplete grammatical structures (most important)
        }

    def process_transcript(self, 
                          text: str, 
                          is_final: bool, 
                          timestamp: float,
                          pending_fragments: List[FragmentCandidate]) -> Tuple[Optional[str], List[FragmentCandidate]]:
        """
        Process a transcript segment with intelligent punctuation handling.
        
        This method is stateless - all state is passed in and returned.
        
        Args:
            text: The transcript text to process
            is_final: Whether this is a final (not interim) result
            timestamp: Timestamp of this segment (milliseconds)
            pending_fragments: Current list of pending fragments
            
        Returns:
            Tuple of (processed_text_or_none, updated_pending_fragments)
            - processed_text_or_none: Text to display, or None if held for merging
            - updated_pending_fragments: Updated fragment buffer
        """
        if not is_final:
            # Pass through interim results, including empty strings
            return text if text else None, pending_fragments
        
        if not text or not text.strip():
            # Handle empty or whitespace-only final results
            return None, pending_fragments
        
        # Clean up the text
        text = text.strip()
        
        # Calculate fragment probability
        fragment_score = self._calculate_fragment_score(
            text, timestamp, pending_fragments
        )
        
        # Create a copy of pending fragments for modification
        updated_fragments = pending_fragments.copy()
        
        if fragment_score >= self.fragment_threshold:
            # This is likely a fragment - add to buffer
            fragment = FragmentCandidate(
                text=text,
                timestamp=timestamp,
                fragment_score=fragment_score
            )
            updated_fragments.append(fragment)
            
            # Enforce buffer size limit
            if len(updated_fragments) > self.max_pending_fragments:
                # Flush oldest fragment to prevent memory buildup
                oldest = updated_fragments.pop(0)
                result_text = oldest.text
                if len(updated_fragments) > 0:
                    # Try to merge with next fragment
                    next_fragment = updated_fragments[0]
                    merged = self._merge_fragments([oldest, next_fragment])
                    if merged:
                        updated_fragments[0] = FragmentCandidate(
                            text=merged,
                            timestamp=next_fragment.timestamp,
                            fragment_score=next_fragment.fragment_score
                        )
                        return None, updated_fragments
                return result_text, updated_fragments
            
            return None, updated_fragments
        else:
            # This is a complete sentence
            if updated_fragments:
                # Merge pending fragments with this complete sentence
                all_fragments = updated_fragments + [
                    FragmentCandidate(text, timestamp, fragment_score)
                ]
                merged_text = self._merge_fragments(all_fragments)
                updated_fragments.clear()
                return merged_text, updated_fragments
            else:
                # No pending fragments, return as-is
                return text, updated_fragments

    def _calculate_fragment_score(self, 
                                 text: str, 
                                 timestamp: float,
                                 pending_fragments: List[FragmentCandidate]) -> float:
        """
        Calculate the probability that text is a sentence fragment.
        
        Returns a score from 0.0 (definitely complete) to 1.0 (definitely fragment).
        """
        scores = {}
        
        # Length analysis
        words = text.split()
        word_count = len(words)
        
        if word_count == 1:
            scores['length'] = 1.0
        elif word_count == 2:
            scores['length'] = 0.9
        elif word_count < self.min_sentence_length:
            scores['length'] = 0.7
        elif word_count < 6:
            scores['length'] = 0.3
        else:
            scores['length'] = 0.0
        
        # Timing analysis
        if pending_fragments and timestamp > 0:
            last_timestamp = pending_fragments[-1].timestamp
            time_gap = timestamp - last_timestamp
            if time_gap < self.merge_threshold_ms:
                # Recent fragments suggest continuation
                scores['timing'] = 1.0 - (time_gap / self.merge_threshold_ms)
            else:
                scores['timing'] = 0.0
        else:
            scores['timing'] = 0.0
        
        # Capitalization analysis
        if text and not text[0].isupper():
            # Lowercase start suggests continuation
            scores['capitalization'] = 1.0
        elif text and text[0].isupper() and len(words) <= 2:
            # Short capitalized phrases could be fragments
            scores['capitalization'] = 0.4
        else:
            scores['capitalization'] = 0.0
        
        # Grammar analysis using heuristics
        scores['grammar'] = self._analyze_grammar_patterns(text)
        
        # Calculate weighted score
        total_score = sum(
            scores[category] * self.weights[category]
            for category in scores
        )
        
        return min(total_score, 1.0)

    def _analyze_grammar_patterns(self, text: str) -> float:
        """
        Analyze grammatical patterns to detect fragments using simple heuristics.
        
        Returns a score from 0.0 (complete) to 1.0 (fragment).
        """
        text_lower = text.lower().strip()
        words = text_lower.split()
        
        if not words:
            return 0.0
        
        first_word = words[0]
        last_word = words[-1]
        
        # Check for conjunction starters (strong fragment indicator)
        if first_word in self.CONJUNCTION_STARTERS:
            return 0.9
        
        # Check for preposition starters (moderate fragment indicator)
        if first_word in self.PREPOSITION_STARTERS:
            return 0.6
        
        # Check for incomplete endings (articles, determiners)
        if last_word in self.INCOMPLETE_ENDINGS:
            return 0.7
        
        # Check for trailing comma (suggests continuation)
        if text.rstrip().endswith(','):
            return 0.8
        
        # Check for incomplete phrases with "of", "in", "on" etc.
        if len(words) >= 2 and words[-2] in self.PREPOSITION_STARTERS:
            return 0.5
        
        # Single word fragments (except complete responses)
        if len(words) == 1:
            complete_responses = {
                'yes', 'no', 'okay', 'ok', 'sure', 'right', 'exactly',
                'correct', 'good', 'great', 'thanks', 'hello', 'hi'
            }
            if first_word not in complete_responses:
                return 0.4
        
        return 0.0

    def _merge_fragments(self, fragments: List[FragmentCandidate]) -> str:
        """
        Merge a list of fragments into a coherent sentence.
        
        Args:
            fragments: List of FragmentCandidate objects to merge
            
        Returns:
            Merged text string
        """
        if not fragments:
            return ""
        
        if len(fragments) == 1:
            return fragments[0].text
        
        # Combine fragments intelligently
        result_parts = []
        
        for i, fragment in enumerate(fragments):
            text = fragment.text.strip()
            
            if i == 0:
                # First fragment - capitalize if needed
                if text and text[0].islower():
                    # Check if previous context suggests this should remain lowercase
                    # For now, keep original capitalization
                    pass
                result_parts.append(text)
            else:
                prev_text = result_parts[-1] if result_parts else ""
                
                # Determine if we need a space
                needs_space = True
                if prev_text.endswith((' ', '\t', '\n')) or text.startswith((' ', '\t', '\n')):
                    needs_space = False
                
                # Handle punctuation connections
                if text.startswith((',', '.', '!', '?', ';', ':')):
                    needs_space = False
                elif prev_text.endswith((',', '-')):
                    needs_space = True  # Always space after comma/dash
                
                if needs_space and not prev_text.endswith(' '):
                    result_parts.append(' ')
                
                result_parts.append(text)
        
        return ''.join(result_parts)

    def flush_pending_fragments(self, pending_fragments: List[FragmentCandidate]) -> Tuple[Optional[str], List[FragmentCandidate]]:
        """
        Force flush all pending fragments as a merged result.
        
        Used when the processor needs to clear its buffer (e.g., long pause detected).
        
        Args:
            pending_fragments: Current list of pending fragments
            
        Returns:
            Tuple of (merged_text_or_none, empty_fragment_list)
        """
        if not pending_fragments:
            return None, []
        
        merged_text = self._merge_fragments(pending_fragments)
        return merged_text, []

    def get_stats(self) -> Dict[str, Any]:
        """
        Get processor configuration and statistics.
        
        Returns:
            Dictionary with current configuration
        """
        return {
            'merge_threshold_ms': self.merge_threshold_ms,
            'min_sentence_length': self.min_sentence_length,
            'fragment_threshold': self.fragment_threshold,
            'max_pending_fragments': self.max_pending_fragments,
            'weights': self.weights.copy()
        }