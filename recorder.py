"""
Core recording functionality for playing patches and recording audio.
"""
import time
import os
import mido

from midi_utils import (
    send_note_on, send_note_off, send_program_change, 
    send_bank_select, midi_note_to_name
)
from audio_utils import get_device_channels, save_audio
from patch_utils import safe_filename, create_patch_folder
from audio_processor import process_recorded_sample, process_patch_folder
from config import SILENCE_THRESHOLD_DB, FADE_IN_MS, FADE_OUT_MS, TARGET_PEAK_DB, UNPROCESSED_FOLDER
import sounddevice as sd
import numpy as np

# Global lists to collect error information
clipping_errors = []
short_sample_errors = []


def check_for_clipping(audio_data, filename, clipping_threshold=0.99):
    """
    Check if audio contains clipping and log warnings.
    
    Args:
        audio_data: numpy array of audio samples (float, typically -1 to 1 range)
        filename: name of the file for logging
        clipping_threshold: threshold above which we consider it clipping (default 0.99)
    
    Returns:
        bool: True if clipping detected, False otherwise
    """
    # Get absolute peak value
    peak_value = np.max(np.abs(audio_data))
    
    # Count samples that exceed the clipping threshold
    clipped_samples = np.sum(np.abs(audio_data) >= clipping_threshold)
    total_samples = audio_data.size
    clipping_percentage = (clipped_samples / total_samples) * 100
    
    if clipped_samples > 0:
        error_msg = f"CLIPPING in {filename}: Peak {peak_value:.4f}, {clipped_samples}/{total_samples} samples ({clipping_percentage:.2f}%)"
        clipping_errors.append(error_msg)
        print(f"  ⚠️  {error_msg}")
        return True
    else:
        print(f"  ✓ No clipping detected (peak: {peak_value:.4f})")
        return False


def record_and_process_note(outport, note, patch, patch_folder, sample_rate, audio_device, filename):
    """
    Record and process a single note with timeout protection.
    
    Args:
        outport: MIDI output port
        note: MIDI note number
        patch: patch configuration
        patch_folder: folder to save files to
        sample_rate: audio sample rate
        audio_device: audio device for recording
        filename: filename for the recorded sample (without .wav extension)
    """
    import threading
    import signal
    
    print(f'Playing note: {note} ({filename})')
    
    # Calculate total recording time (note duration + note_gap for reverb tail)
    record_duration = patch['note_duration'] + patch['note_gap']
    
    # Determine number of channels based on patch setting and device capabilities
    if patch.get('mono', False):
        channels = 1  # Force mono recording
        print(f"Recording in MONO as requested")
    else:
        # Stereo recording (default) - use device capabilities
        max_channels = get_device_channels(audio_device)
        channels = min(2, max_channels) if max_channels > 0 else 1
        if channels == 1:
            print(f"Recording in MONO (device limitation)")
    
    recording = None
    recording_error = None
    
    def record_with_timeout():
        nonlocal recording, recording_error
        try:
            print(f"  🎤 Starting recording: {record_duration:.1f}s, {channels}ch, {sample_rate}Hz, device={audio_device}")
            
            # Start recording
            recording = sd.rec(int(record_duration * sample_rate), 
                             samplerate=sample_rate, channels=channels, 
                             dtype='float64', device=audio_device)
            
            print(f"  📡 Recording started, sending MIDI...")
            
            # Small delay to ensure recording starts before MIDI
            time.sleep(0.5)
            
            # Send MIDI note
            send_note_on(outport, note, patch['velocity'], patch['midi_channel'])
            print(f"  🎹 MIDI Note ON sent: {note} vel={patch['velocity']} ch={patch['midi_channel']}")
            time.sleep(patch['note_duration'])
            send_note_off(outport, note, patch['midi_channel'])
            print(f"  🎹 MIDI Note OFF sent: {note}")

            print(f"  ⏳ Waiting for recording to complete...")
            # Wait for recording to finish with timeout
            sd.wait()
            print(f"  ✅ Recording completed successfully")
            
        except Exception as e:
            recording_error = f"Recording error: {e}"
            print(f"  ❌ {recording_error}")
    
    # Start recording in a separate thread
    record_thread = threading.Thread(target=record_with_timeout)
    record_thread.daemon = True
    record_thread.start()
    
    # Wait for recording to complete with timeout
    timeout_seconds = record_duration + 10.0  # Extra 10 seconds buffer
    record_thread.join(timeout=timeout_seconds)
    
    if record_thread.is_alive():
        print(f"  ⚠️  Recording timeout after {timeout_seconds:.1f}s")
        try:
            sd.stop()  # Stop any ongoing recording
            time.sleep(0.5)
        except:
            pass
        
        # Try emergency reset
        if emergency_audio_reset():
            print(f"  ⚠️  TIMEOUT RECOVERED: Note {note} recording failed but audio system reset - continuing")
        else:
            print(f"  ❌ TIMEOUT: Note {note} recording failed and reset failed - skipping")
        return False
    
    if recording_error:
        print(f"  ❌ ERROR: {recording_error} - skipping note {note}")
        return False
    
    if recording is None:
        print(f"  ❌ ERROR: No audio data recorded for note {note} - skipping")
        return False
    
    try:
        # Check for clipping in the recorded audio
        wav_filename = f"{filename}.wav"
        check_for_clipping(recording, wav_filename)
        
        # Save the audio file
        filepath = os.path.join(patch_folder, wav_filename)
        shape = save_audio(recording, filepath, sample_rate)
        print(f"  Saved: {filepath} ({shape})")
        
        # Create unprocessed subfolder and save original
        unprocessed_folder = os.path.join(patch_folder, UNPROCESSED_FOLDER)
        os.makedirs(unprocessed_folder, exist_ok=True)
        unprocessed_filepath = os.path.join(unprocessed_folder, wav_filename)
        
        # Copy original file to unprocessed folder
        import shutil
        shutil.copy2(filepath, unprocessed_filepath)
        
        # Small delay  
        time.sleep(0.5)
        return True
        
    except Exception as e:
        print(f"  ❌ ERROR saving note {note}: {e}")
        return False


def check_sample_lengths(patch_folder, patch_name, min_ratio=0.3):
    """
    Check for samples that are significantly shorter than others in the same patch.
    This can indicate recording problems.
    
    Args:
        patch_folder: Path to folder containing WAV files
        patch_name: Name of the patch for error reporting
        min_ratio: Minimum ratio of shortest to longest sample (default 0.3 = 30%)
    
    Returns:
        list: List of problematic samples
    """
    global short_sample_errors
    
    try:
        import glob
        from pydub import AudioSegment
        
        # Get all WAV files in the patch folder
        wav_files = glob.glob(os.path.join(patch_folder, "*.wav"))
        wav_files.sort()
        
        if len(wav_files) < 2:
            return []  # Can't compare if less than 2 samples
        
        # Get duration of each sample
        sample_durations = {}
        for wav_file in wav_files:
            try:
                audio = AudioSegment.from_wav(wav_file)
                duration_ms = len(audio)
                filename = os.path.basename(wav_file)
                sample_durations[filename] = duration_ms
            except Exception as e:
                print(f"Warning: Could not analyze {wav_file}: {e}")
                continue
        
        if len(sample_durations) < 2:
            return []
        
        # Find min, max, and median durations
        durations = list(sample_durations.values())
        min_duration = min(durations)
        max_duration = max(durations)
        median_duration = sorted(durations)[len(durations) // 2]
        
        # Check if shortest sample is significantly shorter than the longest
        ratio = min_duration / max_duration if max_duration > 0 else 1.0
        
        # Also check against median to avoid false positives from one very long sample
        median_ratio = min_duration / median_duration if median_duration > 0 else 1.0
        
        problematic_samples = []
        
        # If the ratio is too low, find which samples are problematic
        if ratio < min_ratio or median_ratio < min_ratio:
            # Consider samples problematic if they're less than min_ratio of the median
            threshold = median_duration * min_ratio
            
            for filename, duration in sample_durations.items():
                if duration < threshold:
                    error_msg = f"SHORT SAMPLE in {patch_name}: {filename} ({duration}ms) is {duration/median_duration:.1%} of median ({median_duration}ms)"
                    short_sample_errors.append(error_msg)
                    problematic_samples.append(filename)
                    print(f"  ⚠️  {error_msg}")
        
        if not problematic_samples:
            print(f"  ✓ All samples have consistent length (range: {min_duration}-{max_duration}ms)")
        
        return problematic_samples
        
    except ImportError:
        print("Warning: Could not import required modules for sample length checking")
        return []
    except Exception as e:
        print(f"Error checking sample lengths: {e}")
        return []


def play_patch(outport, patch, sample_rate=44100, audio_device=None):
    """Play a single patch configuration and record audio."""
    patch_start_time = time.time()
    
    print(f"\nPlaying patch: {patch['name']}")
    
    if 'notes' in patch:
        # Drum patch
        print(f"Drum patch with notes: {list(patch['notes'].keys())}")
    else:
        # Regular patch
        print(f"Note range: {patch['from_note']} - {patch['to_note']}")
    
    print(f"Program: {patch['program_change']}")
    print(f"Bank MSB: {patch['bank_msb']}, Bank LSB: {patch['bank_lsb']}")
    print(f"Recording mode: {'MONO' if patch.get('mono', False) else 'STEREO'}")
    
    # Create folder for this patch
    patch_folder = create_patch_folder(patch['name'])
    print(f"Recording audio to folder: {patch_folder}")
    
    # Set up the patch
    send_bank_select(outport, patch['bank_msb'], patch['bank_lsb'], patch['midi_channel'])
    send_program_change(outport, patch['program_change'], patch['midi_channel'])
    time.sleep(1)  # Delay for bank/program change to take effect
    
    # Play the notes
    failed_notes = []
    total_notes = 0
    
    if 'notes' in patch:
        # Drum patch: play specific notes from the notes dictionary
        print(f"Drum patch with {len(patch['notes'])} specific notes")
        for note_str, drum_name in patch['notes'].items():
            note = int(note_str)
            safe_drum_name = safe_filename(drum_name)
            filename = f"{patch['name']}_{safe_drum_name}"
            total_notes += 1
            success = record_and_process_note(outport, note, patch, patch_folder, sample_rate, audio_device, filename)
            if not success:
                failed_notes.append(note)
    else:
        # Regular patch: play notes from from_note to to_note
        print(f"Record from note {patch['from_note']} to {patch['to_note']}")
        for note in range(patch['from_note'], patch['to_note'] + 1):
            note_name = midi_note_to_name(note)
            safe_note_name = safe_filename(note_name)
            filename = f"{note}_{safe_note_name}"
            total_notes += 1
            success = record_and_process_note(outport, note, patch, patch_folder, sample_rate, audio_device, filename)
            if not success:
                failed_notes.append(note)
    
    # Report any failed notes
    if failed_notes:
        print(f"\n⚠️  Failed to record {len(failed_notes)} out of {total_notes} notes:")
        for note in failed_notes:
            note_name = midi_note_to_name(note)
            print(f"   • Note {note} ({note_name})")
        print(f"✅ Successfully recorded {total_notes - len(failed_notes)} out of {total_notes} notes")
    else:
        print(f"\n✅ Successfully recorded all {total_notes} notes")
    
    
    # Check for problematic sample lengths
    print(f"Checking sample consistency for patch: {patch['name']}")
    check_sample_lengths(patch_folder, patch['name'])
    
    # Calculate and log patch processing time
    patch_end_time = time.time()
    patch_duration = patch_end_time - patch_start_time
    
    # Format duration as minutes and seconds
    patch_minutes = int(patch_duration // 60)
    patch_seconds = patch_duration % 60
    if patch_minutes > 0:
        print(f"⏱️  Patch '{patch['name']}' completed in {patch_minutes}m {patch_seconds:.1f}s")
    else:
        print(f"⏱️  Patch '{patch['name']}' completed in {patch_seconds:.1f}s")


def record_all_patches(patches, midi_port_name, sample_rate=44100, audio_device=None):
    """Record all patches with MIDI and audio recording."""
    global clipping_errors, short_sample_errors
    clipping_errors = []  # Reset clipping errors for this session
    short_sample_errors = []  # Reset short sample errors for this session
    total_start_time = time.time()
    
    if not patches:
        print("No patches found!")
        return False
        
    print(f"Loaded {len(patches)} patches")
    print("Audio recording enabled. Files will be saved in patch-specific folders.")
    
    # Count patches that will actually be processed (not skipped)
    patches_to_process = [p for p in patches if not p.get('skip', False)]
    skipped_patches = len(patches) - len(patches_to_process)
    
    if skipped_patches > 0:
        print(f"Will process {len(patches_to_process)} patches ({skipped_patches} skipped)")

    try:
        with mido.open_output(midi_port_name) as outport:
            processed_count = 0
            for i, patch in enumerate(patches):
                print(f"\n--- Patch {i+1}/{len(patches)}: {patch['name']} ---")
                
                # Check if patch should be skipped
                if patch.get('skip', False):
                    print(f"Skipping patch '{patch['name']}' (skip=true)")
                    continue
                
                play_patch(outport, patch, sample_rate, audio_device)
                processed_count += 1
                
                # Add a pause between patches
                if i < len(patches) - 1:
                    print("\nPause between patches...")
                    time.sleep(2.0)
        
        # Calculate and log total processing time
        total_end_time = time.time()
        total_duration = total_end_time - total_start_time
        
        # Format total duration as minutes and seconds
        total_minutes = int(total_duration // 60)
        total_seconds = total_duration % 60
        
        print(f"\n{'='*60}")
        print(f"🎉 ALL PATCHES COMPLETED!")
        print(f"{'='*60}")
        if total_minutes > 0:
            print(f"⏱️  Total processing time: {total_minutes}m {total_seconds:.1f}s")
        else:
            print(f"⏱️  Total processing time: {total_seconds:.1f}s")
        print(f"📊 Processed {processed_count} patches")
        if skipped_patches > 0:
            print(f"⏭️  Skipped {skipped_patches} patches")
        if processed_count > 0:
            avg_time = total_duration / processed_count
            avg_minutes = int(avg_time // 60)
            avg_seconds = avg_time % 60
            if avg_minutes > 0:
                print(f"📈 Average time per patch: {avg_minutes}m {avg_seconds:.1f}s")
            else:
                print(f"📈 Average time per patch: {avg_seconds:.1f}s")
        
        # Report clipping errors
        if clipping_errors:
            print(f"\n⚠️  CLIPPING DETECTED IN {len(clipping_errors)} SAMPLES:")
            print("-" * 60)
            for error in clipping_errors:
                print(f"   • {error}")
            print("-" * 60)
            print("💡 Consider reducing input levels to avoid clipping")
        else:
            print(f"\n✅ No clipping detected in any samples")
        
        # Report short sample errors
        if short_sample_errors:
            print(f"\n⚠️  SHORT SAMPLES DETECTED IN {len(short_sample_errors)} CASES:")
            print("-" * 60)
            for error in short_sample_errors:
                print(f"   • {error}")
            print("-" * 60)
            print("💡 Short samples may indicate recording problems or silent patches")
        else:
            print(f"\n✅ All samples have consistent lengths")
        
        # Overall quality summary
        total_issues = len(clipping_errors) + len(short_sample_errors)
        if total_issues == 0:
            print(f"\n🎉 PERFECT RECORDING SESSION - No issues detected!")
        else:
            print(f"\n📋 RECORDING COMPLETE - {total_issues} issues detected (see above)")
        
        return True
                    
    except OSError as e:
        print(f"Error opening MIDI port '{midi_port_name}': {e}")
        return False


def emergency_audio_reset():
    """Emergency function to reset audio system if it gets stuck."""
    try:
        print("  🚨 Attempting emergency audio reset...")
        sd.stop()  # Stop all streams
        time.sleep(1.0)
        sd.reset()  # Reset sounddevice
        time.sleep(1.0)
        print("  ✅ Audio system reset complete")
        return True
    except Exception as e:
        print(f"  ❌ Audio reset failed: {e}")
        return False
