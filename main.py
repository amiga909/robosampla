#!/usr/bin/env python3
"""
RoboSampla - Automated synthesizer sampler
Main application entry point.
"""
import sys
from config import (
    MIDI_PORT_NAME, SAMPLE_RATE, AUDIO_DEVICE, PATCHES_FILE,
    SILENCE_THRESHOLD_DB, FADE_IN_MS, FADE_OUT_MS, TARGET_PEAK_DB
)
from patch_utils import load_patches
from midi_utils import list_midi_ports
from audio_utils import list_audio_devices
from recorder import record_all_patches
 

def main():
    """Main application function."""
    print("=== RoboSampla - Automated Synthesizer Sampler ===\n")
   
    # Show available devices
    list_midi_ports()
    list_audio_devices()
    
    # Load patches
    patches = load_patches(PATCHES_FILE)
    
    # Ask user if they want to record audio (or set to True for auto-recording)
    record_audio_flag = True  # input("Do you want to record audio? (y/n): ").lower().startswith('y')
    
    # Start recording
    success = record_all_patches(
        patches=patches,
        midi_port_name=MIDI_PORT_NAME,
        record_audio=record_audio_flag,
        sample_rate=SAMPLE_RATE,
        audio_device=AUDIO_DEVICE
    )
    
    if not success:
        print("\nRecording failed. Please check your MIDI port configuration.")
        print("Available MIDI ports:")
        list_midi_ports()
        print(f"\nCurrent MIDI port setting: '{MIDI_PORT_NAME}'")
        print("Update MIDI_PORT_NAME in config.py with one of the available ports.")
        sys.exit(1)
    
    print("\n=== Recording completed successfully! ===")


if __name__ == '__main__':
    main()
