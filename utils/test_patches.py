#!/usr/bin/env python3
"""
Test Patches Utility - Play musical sequences to test generated patches
"""
import os
import sys
import time
import glob
import threading
from collections import deque

import numpy as np
import sounddevice as sd
import soundfile as sf

# Add parent directory to path to import from modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from patch_utils import load_patches


# Bach's Solfeggietto in C minor, H 220 (1766) - Second Half (~20 seconds)
# This famous piece showcases rapid scales and arpeggios
# Note offsets from C (0=C, 1=C#, 2=D, 3=Eb, 4=E, 5=F, 6=F#, 7=G, 8=Ab, 9=A, 10=Bb, 11=B)
# Duration in milliseconds, tempo approximately 120 BPM (250ms per quarter note)

TEST_SEQUENCE = [
    # Measure 17-18: Ascending run in C minor
    (0, 125), (3, 125), (7, 125), (12, 125),   # C-Eb-G-C
    (15, 125), (19, 125), (22, 125), (24, 125), # Eb-G-Bb-C
    
    # Measure 19-20: Descending sequence
    (22, 125), (19, 125), (15, 125), (12, 125), # Bb-G-Eb-C
    (10, 125), (7, 125), (3, 125), (0, 125),   # Bb-G-Eb-C
    
    # Measure 21-22: Two-part counterpoint
    ([0, 12], 250), ([2, 14], 250),            # C+C, D+D
    ([3, 15], 250), ([5, 17], 250),            # Eb+Eb, F+F
    
    # Measure 23-24: Rapid sixteenth note passage
    (7, 83), (8, 83), (10, 83), (12, 83),      # G-Ab-Bb-C
    (14, 83), (15, 83), (17, 83), (19, 83),    # D-Eb-F-G
    (20, 83), (22, 83), (24, 83), (26, 83),    # Ab-Bb-C-D
    
    # Measure 25-26: Melodic sequence with harmony
    ([7, 15], 250), ([5, 17], 250),            # G+Eb, F+F
    ([3, 15], 250), ([0, 12], 250),            # Eb+Eb, C+C
    
    # Measure 27-28: Scale passages
    (12, 100), (14, 100), (15, 100), (17, 100), # C-D-Eb-F
    (19, 100), (20, 100), (22, 100), (24, 100), # G-Ab-Bb-C
    
    # Measure 29-30: Broken chord patterns
    (0, 125), (7, 125), (12, 125), (19, 125),   # C-G-C-G
    (15, 125), (22, 125), (27, 125), (22, 125), # Eb-Bb-Eb-Bb
    
    # Measure 31-32: Final ascending run
    (0, 100), (3, 100), (7, 100), (10, 100),    # C-Eb-G-Bb
    (12, 100), (15, 100), (19, 100), (22, 100), # C-Eb-G-Bb
    (24, 100), (27, 100), (31, 100), (34, 100), # C-Eb-G-Bb
    
    # Final measures: Dramatic conclusion
    ([0, 7, 15], 500),   # C minor chord
    ([5, 12, 20], 500),  # F minor chord
    ([7, 14, 22], 500),  # G major chord
    ([0, 7, 15], 1000),  # Final C minor chord (held)
]


def list_available_patches():
    """List all available patch folders in the output directory."""
    from config import OUTPUT_DIR
    
    patch_folders = []
    if os.path.exists(OUTPUT_DIR):
        for item in os.listdir(OUTPUT_DIR):
            patch_path = os.path.join(OUTPUT_DIR, item)
            if os.path.isdir(patch_path):
                # Check if it contains WAV files
                wav_files = glob.glob(os.path.join(patch_path, "*.wav"))
                if wav_files:
                    patch_folders.append(item)
    
    return sorted(patch_folders)


class PolyphonicAudioPlayer:
    """A polyphonic audio player that can mix and play multiple samples simultaneously."""
    
    def __init__(self, sample_rate=44100, channels=2):
        self.sample_rate = sample_rate
        self.channels = channels
        self.playing_samples = deque()
        self.is_playing = False
        self.stream = None
        self.lock = threading.Lock()
        
    def load_sample(self, file_path):
        """Load an audio sample from file."""
        try:
            data, sr = sf.read(file_path, always_2d=True)
            
            # Resample if necessary
            if sr != self.sample_rate:
                from scipy import signal
                num_samples = int(len(data) * self.sample_rate / sr)
                data = signal.resample(data, num_samples)
            
            # Convert to stereo if mono
            if data.shape[1] == 1 and self.channels == 2:
                data = np.repeat(data, 2, axis=1)
            # Convert to mono if stereo and we want mono
            elif data.shape[1] == 2 and self.channels == 1:
                data = np.mean(data, axis=1, keepdims=True)
            
            # Ensure we have the right number of channels
            if data.shape[1] != self.channels:
                data = data[:, :self.channels]
            
            return data.astype(np.float32)
            
        except Exception as e:
            print(f"Error loading sample {file_path}: {e}")
            return None
    
    def audio_callback(self, outdata, frames, time, status):
        """Audio callback function for sounddevice stream."""
        if status:
            print(f"Audio status: {status}")
        
        # Initialize output buffer
        outdata.fill(0)
        
        with self.lock:
            # Mix all currently playing samples
            samples_to_remove = []
            
            for i, (sample_data, position) in enumerate(self.playing_samples):
                # Calculate how many frames we can read from this sample
                remaining_frames = len(sample_data) - position
                frames_to_read = min(frames, remaining_frames)
                
                if frames_to_read > 0:
                    # Add this sample's audio to the output buffer
                    outdata[:frames_to_read] += sample_data[position:position + frames_to_read]
                    
                    # Update position
                    self.playing_samples[i] = (sample_data, position + frames_to_read)
                
                # Mark for removal if finished
                if position + frames_to_read >= len(sample_data):
                    samples_to_remove.append(i)
            
            # Remove finished samples (in reverse order to maintain indices)
            for i in reversed(samples_to_remove):
                del self.playing_samples[i]
    
    def start_stream(self):
        """Start the audio stream."""
        if not self.is_playing:
            self.stream = sd.OutputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                callback=self.audio_callback,
                blocksize=1024
            )
            self.stream.start()
            self.is_playing = True
    
    def stop_stream(self):
        """Stop the audio stream."""
        if self.is_playing and self.stream:
            self.stream.stop()
            self.stream.close()
            self.is_playing = False
            with self.lock:
                self.playing_samples.clear()
    
    def play_sample(self, file_path):
        """Start playing a sample (adds it to the mix)."""
        sample_data = self.load_sample(file_path)
        if sample_data is not None:
            with self.lock:
                self.playing_samples.append((sample_data, 0))
            return True
        return False
    
    def play_samples(self, file_paths):
        """Play multiple samples simultaneously (true polyphony)."""
        success_count = 0
        for file_path in file_paths:
            if self.play_sample(file_path):
                success_count += 1
        return success_count
    
    def is_busy(self):
        """Check if any samples are currently playing."""
        with self.lock:
            return len(self.playing_samples) > 0


# Global audio player instance
audio_player = PolyphonicAudioPlayer()


def play_audio_file(file_path):
    """Play an audio file using the polyphonic player."""
    return audio_player.play_sample(file_path)


def play_audio_files(file_paths):
    """Play multiple audio files simultaneously."""
    return audio_player.play_samples(file_paths)


def get_patch_samples(patch_folder):
    """Get all WAV files in a patch folder, sorted by note number."""
    wav_files = glob.glob(os.path.join(patch_folder, "*.wav"))
    
    # Sort by extracting note number from filename
    def get_note_number(filename):
        basename = os.path.basename(filename)
        parts = basename.split('_')
        if parts and parts[0].isdigit():
            return int(parts[0])
        return 999  # Put non-numeric files at the end
    
    wav_files.sort(key=get_note_number)
    return wav_files


def get_sample_info(file_path):
    """Extract note information from sample filename."""
    filename = os.path.basename(file_path)
    parts = filename.split('_')
    
    if parts and parts[0].isdigit():
        note_num = int(parts[0])
        if len(parts) > 1:
            note_name = parts[1].replace('.wav', '')
            return note_num, note_name
        else:
            return note_num, f"Note{note_num}"
    
    return None, filename.replace('.wav', '')


def adjust_sequence_to_samples(sequence, available_samples):
    """Adjust a test sequence to use available samples."""
    if not sequence or not available_samples:
        return []
    
    # Get note numbers from available samples
    sample_notes = []
    sample_map = {}
    
    for sample_path in available_samples:
        note_num, note_name = get_sample_info(sample_path)
        if note_num is not None:
            sample_notes.append(note_num)
            sample_map[note_num] = sample_path
    
    if not sample_notes:
        # Fallback: use samples in order
        adjusted_sequence = []
        for i, item in enumerate(sequence):
            if isinstance(item, tuple) and len(item) == 2:
                offset_or_list, duration = item
                if i < len(available_samples):
                    adjusted_sequence.append((available_samples[i], duration))
        return adjusted_sequence
    
    # Sort available notes
    sample_notes.sort()
    base_note = 36  # Start at C2 (MIDI note 36) instead of lowest available note
    
    # Find the closest available note to our desired base
    if sample_notes:
        base_note = min(sample_notes, key=lambda x: abs(x - 36))
    
    # Map sequence to available samples
    adjusted_sequence = []
    for item in sequence:
        if isinstance(item, tuple) and len(item) == 2:
            offset_or_list, duration = item
            
            if isinstance(offset_or_list, list):
                # This is a chord - multiple notes played together
                chord_samples = []
                for offset in offset_or_list:
                    target_note = base_note + offset
                    # Find closest available sample
                    closest_note = min(sample_notes, key=lambda x: abs(x - target_note))
                    sample_path = sample_map[closest_note]
                    chord_samples.append(sample_path)
                adjusted_sequence.append((chord_samples, duration))
            else:
                # Single note
                target_note = base_note + offset_or_list
                # Find closest available sample
                closest_note = min(sample_notes, key=lambda x: abs(x - target_note))
                sample_path = sample_map[closest_note]
                adjusted_sequence.append((sample_path, duration))
    
    return adjusted_sequence


def play_sequence(sequence):
    """Play a musical sequence using polyphonic audio playback."""
    print(f"Playing musical sequence...")
    
    # Start the audio stream
    audio_player.start_stream()
    
    try:
        for i, (sample_or_samples, duration_ms) in enumerate(sequence):
            if isinstance(sample_or_samples, list):
                # This is a chord - multiple samples played simultaneously
                print(f"  {i+1:2d}: CHORD ({duration_ms}ms)")
                for sample_path in sample_or_samples:
                    note_num, note_name = get_sample_info(sample_path)
                    filename = os.path.basename(sample_path)
                    print(f"      {note_name} - {filename}")
                
                # Play all chord samples simultaneously
                success_count = play_audio_files(sample_or_samples)
                if success_count == 0:
                    print(f"        Failed to play chord")
                elif success_count < len(sample_or_samples):
                    print(f"        Only {success_count}/{len(sample_or_samples)} samples played")
                    
            else:
                # Single sample
                sample_path = sample_or_samples
                note_num, note_name = get_sample_info(sample_path)
                filename = os.path.basename(sample_path)
                
                print(f"  {i+1:2d}: {note_name} ({duration_ms}ms) - {filename}")
                
                # Play the audio file
                if not play_audio_file(sample_path):
                    print(f"    Failed to play {filename}")
                    continue
            
            # Wait for the specified duration
            time.sleep(duration_ms / 1000.0)
            
            # Small gap between notes/chords
            time.sleep(0.15)
            
    finally:
        # Wait for any remaining audio to finish
        while audio_player.is_busy():
            time.sleep(0.1)
        
        # Stop the audio stream
        audio_player.stop_stream()


def test_patch(patch_name):
    """Test a specific patch with the musical sequence."""
    from config import OUTPUT_DIR
    
    print(f"\n{'='*60}")
    print(f"TESTING PATCH: {patch_name}")
    print(f"{'='*60}")
    
    # Check patch folder
    patch_folder = os.path.join(OUTPUT_DIR, patch_name)
    if not os.path.exists(patch_folder):
        print(f"Error: Patch folder not found: {patch_folder}")
        return False
    
    # Get available samples
    available_samples = get_patch_samples(patch_folder)
    if not available_samples:
        print(f"Error: No WAV files found in {patch_folder}")
        return False
    
    print(f"Found {len(available_samples)} samples:")
    for sample_path in available_samples:
        note_num, note_name = get_sample_info(sample_path)
        filename = os.path.basename(sample_path)
        print(f"  {note_name}: {filename}")
    
    print(f"\n--- Playing Musical Test Sequence ---")
    
    # Adjust sequence to use available samples
    adjusted_sequence = adjust_sequence_to_samples(TEST_SEQUENCE, available_samples)
    
    if not adjusted_sequence:
        print("No samples available for the test sequence")
        return False
    
    # Play the sequence automatically
    try:
        play_sequence(adjusted_sequence)
        print("\nSequence complete!")
    except KeyboardInterrupt:
        print("\nPlayback stopped by user.")
    
    print(f"\nTesting complete for patch '{patch_name}'")
    return True


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test generated patches by playing audio samples")
    parser.add_argument('--patch', type=str, help='Specific patch name to test')
    parser.add_argument('--list', action='store_true', help='List available patches')
    
    args = parser.parse_args()
    
    print("="*60)
    print("         ROBOSAMPLA PATCH TESTER")
    print("="*60)
    print("Playing audio samples with true polyphonic playback")
    
    try:
        # List available patches
        available_patches = list_available_patches()
        
        if args.list or not available_patches:
            print("\nAvailable patches:")
            if available_patches:
                for i, patch_name in enumerate(available_patches):
                    print(f"{i:2d}: {patch_name}")
            else:
                print("No patches found. Please record some patches first.")
            
            if not available_patches:
                sys.exit(1)
            
            if args.list:
                sys.exit(0)
        
        # Select patch to test
        if args.patch:
            if args.patch in available_patches:
                patch_to_test = args.patch
            else:
                print(f"Error: Patch '{args.patch}' not found.")
                print(f"Available patches: {', '.join(available_patches)}")
                sys.exit(1)
        else:
            # Interactive selection
            print("\nAvailable patches:")
            for i, patch_name in enumerate(available_patches):
                print(f"{i:2d}: {patch_name}")
            
            while True:
                try:
                    choice = input(f"\nSelect patch to test (0-{len(available_patches)-1}): ").strip()
                    patch_idx = int(choice)
                    
                    if 0 <= patch_idx < len(available_patches):
                        patch_to_test = available_patches[patch_idx]
                        break
                    else:
                        print(f"Invalid choice. Please enter 0-{len(available_patches)-1}")
                        
                except ValueError:
                    print("Invalid input. Please enter a number")
                except KeyboardInterrupt:
                    print("\nCancelled.")
                    sys.exit(0)
        
        # Test the selected patch
        print("\nThis will play Bach's Solfeggietto in C minor (second half):")
        print("  - Famous baroque piece by C.P.E. Bach (1766)")
        print("  - Rapid scales and arpeggios (~20 seconds)")
        print("  - True polyphonic playback with chords")
        print("  - Press Ctrl+C to stop playback")
        
        success = test_patch(patch_to_test)
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\nPlayback stopped by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
    finally:
        # Ensure audio stream is properly closed
        try:
            audio_player.stop_stream()
        except:
            pass


if __name__ == '__main__':
    main()
