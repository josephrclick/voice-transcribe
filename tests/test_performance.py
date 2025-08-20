#!/usr/bin/env python3
"""
Performance tests for punctuation processing components.

These tests verify that processing meets real-time requirements and
can handle high-frequency inputs without performance degradation.

To run performance tests:
    RUN_PERF_TESTS=1 python -m pytest tests/test_performance.py -v
"""

import unittest
import time
import os
import sys
from typing import List, Tuple
import random
import string

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from punctuation_processor import PunctuationProcessor, FragmentCandidate
from enhance import FragmentProcessor


# Skip performance tests by default unless RUN_PERF_TESTS env var is set
SKIP_PERF_TESTS = os.environ.get('RUN_PERF_TESTS', '').lower() not in ('1', 'true', 'yes')


@unittest.skipIf(SKIP_PERF_TESTS, "Performance tests skipped. Set RUN_PERF_TESTS=1 to run.")
class TestPerformanceMetrics(unittest.TestCase):
    """Test performance requirements for real-time processing"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.punct_processor = PunctuationProcessor()
        self.frag_processor = FragmentProcessor()
    
    def generate_random_text(self, word_count: int) -> str:
        """Generate random text with specified word count"""
        words = []
        for _ in range(word_count):
            word_length = random.randint(3, 10)
            word = ''.join(random.choices(string.ascii_lowercase, k=word_length))
            words.append(word)
        return ' '.join(words)
    
    def test_fragment_detection_latency(self):
        """Test fragment detection meets <5ms requirement"""
        test_inputs = [
            "Short fragment",
            "This is a longer sentence with more words to process",
            self.generate_random_text(20),
            self.generate_random_text(50),
        ]
        
        latencies = []
        
        for input_text in test_inputs:
            start_time = time.perf_counter()
            score = self.punct_processor._calculate_fragment_score(input_text, 1000, [])
            end_time = time.perf_counter()
            
            latency_ms = (end_time - start_time) * 1000
            latencies.append(latency_ms)
            
            # Each detection should be under 5ms
            self.assertLess(latency_ms, 5.0, 
                          f"Fragment detection took {latency_ms:.2f}ms (limit: 5ms)")
        
        # Average should be well under 5ms
        avg_latency = sum(latencies) / len(latencies)
        self.assertLess(avg_latency, 3.0,
                       f"Average latency {avg_latency:.2f}ms exceeds target")
    
    def test_merge_processing_latency(self):
        """Test merge processing meets <10ms requirement"""
        test_cases = [
            # Small merge
            [FragmentCandidate("Hello", 1000, 0.8),
             FragmentCandidate("world", 1100, 0.9)],
            # Medium merge
            [FragmentCandidate(f"word{i}", 1000 + i*100, 0.7) 
             for i in range(5)],
            # Large merge
            [FragmentCandidate(f"word{i}", 1000 + i*100, 0.6) 
             for i in range(10)],
        ]
        
        latencies = []
        
        for fragments in test_cases:
            start_time = time.perf_counter()
            result = self.punct_processor._merge_fragments(fragments)
            end_time = time.perf_counter()
            
            latency_ms = (end_time - start_time) * 1000
            latencies.append(latency_ms)
            
            # Each merge should be under 10ms
            self.assertLess(latency_ms, 10.0,
                          f"Merge processing took {latency_ms:.2f}ms (limit: 10ms)")
        
        # Average should be well under 10ms
        avg_latency = sum(latencies) / len(latencies)
        self.assertLess(avg_latency, 5.0,
                       f"Average merge latency {avg_latency:.2f}ms exceeds target")
    
    def test_full_processing_latency(self):
        """Test complete transcript processing meets real-time requirements"""
        test_inputs = [
            "Short text",
            "This is a medium length sentence with several words",
            "This. Is. A. Heavily. Fragmented. Input. That. Should. Still. Process. Quickly.",
            self.generate_random_text(30),
        ]
        
        latencies = []
        
        for input_text in test_inputs:
            fragments = []
            start_time = time.perf_counter()
            result, fragments = self.punct_processor.process_transcript(
                input_text, True, time.time() * 1000, fragments
            )
            end_time = time.perf_counter()
            
            latency_ms = (end_time - start_time) * 1000
            latencies.append(latency_ms)
            
            # Full processing should be under 10ms
            self.assertLess(latency_ms, 10.0,
                          f"Processing took {latency_ms:.2f}ms (limit: 10ms)")
        
        # 99th percentile should be under 10ms
        sorted_latencies = sorted(latencies)
        p99_index = int(len(sorted_latencies) * 0.99)
        p99_latency = sorted_latencies[min(p99_index, len(sorted_latencies)-1)]
        self.assertLess(p99_latency, 10.0,
                       f"99th percentile latency {p99_latency:.2f}ms exceeds limit")
    
    def test_high_frequency_input_handling(self):
        """Test handling rapid transcript updates (simulating fast speech)"""
        # Simulate 20 updates in rapid succession
        rapid_inputs = [(f"word{i}", True, i * 50) for i in range(20)]
        
        fragments = []
        results = []
        
        start_time = time.perf_counter()
        for text, is_final, timestamp in rapid_inputs:
            result, fragments = self.punct_processor.process_transcript(
                text, is_final, timestamp, fragments
            )
            if result:
                results.append(result)
        end_time = time.perf_counter()
        
        total_time = end_time - start_time
        
        # Should handle 20 updates in under 200ms
        self.assertLess(total_time, 0.2,
                       f"Rapid processing took {total_time:.3f}s (limit: 0.2s)")
        
        # Average per-update time should be under 10ms
        avg_time_ms = (total_time / 20) * 1000
        self.assertLess(avg_time_ms, 10.0,
                       f"Average per-update time {avg_time_ms:.2f}ms exceeds limit")
    
    def test_fragment_reconstruction_performance(self):
        """Test FragmentProcessor reconstruction performance"""
        test_cases = [
            "Simple. Fragment. Test.",
            "This. Is. A. Much. Longer. Fragmented. Text. With. Many. Periods.",
            ". ".join(self.generate_random_text(20).split()),  # 20 word fragments
            ". ".join(self.generate_random_text(50).split()),  # 50 word fragments
        ]
        
        latencies = []
        
        for fragmented_text in test_cases:
            start_time = time.perf_counter()
            result = self.frag_processor.reconstruct_fragments(fragmented_text)
            end_time = time.perf_counter()
            
            latency_ms = (end_time - start_time) * 1000
            latencies.append(latency_ms)
            
            # Reconstruction should be fast even for large inputs
            self.assertLess(latency_ms, 20.0,
                          f"Reconstruction took {latency_ms:.2f}ms (limit: 20ms)")
        
        # Average should be well under limit
        avg_latency = sum(latencies) / len(latencies)
        self.assertLess(avg_latency, 10.0,
                       f"Average reconstruction latency {avg_latency:.2f}ms")
    
    def test_memory_efficiency(self):
        """Test that fragment buffer doesn't grow unbounded"""
        # Process many fragments
        fragments = []
        memory_snapshots = []
        
        for i in range(100):
            text = f"fragment {i}"
            result, fragments = self.punct_processor.process_transcript(
                text, True, 1000 + i * 100, fragments
            )
            
            # Record buffer size
            memory_snapshots.append(len(fragments))
        
        # Buffer should never exceed max_pending_fragments
        max_buffer_size = max(memory_snapshots)
        self.assertLessEqual(max_buffer_size, self.punct_processor.max_pending_fragments,
                           f"Buffer grew to {max_buffer_size}, exceeds limit")
        
        # Average buffer size should be reasonable
        avg_buffer_size = sum(memory_snapshots) / len(memory_snapshots)
        self.assertLess(avg_buffer_size, self.punct_processor.max_pending_fragments,
                       f"Average buffer size {avg_buffer_size:.1f} is too high")
    
    def test_sustained_load_performance(self):
        """Test performance under sustained load (30 second simulation)"""
        # Simulate 30 seconds of speech at ~3 words per second
        duration_seconds = 30
        words_per_second = 3
        total_words = duration_seconds * words_per_second
        
        fragments = []
        results = []
        latencies = []
        
        start_time = time.perf_counter()
        
        for i in range(total_words):
            word = f"word{i % 100}"  # Cycle through 100 different words
            timestamp = 1000 + (i * 333)  # ~3 words per second
            
            iter_start = time.perf_counter()
            result, fragments = self.punct_processor.process_transcript(
                word, True, timestamp, fragments
            )
            iter_end = time.perf_counter()
            
            if result:
                results.append(result)
            
            latencies.append((iter_end - iter_start) * 1000)
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        # Should complete in reasonable time
        self.assertLess(total_time, 5.0,
                       f"Sustained load test took {total_time:.2f}s (limit: 5s)")
        
        # 99th percentile latency should remain low
        sorted_latencies = sorted(latencies)
        p99_index = int(len(sorted_latencies) * 0.99)
        p99_latency = sorted_latencies[p99_index]
        self.assertLess(p99_latency, 10.0,
                       f"99th percentile under load: {p99_latency:.2f}ms")
        
        # Median latency should be very low
        median_index = len(sorted_latencies) // 2
        median_latency = sorted_latencies[median_index]
        self.assertLess(median_latency, 2.0,
                       f"Median latency under load: {median_latency:.2f}ms")


@unittest.skipIf(SKIP_PERF_TESTS, "Performance tests skipped. Set RUN_PERF_TESTS=1 to run.")
class TestThroughputBenchmarks(unittest.TestCase):
    """Test throughput capabilities of the processing pipeline"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.punct_processor = PunctuationProcessor()
        self.frag_processor = FragmentProcessor()
    
    def test_words_per_second_throughput(self):
        """Test maximum words per second throughput"""
        # Generate test data
        num_words = 1000
        words = [f"word{i}" for i in range(num_words)]
        
        fragments = []
        results = []
        
        start_time = time.perf_counter()
        
        for i, word in enumerate(words):
            result, fragments = self.punct_processor.process_transcript(
                word, True, 1000 + i * 10, fragments
            )
            if result:
                results.append(result)
        
        end_time = time.perf_counter()
        elapsed_seconds = end_time - start_time
        
        words_per_second = num_words / elapsed_seconds
        
        # Should handle at least 100 words per second
        self.assertGreater(words_per_second, 100,
                          f"Throughput {words_per_second:.0f} words/sec below target")
        
        print(f"\nThroughput: {words_per_second:.0f} words/second")
    
    def test_fragment_reconstruction_throughput(self):
        """Test fragment reconstruction throughput"""
        # Generate heavily fragmented text
        num_sentences = 100
        fragmented_texts = []
        
        for i in range(num_sentences):
            words = [f"word{j}" for j in range(10)]
            fragmented = ". ".join(words) + "."
            fragmented_texts.append(fragmented)
        
        start_time = time.perf_counter()
        
        for text in fragmented_texts:
            result = self.frag_processor.reconstruct_fragments(text)
        
        end_time = time.perf_counter()
        elapsed_seconds = end_time - start_time
        
        sentences_per_second = num_sentences / elapsed_seconds
        
        # Should handle at least 50 fragmented sentences per second
        self.assertGreater(sentences_per_second, 50,
                          f"Reconstruction throughput {sentences_per_second:.0f} sentences/sec")
        
        print(f"\nReconstruction throughput: {sentences_per_second:.0f} sentences/second")
    
    def test_parallel_processing_simulation(self):
        """Simulate parallel processing of multiple streams"""
        # Simulate 5 concurrent transcription streams
        num_streams = 5
        words_per_stream = 100
        
        streams = []
        for stream_id in range(num_streams):
            processor = PunctuationProcessor()
            fragments = []
            stream_data = {
                'processor': processor,
                'fragments': fragments,
                'results': []
            }
            streams.append(stream_data)
        
        start_time = time.perf_counter()
        
        # Process words round-robin across streams
        for word_index in range(words_per_stream):
            for stream_id, stream in enumerate(streams):
                word = f"stream{stream_id}_word{word_index}"
                timestamp = 1000 + word_index * 100
                
                result, stream['fragments'] = stream['processor'].process_transcript(
                    word, True, timestamp, stream['fragments']
                )
                if result:
                    stream['results'].append(result)
        
        end_time = time.perf_counter()
        elapsed_seconds = end_time - start_time
        
        total_words = num_streams * words_per_stream
        words_per_second = total_words / elapsed_seconds
        
        # Should handle multiple streams efficiently
        self.assertGreater(words_per_second, 200,
                          f"Multi-stream throughput {words_per_second:.0f} words/sec")
        
        print(f"\nMulti-stream throughput: {words_per_second:.0f} words/second across {num_streams} streams")


class PerformanceBenchmarks:
    """Performance benchmarks for the punctuation sprint"""
    
    BENCHMARKS = {
        "fragment_detection": 5,      # ms per transcript
        "merge_processing": 10,       # ms per merge operation
        "ui_update_latency": 16,      # ms (60fps requirement)
        "configuration_change": 100,  # ms for settings update
        "service_restart": 2000,      # ms for graceful restart
    }
    
    @classmethod
    def run_all_benchmarks(cls):
        """Run comprehensive performance testing"""
        results = {}
        
        # Fragment detection benchmark
        processor = PunctuationProcessor()
        test_text = "This is a test sentence for benchmarking"
        
        start = time.perf_counter()
        processor._calculate_fragment_score(test_text, 1000, [])
        end = time.perf_counter()
        
        results["fragment_detection"] = {
            "actual_time": (end - start) * 1000,
            "max_allowed": cls.BENCHMARKS["fragment_detection"],
            "passed": (end - start) * 1000 <= cls.BENCHMARKS["fragment_detection"]
        }
        
        # Merge processing benchmark
        fragments = [FragmentCandidate(f"word{i}", 1000 + i*100, 0.7) for i in range(5)]
        
        start = time.perf_counter()
        processor._merge_fragments(fragments)
        end = time.perf_counter()
        
        results["merge_processing"] = {
            "actual_time": (end - start) * 1000,
            "max_allowed": cls.BENCHMARKS["merge_processing"],
            "passed": (end - start) * 1000 <= cls.BENCHMARKS["merge_processing"]
        }
        
        return results


if __name__ == '__main__':
    if SKIP_PERF_TESTS:
        print("\nPerformance tests skipped. Set RUN_PERF_TESTS=1 to run.")
        print("Example: RUN_PERF_TESTS=1 python -m pytest tests/test_performance.py -v\n")
    else:
        # Run benchmarks if executing directly
        print("\nRunning performance benchmarks...")
        benchmarks = PerformanceBenchmarks.run_all_benchmarks()
        
        print("\nBenchmark Results:")
        print("-" * 50)
        for name, result in benchmarks.items():
            status = "✓ PASS" if result["passed"] else "✗ FAIL"
            print(f"{name:20} {result['actual_time']:6.2f}ms / {result['max_allowed']:6.2f}ms  {status}")
        
        print("\n")
        
    # Run unit tests
    unittest.main(verbosity=2)