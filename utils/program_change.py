#!/usr/bin/env python3
"""
Program Change Sender - Send MIDI program changes interactively
Usage: python program_change.py [program_number] [channel]
"""
import sys
import argparse
import time
import os
import mido

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config_loader import MIDI_PORT_NAME, run_setup_if_needed
from midi_utils import send_program_change, send_note_on, send_note_off, list_midi_ports, midi_note_to_name


def send_program_interactive():
    """Interactive mode for sending program changes."""
    print("=== Interactive Program Change Sender ===")
    print(f"Connected to MIDI port: {MIDI_PORT_NAME}")
    print("Commands:")
    print("  - Enter program number (0-127)")
    print("  - Enter 'q' or 'quit' to exit")
    print("  - Enter 'list' to show available MIDI ports")
    print("  - Format: 'program [channel]' (channel is optional, default 0)")
    print()
    
    try:
        with mido.open_output(MIDI_PORT_NAME) as outport:
            while True:
                try:
                    user_input = input("Program Change> ").strip().lower()
                    
                    if user_input in ['q', 'quit', 'exit']:
                        print("Goodbye!")
                        break
                    elif user_input == 'list':
                        list_midi_ports()
                        continue
                    elif user_input == 'help':
                        print("Enter program number (0-127) or 'program channel' format")
                        print("Example: '42' or '42 1' for program 42 on channel 1")
                        continue
                    
                    # Parse input
                    parts = user_input.split()
                    if len(parts) == 0:
                        continue
                    
                    try:
                        program = int(parts[0])
                        channel = int(parts[1]) if len(parts) > 1 else 0
                        
                        if not 0 <= program <= 127:
                            print("Error: Program number must be between 0-127")
                            continue
                        if not 0 <= channel <= 15:
                            print("Error: Channel must be between 0-15")
                            continue
                        
                        send_program_change(outport, program, channel)
                        print(f"Sent: Program Change {program} on channel {channel}")
                        
                    except ValueError:
                        print("Error: Invalid input. Enter a number (0-127) or 'help' for usage")
                        
                except KeyboardInterrupt:
                    print("\nGoodbye!")
                    break
                except EOFError:
                    print("\nGoodbye!")
                    break
                    
    except OSError as e:
        print(f"Error opening MIDI port '{MIDI_PORT_NAME}': {e}")
        print("\nAvailable MIDI ports:")
        list_midi_ports()
        return False
    
    return True


def send_program_once(program, channel=0):
    """Send a single program change and exit."""
    try:
        with mido.open_output(MIDI_PORT_NAME) as outport:
            send_program_change(outport, program, channel)
            print(f"Sent: Program Change {program} on channel {channel}")
            return True
    except OSError as e:
        print(f"Error opening MIDI port '{MIDI_PORT_NAME}': {e}")
        print("\nAvailable MIDI ports:")
        list_midi_ports()
        return False


def send_note_sequence():
    """Send note sequence: Hardcoded dictionary of specific notes."""
    try:
        with mido.open_output(MIDI_PORT_NAME) as outport:
            print(f"Sending note sequence on MIDI port: {MIDI_PORT_NAME}")
          
            # Hardcoded note sequence with note numbers and names
            notes = {
                0: "C-1",
                3: "D#-1",
                6: "F#-1", 
                12: "C0",
                18: "F#0",
                24: "C1",
                30: "F#1",
                36: "C2",
                96: "C7",
                103: "G7",
                108: "C8",
                111: "D8",
                116: "E8",
                120: "C9",
                127: "G9"
            }
            
            print(f"Playing {len(notes)} notes: {list(notes.keys())}")
            
            for note_num, note_name in notes.items():
                print(f"Playing note {note_num} ({note_name})")
                
                # Send note on
                send_note_on(outport, note_num, 100, 0)  # velocity 100, channel 0
                time.sleep(2.0)   

                # Send note off
                send_note_off(outport, note_num, 0)
                time.sleep(0.5)  # 0.5 second interval between notes
            
            print("Note sequence completed!")
            return True
            
    except OSError as e:
        print(f"Error opening MIDI port '{MIDI_PORT_NAME}': {e}")
        print("\nAvailable MIDI ports:")
        list_midi_ports()
        return False
    except KeyboardInterrupt:
        print("\nNote sequence interrupted by user")
        return False


def main():
    """Main function with command line argument parsing."""
    # Test configuration and run setup if needed
    if not run_setup_if_needed():
        print("Configuration setup failed. Exiting.")
        sys.exit(1)
    
    parser = argparse.ArgumentParser(
        description="Send MIDI program change and play note sequence",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python program_change.py 42                # Send program 42 on channel 0, then play notes
  python program_change.py 42 1              # Send program 42 on channel 1, then play notes
  python program_change.py --list            # List MIDI ports
        """
    )
    
    parser.add_argument('program', type=int, 
                       help='Program number (0-127) - required')
    parser.add_argument('channel', nargs='?', type=int, default=0,
                       help='MIDI channel (0-15, default: 0)')
    parser.add_argument('--list', action='store_true',
                       help='List available MIDI ports and exit')
    
    args = parser.parse_args()
    
    # Handle list option
    if args.list:
        list_midi_ports()
        return
    
    # Validate arguments
    if not 0 <= args.program <= 127:
        print("Error: Program number must be between 0-127")
        sys.exit(1)
    if not 0 <= args.channel <= 15:
        print("Error: Channel must be between 0-15")
        sys.exit(1)
    
    # Send program change first
    print(f"Sending Program Change {args.program} on channel {args.channel}...")
    success = send_program_once(args.program, args.channel)
    if not success:
        sys.exit(1)
    
    # Always run note sequence after program change
    print("\nStarting note sequence...")
    time.sleep(3.0)  # Pause between program change and notes
    success = send_note_sequence()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
