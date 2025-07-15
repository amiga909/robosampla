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
import sounddevice as sd


def play_patch(outport, patch, record_audio_flag=False, sample_rate=44100, audio_device=None):
    """Play a single patch configuration and optionally record audio."""
    print(f"\nPlaying patch: {patch['name']}")
    print(f"Note range: {patch['from_note']} - {patch['to_note']}")
    print(f"Program: {patch['program_change']}")
    print(f"Bank MSB: {patch['bank_msb']}, Bank LSB: {patch['bank_lsb']}")
    
    # Create folder for this patch if recording
    patch_folder = None
    if record_audio_flag:
        patch_folder = create_patch_folder(patch['name'])
        print(f"Recording audio to folder: {patch_folder}")
    
    # Set up the patch
    send_bank_select(outport, patch['bank_msb'], patch['bank_lsb'], patch['midi_channel'])
    send_program_change(outport, patch['program_change'], patch['midi_channel'])
    time.sleep(0.1)  # Small delay for bank/program change to take effect
    
    # Play the notes
    for note in range(patch['from_note'], patch['to_note'] + 1):
        note_name = midi_note_to_name(note)
        print(f'Playing note: {note} ({note_name})')
        
        recording = None
        if record_audio_flag:
            # Calculate total recording time (note duration + small buffer)
            record_duration = patch['note_duration'] + 0.2  # Extra 200ms buffer
            
            # Get device info to determine available channels
            channels = get_device_channels(audio_device)
            
            # Start recording
            recording = sd.rec(int(record_duration * sample_rate), 
                             samplerate=sample_rate, channels=channels, 
                             dtype='float64', device=audio_device)
            
            # Small delay to ensure recording starts before MIDI
            time.sleep(0.05)
        
        # Send MIDI note
        send_note_on(outport, note, patch['velocity'], patch['midi_channel'])
        time.sleep(patch['note_duration'])
        send_note_off(outport, note, patch['midi_channel'])

        if record_audio_flag and recording is not None:
            # Wait for recording to finish
            sd.wait()
            
            # Save the audio file
            safe_note_name = safe_filename(note_name)
            filename = f"{safe_note_name}_{note}.wav"
            filepath = os.path.join(patch_folder, filename)
            
            # Save the recording
            shape = save_audio(recording, filepath, sample_rate)
            print(f"  Saved: {filepath} ({shape})")
        
        time.sleep(patch['note_gap'])


def record_all_patches(patches, midi_port_name, record_audio=True, sample_rate=44100, audio_device=None):
    """Record all patches with MIDI and optional audio recording."""
    if not patches:
        print("No patches found!")
        return False
        
    print(f"Loaded {len(patches)} patches")
    
    if record_audio:
        print("Audio recording enabled. Files will be saved in patch-specific folders.")
    else:
        print("Audio recording disabled. Playing MIDI only.")
    
    try:
        with mido.open_output(midi_port_name) as outport:
            for i, patch in enumerate(patches):
                print(f"\n--- Playing patch {i+1}/{len(patches)} ---")
                play_patch(outport, patch, record_audio, sample_rate, audio_device)
                
                # Add a pause between patches
                if i < len(patches) - 1:
                    print("\nPause between patches...")
                    time.sleep(2.0)
        return True
                    
    except OSError as e:
        print(f"Error opening MIDI port '{midi_port_name}': {e}")
        return False
