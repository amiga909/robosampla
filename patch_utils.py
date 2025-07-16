"""
Patch management utilities for loading and handling synthesizer patches.
"""
import json
import os
import re
from config import OUTPUT_DIR, DEFAULT_MIDI_CHANNEL, DEFAULT_BANK_MSB, DEFAULT_BANK_LSB, DEFAULT_VELOCITY


def load_patches(filename='patches.json'):
    """Load patches from a JSON file and apply default values for missing parameters."""
    try:
        with open(filename, 'r') as f:
            patches = json.load(f)
        
        # Apply default values for missing MIDI parameters
        for patch in patches:
            patch.setdefault('midi_channel', DEFAULT_MIDI_CHANNEL)
            patch.setdefault('bank_msb', DEFAULT_BANK_MSB)
            patch.setdefault('bank_lsb', DEFAULT_BANK_LSB)
            patch.setdefault('velocity', DEFAULT_VELOCITY)
        
        return patches
    except FileNotFoundError:
        print(f"{filename} not found. Using default patch.")
        return [{
            "name": "Default",
            "from_note": 60,
            "to_note": 72,
            "note_gap": 0.1,
            "note_duration": 1.0,
            "program_change": 0,
            "midi_channel": DEFAULT_MIDI_CHANNEL,
            "bank_msb": DEFAULT_BANK_MSB,
            "bank_lsb": DEFAULT_BANK_LSB,
            "velocity": DEFAULT_VELOCITY
        }]


def safe_filename(name):
    """Create a safe filename by removing/replacing problematic characters."""
    # Replace # with 'sharp' and remove other problematic characters
    safe_name = name.replace('#', 'sharp')
    safe_name = re.sub(r'[<>:"/\\|?*]', '', safe_name)
    return safe_name


def create_patch_folder(patch_name):
    """Create a folder for a patch if it doesn't exist."""
    folder_name = safe_filename(patch_name)
    full_path = os.path.join(OUTPUT_DIR, folder_name)
    os.makedirs(full_path, exist_ok=True)
    return full_path
