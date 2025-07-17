#!/usr/bin/env python3
"""
Test individual sample processing
"""
import sys
import os

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from audio_processor import process_sample
from pydub import AudioSegment
from config import SILENCE_THRESHOLD_DB, FADE_IN_MS, FADE_OUT_MS

def test_sample_processing():
    """Test processing a single sample."""
    test_file = "_output/_test_patch/unprocessed/60_C4.wav"
    
    if not os.path.exists(test_file):
        print(f"Test file {test_file} not found")
        return
    
    print("="*60)
    print("SAMPLE PROCESSING TEST")
    print("="*60)
    
    # Load original
    original = AudioSegment.from_wav(test_file)
    print(f"Original: {len(original)} ms, peak: {original.max_dBFS:.1f} dB")
    
    # Process with current settings
    processed, error_info = process_sample(original, SILENCE_THRESHOLD_DB, FADE_IN_MS, FADE_OUT_MS)
    print(f"Processed: {len(processed)} ms, peak: {processed.max_dBFS:.1f} dB")
    
    # Report any errors
    if error_info["has_error"]:
        print(f"Warning: {error_info['description']}")
    
    # Calculate changes
    length_change = len(original) - len(processed)
    print(f"Length change: -{length_change} ms ({length_change/len(original)*100:.1f}%)")
    
    # Save for comparison
    test_output = "_output/_test_patch/60_C4_processed_test.wav"
    processed.export(test_output, format="wav")
    print(f"Saved processed version to: {test_output}")

if __name__ == '__main__':
    test_sample_processing()
