#!/usr/bin/env python3
"""
Program Change Sender - Send MIDI program changes interactively
Usage: python program_change.py [program_number] [channel]
"""
import sys
import argparse
import mido
from config import MIDI_PORT_NAME
from midi_utils import send_program_change, list_midi_ports


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


def main():
    """Main function with command line argument parsing."""
    parser = argparse.ArgumentParser(
        description="Send MIDI program changes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python program_change.py                    # Interactive mode
  python program_change.py 42                # Send program 42 on channel 0
  python program_change.py 42 1              # Send program 42 on channel 1
  python program_change.py --list            # List MIDI ports
        """
    )
    
    parser.add_argument('program', nargs='?', type=int, 
                       help='Program number (0-127)')
    parser.add_argument('channel', nargs='?', type=int, default=0,
                       help='MIDI channel (0-15, default: 0)')
    parser.add_argument('--list', action='store_true',
                       help='List available MIDI ports and exit')
    parser.add_argument('--interactive', '-i', action='store_true',
                       help='Force interactive mode')
    
    args = parser.parse_args()
    
    # Handle list option
    if args.list:
        list_midi_ports()
        return
    
    # Validate arguments
    if args.program is not None:
        if not 0 <= args.program <= 127:
            print("Error: Program number must be between 0-127")
            sys.exit(1)
        if not 0 <= args.channel <= 15:
            print("Error: Channel must be between 0-15")
            sys.exit(1)
    
    # Determine mode
    if args.program is not None and not args.interactive:
        # Single program change mode
        success = send_program_once(args.program, args.channel)
        sys.exit(0 if success else 1)
    else:
        # Interactive mode
        success = send_program_interactive()
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
