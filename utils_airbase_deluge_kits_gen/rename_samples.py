#!/usr/bin/env python3
"""
Sample File Renamer
Standardizes Airbase sample filenames to use consistent 1-10 numbering pattern.
Handles various MIDI note numbers and naming conventions.
"""

import os
from pathlib import Path
import re
import shutil


def get_standard_mapping():
    """
    Get mapping from various drum types and MIDI notes to standard numbering.
    Returns dict mapping patterns to standard numbers.
    """
    return {
        # Standard GM drum mapping
        36: "1_Kick",           # Bass Drum 1
        35: "1_Kick",           # Bass Drum 2 (alternative)
        38: "2_Snare",          # Acoustic Snare
        40: "2_Snare",          # Electric Snare (alternative)
        41: "3_LoTom",          # Low Floor Tom
        43: "3_LoTom",          # High Floor Tom (alternative)
        45: "4_HiTom",          # Low Tom
        47: "4_HiTom",          # Low-Mid Tom (alternative)
        48: "4_HiTom",          # Hi-Mid Tom (alternative)
        50: "4_HiTom",          # High Tom (alternative)
        42: "5_ClosedHiHat",    # Closed Hi-Hat
        44: "5_ClosedHiHat",    # Pedal Hi-Hat (alternative)
        46: "6_OpenHiHat",      # Open Hi-Hat
        39: "7_Clap",           # Hand Clap
        37: "8_Rim_Shot",       # Side Stick/Rim Shot
        49: "9_Crash",          # Crash Cymbal 1
        57: "9_Crash",          # Crash Cymbal 2 (alternative)
        51: "10_Ride",          # Ride Cymbal 1
        53: "10_Ride",          # Ride Bell (alternative)
        59: "10_Ride",          # Ride Cymbal 2 (alternative)
        52: "10_Ride",          # Chinese Cymbal (alternative)
        
        # Additional mappings for non-standard numbers
        11: "5_ClosedHiHat",    # Sometimes used for hi-hat
        
        # Handle PedalHiHat as ClosedHiHat
        "PedalHiHat": "5_ClosedHiHat",
    }


def is_already_standard_format(filename):
    """
    Check if filename is already in the standard 1-10 format.
    Returns True if it matches the pattern N_Type_PatchName.wav
    """
    # Pattern: number (1-10) + underscore + drum type + underscore + patch name + .wav
    pattern = r'^(1_Kick|2_Snare|3_LoTom|4_HiTom|5_ClosedHiHat|6_OpenHiHat|7_Clap|8_Rim_Shot|9_Crash|10_Ride)_[^_]+\.wav$'
    return bool(re.match(pattern, filename))


def detect_sample_type_from_name(filename):
    """
    Detect drum type from filename for NON-STANDARD files only.
    Only works on files that clearly need renaming (MIDI numbers or special names).
    Returns the standard type name or None if not recognized.
    """
    # Don't process files that are already in standard format
    if is_already_standard_format(filename):
        return None
    
    filename_lower = filename.lower()
    
    # Only look for very specific patterns that clearly indicate the drum type
    # and are NOT already in standard format
    type_patterns = {
        "5_ClosedHiHat": ["pedalhihat", "pedal_hihat"],  # Only PedalHiHat -> ClosedHiHat
    }
    
    for standard_type, patterns in type_patterns.items():
        for pattern in patterns:
            if pattern in filename_lower:
                return standard_type
    
    return None


def find_samples_to_rename(patch_dir):
    """
    Find all WAV files in a patch directory and determine their renaming.
    Only renames files that clearly need it (MIDI numbers or special cases).
    Returns list of (old_path, new_filename) tuples.
    """
    renaming_list = []
    mapping = get_standard_mapping()
    
    for file_path in patch_dir.glob("*.wav"):
        filename = file_path.name
        
        # Skip files that are already in standard format
        if is_already_standard_format(filename):
            continue
        
        # Extract patch name from filename (everything after the last underscore before .wav)
        match = re.search(r'_([^_]+)\.wav$', filename)
        if not match:
            print(f"    ⚠️  Cannot extract patch name from: {filename}")
            continue
            
        patch_name = match.group(1)
        
        # Only process files with MIDI note numbers at the start
        midi_match = re.match(r'^(\d+)_', filename)
        if midi_match:
            midi_note = int(midi_match.group(1))
            # Only rename if it's a known MIDI mapping and not already standard (1-10)
            if midi_note in mapping and midi_note not in range(1, 11):
                new_filename = f"{mapping[midi_note]}_{patch_name}.wav"
                if new_filename != filename:
                    renaming_list.append((file_path, new_filename))
                continue
        
        # Handle special cases like PedalHiHat
        detected_type = detect_sample_type_from_name(filename)
        if detected_type:
            new_filename = f"{detected_type}_{patch_name}.wav"
            if new_filename != filename:
                renaming_list.append((file_path, new_filename))
            continue
        
        # Only warn about files that look like they might need renaming
        if re.match(r'^\d+_', filename) and not is_already_standard_format(filename):
            print(f"    ❓ Unknown MIDI note number in: {filename}")
    
    return renaming_list


def rename_samples_in_patch(patch_dir, dry_run=True):
    """
    Rename samples in a single patch directory.
    
    Args:
        patch_dir: Path to patch directory
        dry_run: If True, only show what would be renamed
        
    Returns:
        Number of files that would be/were renamed
    """
    renaming_list = find_samples_to_rename(patch_dir)
    
    if not renaming_list:
        print(f"  ✓ No renaming needed")
        return 0
    
    for old_path, new_filename in renaming_list:
        new_path = old_path.parent / new_filename
        
        if dry_run:
            print(f"  → Would rename: {old_path.name} → {new_filename}")
        else:
            try:
                # Check if target already exists
                if new_path.exists():
                    print(f"  ⚠️  Target exists, skipping: {old_path.name} → {new_filename}")
                    continue
                    
                old_path.rename(new_path)
                print(f"  ✓ Renamed: {old_path.name} → {new_filename}")
            except Exception as e:
                print(f"  ❌ Error renaming {old_path.name}: {e}")
    
    return len(renaming_list)


def main():
    """Main function to process all patches."""
    # Current directory where this script file is located
    current_dir = Path(__file__).parent
    
    # Parent directory (one level up from current script)
    parent_dir = Path(__file__).parent.parent
    
    processed_dir = parent_dir / "_output_Jomox" / "_processed"
    
    # Check if processed directory exists
    if not processed_dir.exists():
        print(f"❌ Processed directory not found: {processed_dir}")
        return
    
    print(f"🔄 Sample File Renamer")
    print(f"📂 Input: {processed_dir}")
    print()
    
    # Get all patch directories (exclude _incomplete_ folders and files)
    patch_dirs = []
    for item in processed_dir.iterdir():
        if item.is_dir() and not item.name.startswith('_incomplete_') and not item.name.startswith('.'):
            patch_dirs.append(item)
    
    if not patch_dirs:
        print("❌ No patch directories found")
        return
    
    print(f"Found {len(patch_dirs)} patch directories")
    print()
    
    # First pass: dry run to show what would be renamed
    print("🔍 Checking what files need renaming...")
    print()
    
    total_renames = 0
    patches_with_renames = 0
    
    for patch_dir in sorted(patch_dirs):
        patch_name = patch_dir.name
        print(f"📁 Checking: {patch_name}")
        
        try:
            rename_count = rename_samples_in_patch(patch_dir, dry_run=True)
            if rename_count > 0:
                patches_with_renames += 1
                total_renames += rename_count
        except Exception as e:
            print(f"  ❌ Error checking {patch_name}: {e}")
        
        print()
    
    if total_renames == 0:
        print("✅ No files need renaming!")
        return
    
    print(f"📊 Summary:")
    print(f"   Patches needing renames: {patches_with_renames}")
    print(f"   Total files to rename: {total_renames}")
    print()
    
    # Ask for confirmation
    response = input("Proceed with renaming? (y/N): ").strip().lower()
    if response not in ['y', 'yes']:
        print("Cancelled.")
        return
    
    # Second pass: actual renaming
    print()
    print("🔄 Renaming files...")
    print()
    
    actual_renames = 0
    
    for patch_dir in sorted(patch_dirs):
        patch_name = patch_dir.name
        print(f"📁 Processing: {patch_name}")
        
        try:
            rename_count = rename_samples_in_patch(patch_dir, dry_run=False)
            actual_renames += rename_count
        except Exception as e:
            print(f"  ❌ Error processing {patch_name}: {e}")
        
        print()
    
    print(f"✅ Complete!")
    print(f"   Files renamed: {actual_renames}")


if __name__ == "__main__":
    main()
