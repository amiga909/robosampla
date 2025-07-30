"""
Patch management utilities for loading and handling synthesizer patches.
"""
import json
import os
import re
from config import OUTPUT_DIR, DEFAULT_MIDI_CHANNEL, DEFAULT_BANK_MSB, DEFAULT_BANK_LSB, DEFAULT_VELOCITY

DRUM_MAPPING_FILE = '_drum_mapping.json'


def load_drum_mappings(filename=DRUM_MAPPING_FILE):
    """Load drum mappings from JSON file."""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: {filename} not found. Drum mappings will not be available.")
        return {}
    except json.JSONDecodeError as e:
        print(f"Error parsing {filename}: {e}")
        return {}


def apply_drum_mapping(patch, drum_mappings):
    """Apply drum mapping to a patch if it has a type field."""
    if 'type' in patch and patch['type'] in drum_mappings:
        mapping = drum_mappings[patch['type']]
        
        # Handle special airbaseSynth type
        if patch['type'] == 'airbaseSynth':
            # Set up airbaseSynth specific parameters
            patch['trigger_note'] = mapping.get('trigger_note', 36)
            patch['control_cc'] = mapping.get('control_cc', 101)
            patch['cc_to_note_mapping'] = mapping.get('cc_to_note_mapping', {})
            patch['notes'] = mapping.get('notes', {})
            print(f"Applied {patch['type']} synth mapping: trigger note {patch['trigger_note']}, CC {patch['control_cc']}, {len(patch['notes'])} notes")
        else:
            # Handle regular drum mappings
            if 'notes' in mapping:
                patch['notes'] = mapping['notes']
                print(f"Applied {patch['type']} drum mapping: {len(patch['notes'])} notes")
            else:
                print(f"Warning: No notes found in {patch['type']} mapping")
    return patch


def load_patches(filename='patches.json'):
    """Load patches from a JSON file and apply default values for missing parameters."""
    try:
        with open(filename, 'r') as f:
            patches = json.load(f)
        
        # Load drum mappings
        drum_mappings = load_drum_mappings()
        
        # Apply default values for missing MIDI parameters and drum mappings
        for patch in patches:
            # Apply drum mapping if patch has a type
            patch = apply_drum_mapping(patch, drum_mappings)
            
            # Apply default MIDI parameters
            patch.setdefault('midi_channel', DEFAULT_MIDI_CHANNEL)
            patch.setdefault('bank_msb', DEFAULT_BANK_MSB)
            patch.setdefault('bank_lsb', DEFAULT_BANK_LSB)
            patch.setdefault('velocity', DEFAULT_VELOCITY)
            
            # Apply default mono setting (default is stereo recording)
            patch.setdefault('mono', False)
        
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
            "velocity": DEFAULT_VELOCITY,
            "mono": False
        }]


def save_patches(patches, filename='patches.json'):
    """Save patches to a JSON file."""
    try:
        with open(filename, 'w') as f:
            json.dump(patches, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving patches to {filename}: {e}")
        return False


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
