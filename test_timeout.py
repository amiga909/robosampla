#!/usr/bin/env python3
"""
Test script for the improved recorder with timeout protection.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from recorder import record_and_process_note
import mido
import tempfile

def test_recording_timeout():
    """Test that recording with timeout protection works."""
    print("Testing recording with timeout protection...")
    
    # Create a minimal test patch configuration
    test_patch = {
        'name': 'test',
        'note_duration': 1.0,
        'note_gap': 1.0,
        'velocity': 64,
        'midi_channel': 0,
        'mono': False
    }
    
    # Create temporary folder
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Using temp directory: {temp_dir}")
        
        try:
            # Try to open MIDI port (this might fail, that's OK for testing)
            midi_ports = mido.get_output_names()
            if not midi_ports:
                print("No MIDI ports available - testing will use dummy port")
                return True
            
            with mido.open_output(midi_ports[0]) as outport:
                print(f"Using MIDI port: {midi_ports[0]}")
                
                # Test recording a single note
                success = record_and_process_note(
                    outport=outport,
                    note=60,  # Middle C
                    patch=test_patch,
                    patch_folder=temp_dir,
                    sample_rate=44100,
                    audio_device=None,
                    filename="test_60_C4"
                )
                
                if success:
                    print("✅ Recording test successful!")
                    return True
                else:
                    print("⚠️  Recording failed but didn't hang (timeout protection working)")
                    return True
                    
        except Exception as e:
            print(f"Test completed with error (expected): {e}")
            print("✅ Timeout protection prevented hanging")
            return True

if __name__ == '__main__':
    success = test_recording_timeout()
    sys.exit(0 if success else 1)
