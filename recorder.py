"""
Core recording functionality for playing patches and recording audio.
"""
import time
import os
import mido

from midi_utils import (
    send_note_on, send_note_off, send_program_change, 
    send_bank_select, send_airbase_bank_select, send_control_change, midi_note_to_name
)
from audio_utils import get_device_channels, save_audio
from patch_utils import safe_filename, create_patch_folder, save_patches
#from audio_processor import process_recorded_sample, process_patch_folder
from config import (
    SILENCE_THRESHOLD_DB, FADE_IN_MS, FADE_OUT_MS, TARGET_PEAK_DB, 
    SAMPLE_RATE, DEFAULT_VELOCITY
)
import sounddevice as sd
import numpy as np

# Global lists to collect error information
clipping_errors = []
short_sample_errors = []


def check_for_clipping(audio_data, filename, patch_name=None, clipping_threshold=0.99):
    """
    Check if audio contains clipping and log warnings.
    
    Args:
        audio_data: numpy array of audio samples (float, typically -1 to 1 range)
        filename: name of the file for logging
        patch_name: name of the patch for logging (optional)
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
        # Include patch name in error message if provided
        if patch_name:
            error_msg = f"CLIPPING in patch '{patch_name}' - {filename}: Peak {peak_value:.4f}, {clipped_samples}/{total_samples} samples ({clipping_percentage:.2f}%)"
        else:
            error_msg = f"CLIPPING in {filename}: Peak {peak_value:.4f}, {clipped_samples}/{total_samples} samples ({clipping_percentage:.2f}%)"
        clipping_errors.append(error_msg)
        print(f"  ⚠️  {error_msg}")
        return True
    else:
        print(f"  ✓ No clipping detected (peak: {peak_value:.4f})")
        return False


def record_and_process_note(outport, note, patch, patch_folder, sample_rate, audio_device, filename, cc_value=None):
    """
    Record and process a single note. Supports both regular notes and airbaseSynth.
    
    Args:
        outport: MIDI output port
        note: MIDI note number
        patch: patch configuration
        patch_folder: folder to save files to
        sample_rate: audio sample rate
        audio_device: audio device for recording
        filename: filename for the recorded sample (without .wav extension)
        cc_value: Optional CC value for airbaseSynth (if provided, sends CC before note)
    """
    if cc_value is not None:
        print(f'Playing airbaseSynth: CC={cc_value} -> note {note} ({filename})')
    else:
        print(f'Playing note: {note} ({filename})')

    RECORD_START_BUFFER = 0.5  # Buffer time before recording starts (to ensure MIDI is sent)
    # Calculate total recording time (note duration + note_gap)
    record_duration = patch['note_duration'] + patch['note_gap'] + RECORD_START_BUFFER
    
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
    
    try:
        print(f"  🎤 Starting recording: {record_duration:.1f}s, {channels}ch, {sample_rate}Hz, device={audio_device}")
        
        # Start recording (simplified approach like the working earlier version)
        recording = sd.rec(int(record_duration * sample_rate), 
                         samplerate=sample_rate, channels=channels, 
                         dtype='float64', device=audio_device)
        
        print(f"  📡 Recording started, sending MIDI...")
        
        # always have silence before
        time.sleep(RECORD_START_BUFFER)
        
        # Send CC message first if this is airbaseSynth
        if cc_value is not None:
            control_cc = patch.get('control_cc', 101)
            send_control_change(outport, control_cc, cc_value, patch['midi_channel'])
            print(f"  🎛️  Sent CC {control_cc} = {cc_value} on channel {patch['midi_channel']}")
            # Airbase synth needs more time to process CC messages
            time.sleep(0.5)
        
        # Send MIDI note ON
        print(f"  🎹 Sending MIDI Note ON: {note} vel={patch['velocity']} ch={patch['midi_channel']}")
        send_note_on(outport, note, patch['velocity'], patch['midi_channel'])

        # Wait for note duration (simplified - no chunking to avoid complexity)
        print(f"  ⏳ MIDI Note ON sent - Waiting {patch['note_duration']}s for note duration...")
        time.sleep(patch['note_duration'])

        # Send MIDI note OFF
        send_note_off(outport, note, patch['midi_channel'])
        print(f"  🎹 Note duration completed - Sent MIDI Note OFF: {note} ch={patch['midi_channel']}")
        
        # Wait for the recording to complete (like earlier version - no sd.wait(), just calculated time)
        remaining_time = patch['note_gap']  # Just wait for the reverb tail
        if remaining_time > 0:
            print(f"  ⏳ Waiting  {remaining_time:.1f}s for release tail...")
            time.sleep(remaining_time)
        
        print(f"  ✅ Recording time completed")
        
        # Improved audio cleanup for stability
        try:
            sd.stop()  # Stop current recording stream
            time.sleep(0.2)  # Give more time for cleanup
            
            # Force garbage collection to free audio buffers
            import gc
            gc.collect()
            time.sleep(0.1)
        except Exception as cleanup_error:
            print(f"  ⚠️  Audio cleanup warning: {cleanup_error}")
        
        # Check for clipping in the recorded audio
        wav_filename = f"{filename}.wav"
        check_for_clipping(recording, wav_filename, patch['name'])
        
        # Save the audio file
        filepath = os.path.join(patch_folder, wav_filename)
        shape = save_audio(recording, filepath, sample_rate)
        print(f"  Saved: {filepath} ({shape})")
        
        # Longer delay for airbaseSynth to prevent hangs
        if cc_value is not None:
            time.sleep(0.3)  # Extra time for airbaseSynth cleanup
        else:
            time.sleep(0.1)  # Small delay before next note for regular patches
        return True
        
    except Exception as e:
        if cc_value is not None:
            print(f"  ❌ ERROR recording airbaseSynth (CC={cc_value}): {e}")
        else:
            print(f"  ❌ ERROR recording note {note}: {e}")
        

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


def play_patch(outport, patch, sample_rate=44100, audio_device=None, patches_list=None, patches_filename=None):
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
    if patch.get('type') == 'airbase':
        # For Airbase: use LSB value directly as bank number (0-7)
        # The bank_lsb in patch should be the CC32 value (0,1,2,3,4,5,6,7)
        airbase_bank = patch['bank_lsb']
        print(f"Airbase bank selection: CC32={airbase_bank}")
        send_airbase_bank_select(outport, airbase_bank, patch['midi_channel'])
    else:
        # Standard MIDI bank selection
        send_bank_select(outport, patch['bank_msb'], patch['bank_lsb'], patch['midi_channel'])
    
    send_program_change(outport, patch['program_change'], patch['midi_channel'])
    time.sleep(1)  # Delay for bank/program change to take effect
    
    # Play the notes
    failed_notes = []
    total_notes = 0
    
    if patch.get('type') == 'airbaseSynth':
        # Airbase Synth patch: send CC values with fixed trigger note
        print(f"Airbase Synth patch with {len(patch['cc_to_note_mapping'])} notes using CC {patch['control_cc']}")
        trigger_note = patch['trigger_note']
        
        # Iterate through cc_to_note_mapping (CC value -> MIDI note value)
        for cc_str, midi_note_value in patch['cc_to_note_mapping'].items():
            cc_value = int(cc_str)
            
            # Generate filename using MIDI note value and proper note name (consistent with regular patches)
            note_name = midi_note_to_name(midi_note_value)
            safe_note_name = safe_filename(note_name)
            filename = f"{midi_note_value}_{safe_note_name}"
            total_notes += 1
            
            # Record with CC value and trigger note
            success = record_and_process_note(outport, trigger_note, patch, patch_folder, sample_rate, 
                                            audio_device, filename, cc_value=cc_value)
            if not success:
                failed_notes.append(midi_note_value)
                
    elif 'notes' in patch:
        # Drum patch: play specific notes from the notes dictionary
        print(f"Drum patch with {len(patch['notes'])} specific notes")
        for note_str, drum_name in patch['notes'].items():
            note = int(note_str)
            
            # Exception for airbase hihat MIDI note numbers: use 41 in filename but play original note
            filename_note = 41 if note == 43 else note
            
            safe_drum_name = safe_filename(drum_name)
            filename = f"{filename_note}_{safe_drum_name}_{patch['name']}"
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
    
    # Mark patch as successfully recorded if we have the patches list and filename
    # Only mark as skip if recording was successful (some failures are acceptable)
    recording_success_rate = (total_notes - len(failed_notes)) / total_notes if total_notes > 0 else 0.0
    
    if patches_list is not None and patches_filename is not None and recording_success_rate >= 0.5:  # At least 50% success
        # Find and update this patch in the patches list
        for i, p in enumerate(patches_list):
            if p.get('name') == patch['name']:
                patches_list[i]['skip'] = True
                print(f"  ✅ Marked patch '{patch['name']}' as skip=true (success rate: {recording_success_rate:.1%})")
                
                # Save the updated patches file
                if save_patches(patches_list, patches_filename):
                    print(f"  💾 Updated {patches_filename}")
                else:
                    print(f"  ⚠️  Failed to save {patches_filename}")
                break
    elif recording_success_rate < 0.5:
        print(f"  ⚠️  Patch '{patch['name']}' not marked as complete due to low success rate ({recording_success_rate:.1%})")
    
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


def record_all_patches(patches, midi_port_name, sample_rate=44100, audio_device=None, patches_filename=None):
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
                
                play_patch(outport, patch, sample_rate, audio_device, patches, patches_filename)
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


 