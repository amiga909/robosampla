"""
MIDI utility functions for sending MIDI messages.
"""
import mido
import time


def send_note_on(outport, note, velocity=100, channel=0):
    """Send a MIDI note on message."""
    msg = mido.Message('note_on', note=note, velocity=velocity, channel=channel)
    outport.send(msg)


def send_note_off(outport, note, channel=0):
    """Send a MIDI note off message."""
    msg = mido.Message('note_off', note=note, velocity=0, channel=channel)
    outport.send(msg)


def send_program_change(outport, program, channel=0):
    """Send a MIDI program change message."""
    msg = mido.Message('program_change', program=program, channel=channel)
    outport.send(msg)


def send_bank_select(outport, bank_msb, bank_lsb, channel=0):
    """Send MIDI bank select messages (MSB and LSB)."""
    # Send Bank Select MSB (CC 0)
    msb_msg = mido.Message('control_change', control=0, value=bank_msb, channel=channel)
    outport.send(msb_msg)
    # Send Bank Select LSB (CC 32)
    lsb_msg = mido.Message('control_change', control=32, value=bank_lsb, channel=channel)
    outport.send(lsb_msg)


def list_midi_ports():
    """List all available MIDI input and output ports."""
    print("Available MIDI Output Ports:")
    for port in mido.get_output_names():
        print(f"  - {port}")

    print("\nAvailable MIDI Input Ports:")
    for port in mido.get_input_names():
        print(f"  - {port}")


def midi_note_to_name(midi_note):
    """Convert MIDI note number to note name (e.g., 60 -> C4)."""
    note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    octave = (midi_note // 12) - 1
    note = note_names[midi_note % 12]
    return f"{note}{octave}"
