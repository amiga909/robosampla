#!/usr/bin/env python3
"""
Test silence removal functionality
"""
import sys
import os
import glob

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from audio_processor import remove_silence
from pydub import AudioSegment
from config import SILENCE_THRESHOLD_DB, OUTPUT_DIR

def test_silence_removal():
    """Test silence removal on existing audio files."""
    print("="*60)
    print("SILENCE REMOVAL TEST")
    print("="*60)
    
    # Find some test files
    test_folder = OUTPUT_DIR
    if not os.path.exists(test_folder):
        print(f"Output folder '{test_folder}' not found. Please record some samples first.")
        return
    
    # Find WAV files in any patch folder
    wav_files = []
    for patch_folder in os.listdir(test_folder):
        patch_path = os.path.join(test_folder, patch_folder)
        if os.path.isdir(patch_path):
            patch_wavs = glob.glob(os.path.join(patch_path, "*.wav"))
            wav_files.extend(patch_wavs)
    
    if not wav_files:
        print(f"No WAV files found in '{test_folder}'. Please record some samples first.")
        return
    
    # Test on first few files
    test_files = wav_files[:3]  # Test first 3 files
    
    for wav_file in test_files:
        print(f"\nTesting: {os.path.basename(wav_file)}")
        print("-" * 40)
        
        try:
            # Load audio
            audio = AudioSegment.from_wav(wav_file)
            original_length = len(audio)
            
            print(f"Original length: {original_length} ms")
            print(f"Sample rate: {audio.frame_rate} Hz")
            print(f"Channels: {audio.channels}")
            print(f"Sample width: {audio.sample_width} bytes")
            print(f"Peak level: {audio.max_dBFS:.1f} dB")
            
            # Test silence removal with different thresholds
            thresholds = [-60.0, -50.0, -40.0, -30.0]
            
            for threshold in thresholds:
                print(f"\n  Testing threshold: {threshold} dB")
                trimmed = remove_silence(audio, threshold)
                new_length = len(trimmed)
                removed = original_length - new_length
                print(f"    Result: {original_length} ms -> {new_length} ms (removed {removed} ms)")
                
        except Exception as e:
            print(f"Error testing {wav_file}: {e}")

if __name__ == '__main__':
    test_silence_removal()
