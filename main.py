#!/usr/bin/env python3
"""
RoboSampla - Automated synthesizer sampler
Main application entry point.
"""
import sys
import os

# Test and load configuration
from config_loader import (
    MIDI_PORT_NAME, SAMPLE_RATE, AUDIO_DEVICE, PATCHES_FILE,
    SILENCE_THRESHOLD_DB, FADE_IN_MS, FADE_OUT_MS, TARGET_PEAK_DB,
    run_setup_if_needed
)
from patch_utils import load_patches
from midi_utils import list_midi_ports
from audio_utils import list_audio_devices
from recorder import record_all_patches
 

def main():
    """Main application function."""
    import signal
    import sys
    
    def timeout_handler(signum, frame):
        print("\n⚠️  APPLICATION TIMEOUT - The recording process appears to be stuck.")
        print("This might be due to:")
        print("  • Audio device issues")
        print("  • MIDI device problems") 
        print("  • System resource constraints")
        print("\nTry:")
        print("  • Restarting the application")
        print("  • Checking audio/MIDI device connections")
        print("  • Running setup.py to reconfigure devices")
        sys.exit(1)
    
    # Set up a global timeout (30 minutes)
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(1800)  # 30 minutes timeout
    
    print("=== RoboSampla - Automated Synthesizer Sampler ===\n")
    
    try:
        # Test configuration and run setup if needed
        if not run_setup_if_needed():
            print("Configuration setup failed. Exiting.")
            sys.exit(1)
       
        # Show available devices
        list_midi_ports()
        list_audio_devices()
        
        # Load patches
        patches = load_patches(PATCHES_FILE)
        
        # Start recording (audio recording is always enabled)
        success = record_all_patches(
            patches=patches,
            midi_port_name=MIDI_PORT_NAME,
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
        
    finally:
        # Cancel the timeout alarm
        signal.alarm(0)


if __name__ == '__main__':
    main()
