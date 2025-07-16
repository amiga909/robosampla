"""
Patch management utilities for loading and handling synthesizer patches.
"""
import json
import os
import re
from config import OUTPUT_DIR


def load_patches(filename='patches.json'):
    """Load patches from a JSON file."""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"{filename} not found. Using default patch.")
        return [{
            "name": "Default",
            "from_note": 60,
            "to_note": 72,
            "note_gap": 0.1,
            "note_duration": 1.0,
            "program_change": 0,
            "bank_msb": 0,
            "bank_lsb": 0,
            "velocity": 100
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
