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
from config import SILENCE_THRESHOLD_DB, FADE_IN_MS, FADE_OUT_MS, TARGET_PEAK_DB
import sounddevice as sd
import numpy as np


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
        print(f"  ⚠️  CLIPPING DETECTED in {filename}")
        print(f"      Peak value: {peak_value:.4f}")
        print(f"      Clipped samples: {clipped_samples}/{total_samples} ({clipping_percentage:.2f}%)")
        return True
    else:
        print(f"  ✓ No clipping detected (peak: {peak_value:.4f})")
        return False


def record_and_process_note(outport, note, patch, patch_folder, sample_rate, audio_device, filename):
    """
    Record and process a single note.
    
    Args:
        outport: MIDI output port
        note: MIDI note number
        patch: patch configuration
        patch_folder: folder to save files to
        sample_rate: audio sample rate
        audio_device: audio device for recording
        filename: filename for the recorded sample (without .wav extension)
    """
    print(f'Playing note: {note} ({filename})')
    
    # Calculate total recording time (note duration + note_gap for reverb tail)
    record_duration = patch['note_duration'] + patch['note_gap']
    
    # Get device info to determine available channels
    channels = get_device_channels(audio_device)
    
    # Start recording
    recording = sd.rec(int(record_duration * sample_rate), 
                     samplerate=sample_rate, channels=channels, 
                     dtype='float64', device=audio_device)
    
    # Small delay to ensure recording starts before MIDI
    time.sleep(0.5)
    
    # Send MIDI note
    send_note_on(outport, note, patch['velocity'], patch['midi_channel'])
    time.sleep(patch['note_duration'])
    send_note_off(outport, note, patch['midi_channel'])

    # Wait for recording to finish
    sd.wait()
    
    # Check for clipping in the recorded audio
    wav_filename = f"{filename}.wav"
    check_for_clipping(recording, wav_filename)
    
    # Save the audio file
    filepath = os.path.join(patch_folder, wav_filename)
    shape = save_audio(recording, filepath, sample_rate)
    print(f"  Saved: {filepath} ({shape})")
    
    # Create unprocessed subfolder and save original
    unprocessed_folder = os.path.join(patch_folder, "unprocessed")
    os.makedirs(unprocessed_folder, exist_ok=True)
    unprocessed_filepath = os.path.join(unprocessed_folder, wav_filename)
    
    # Copy original file to unprocessed folder
    import shutil
    shutil.copy2(filepath, unprocessed_filepath)
    
    # Process the recorded sample (remove silence, add fades)
    print(f"  Processing: {wav_filename}")
    if process_recorded_sample(filepath, sample_rate, 
                             SILENCE_THRESHOLD_DB, FADE_IN_MS, FADE_OUT_MS):
        print(f"  ✓ Processed successfully")
    else:
        print(f"  ✗ Processing failed")
    
    # Small delay to ensure processing is done.   
    time.sleep(0.5)


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
    
    # Create folder for this patch
    patch_folder = create_patch_folder(patch['name'])
    print(f"Recording audio to folder: {patch_folder}")
    
    # Set up the patch
    send_bank_select(outport, patch['bank_msb'], patch['bank_lsb'], patch['midi_channel'])
    send_program_change(outport, patch['program_change'], patch['midi_channel'])
    time.sleep(1)  # Delay for bank/program change to take effect
    
    # Play the notes
    if 'notes' in patch:
        # Drum patch: play specific notes from the notes dictionary
        print(f"Drum patch with {len(patch['notes'])} specific notes")
        for note_str, drum_name in patch['notes'].items():
            note = int(note_str)
            safe_drum_name = safe_filename(drum_name)
            filename = f"{patch['name']}_{safe_drum_name}"
            record_and_process_note(outport, note, patch, patch_folder, sample_rate, audio_device, filename)
    else:
        # Regular patch: play notes from from_note to to_note
        print(f"Record from note {patch['from_note']} to {patch['to_note']}")
        for note in range(patch['from_note'], patch['to_note'] + 1):
            note_name = midi_note_to_name(note)
            safe_note_name = safe_filename(note_name)
            filename = f"{note}_{safe_note_name}"
            record_and_process_note(outport, note, patch, patch_folder, sample_rate, audio_device, filename)
    
    # After all notes in the patch are recorded, normalize the entire patch
    print(f"\nPost-processing patch: {patch['name']}")
    if process_patch_folder(patch_folder, sample_rate, TARGET_PEAK_DB, FADE_IN_MS, FADE_OUT_MS):
        print(f"✓ Patch normalization completed")
    else:
        print(f"✗ Patch normalization failed")
    
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
        
        return True
                    
    except OSError as e:
        print(f"Error opening MIDI port '{midi_port_name}': {e}")
        return False
