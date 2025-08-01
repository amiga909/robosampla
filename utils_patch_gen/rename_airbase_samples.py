#!/usr/bin/env python3
"""
Rename Airbase samples in _processed folders.
Maps GM drum numbers to sequential numbers 1-10.
"""
import os
import glob
import argparse


def get_airbase_mapping():
    """
    Return the mapping from GM drum numbers to sequential numbers.
    Based on the Airbase sample naming convention.
    """
    return {
        36: 1,   # Kick
        40: 2,   # Snare
        41: 3,   # LoTom  
        41: 4,   # HiTom (Note: This creates a conflict - need to handle)
        42: 5,   # ClosedHiHat
        46: 6,   # OpenHiHat
        39: 7,   # Clap
        37: 8,   # Rim
        49: 9,   # Crash
        52: 10,  # Ride
        44: 11,  # PedalHiHat
    }


def get_detailed_airbase_mapping():
    """
    Return a more detailed mapping that handles the instrument names.
    """
    return {
        # Kick
        36: 1,
        # Snare
        40: 2,
        # Toms - need to distinguish by name
        41: {"LoTom": 3, "HiTom": 4},
        # Hi-hats
        42: 5,   # ClosedHiHat
        46: 6,   # OpenHiHat
        44: 11,  # PedalHiHat
        # Percussion
        39: 7,   # Clap
        37: 8,   # Rim Shot
        49: 9,   # Crash
        52: 10,   # Ride
    }


def determine_new_number(filename, old_number):
    """
    Determine the new number based on filename and old GM number.
    Handles special cases like distinguishing between LoTom and HiTom.
    """
    mapping = get_detailed_airbase_mapping()
    
    if old_number in mapping:
        if isinstance(mapping[old_number], dict):
            # Special case for number 41 (LoTom vs HiTom)
            filename_lower = filename.lower()
            if "lotom" in filename_lower:
                return mapping[old_number]["LoTom"]
            elif "hitom" in filename_lower:
                return mapping[old_number]["HiTom"]
            else:
                # Default to LoTom if we can't determine
                print(f"    ⚠️  Could not determine Tom type for {filename}, defaulting to LoTom")
                return mapping[old_number]["LoTom"]
        else:
            return mapping[old_number]
    
    return None


def rename_files_in_folder(folder_path, dry_run=True):
    """
    Rename airbase sample files in a folder.
    
    Args:
        folder_path: Path to folder containing WAV files
        dry_run: If True, only show what would be renamed without actually renaming
    
    Returns:
        List of rename operations performed/planned
    """
    print(f"\n📁 Processing folder: {os.path.basename(folder_path)}")
    
    # Find all WAV files
    wav_files = glob.glob(os.path.join(folder_path, "*.wav"))
    
    if not wav_files:
        print("  No WAV files found")
        return []
    
    # Check if this folder contains airbase samples (look for 36_Kick)
    has_airbase = any("36_Kick" in os.path.basename(f) for f in wav_files)
    
    if not has_airbase:
        print("  No airbase samples detected (no 36_Kick found), skipping")
        return []
    
    print("  ✅ Airbase samples detected!")
    
    rename_operations = []
    
    for wav_file in sorted(wav_files):
        filename = os.path.basename(wav_file)
        
        # Extract the first number from filename
        parts = filename.split('_', 1)
        if len(parts) < 2:
            print(f"    ⚠️  Skipping {filename} - unexpected format")
            continue
        
        try:
            old_number = int(parts[0])
        except ValueError:
            print(f"    ⚠️  Skipping {filename} - first part is not a number")
            continue
        
        # Determine new number
        new_number = determine_new_number(filename, old_number)
        
        if new_number is None:
            print(f"    ⚠️  Skipping {filename} - no mapping for number {old_number}")
            continue
        
        # Create new filename
        new_filename = f"{new_number}_{parts[1]}"
        new_filepath = os.path.join(folder_path, new_filename)
        
        if filename == new_filename:
            print(f"    ⏸️  {filename} (already correct)")
            continue
        
        operation = {
            'old_path': wav_file,
            'new_path': new_filepath,
            'old_filename': filename,
            'new_filename': new_filename,
            'old_number': old_number,
            'new_number': new_number
        }
        
        if dry_run:
            print(f"    🔄 WOULD RENAME: {filename} → {new_filename}")
        else:
            try:
                os.rename(wav_file, new_filepath)
                print(f"    ✅ RENAMED: {filename} → {new_filename}")
            except OSError as e:
                print(f"    ❌ ERROR renaming {filename}: {e}")
                continue
        
        rename_operations.append(operation)
    
    return rename_operations


def process_processed_folder(processed_folder, dry_run=True):
    """
    Process all subfolders in the _processed folder.
    
    Args:
        processed_folder: Path to _processed folder
        dry_run: If True, only show what would be renamed
    
    Returns:
        Dictionary with results per folder
    """
    if not os.path.exists(processed_folder):
        print(f"❌ _processed folder not found: {processed_folder}")
        return {}
    
    print(f"🔍 Scanning for airbase samples in: {processed_folder}")
    
    results = {}
    total_operations = 0
    
    # Find all subdirectories
    subdirs = [d for d in os.listdir(processed_folder) 
               if os.path.isdir(os.path.join(processed_folder, d))]
    
    if not subdirs:
        print("  No subdirectories found")
        return results
    
    for subdir in sorted(subdirs):
        subdir_path = os.path.join(processed_folder, subdir)
        operations = rename_files_in_folder(subdir_path, dry_run)
        
        if operations:
            results[subdir] = operations
            total_operations += len(operations)
    
    print(f"\n📊 SUMMARY:")
    print(f"  Folders processed: {len(subdirs)}")
    print(f"  Folders with airbase samples: {len(results)}")
    print(f"  Total rename operations: {total_operations}")
    
    if dry_run:
        print(f"  📝 DRY RUN MODE - No files were actually renamed")
        print(f"  💡 Run with --execute to perform the renames")
    else:
        print(f"  ✅ All renames completed")
    
    return results


def main():
    parser = argparse.ArgumentParser(description='Rename Airbase samples in _processed folders')
    parser.add_argument('--execute', action='store_true', 
                       help='Actually perform the renames (default is dry run)')
    parser.add_argument('--folder', type=str, default='_processed',
                       help='Path to processed folder (default: _processed)')
    
    args = parser.parse_args()
    
    # Determine the processed folder path
    if os.path.isabs(args.folder):
        processed_folder = args.folder
    else:
        # Relative to current working directory
        processed_folder = os.path.join(os.getcwd(), args.folder)
    
    dry_run = not args.execute
    
    print("🎵 Airbase Sample Renamer")
    print("=" * 40)
    
    if dry_run:
        print("🔍 DRY RUN MODE - No files will be renamed")
    else:
        print("⚡ EXECUTE MODE - Files will be renamed")
    
    print(f"📂 Target folder: {processed_folder}")
    
    # Show the mapping
    print(f"\n🗺️  Airbase Mapping:")
    mapping = get_detailed_airbase_mapping()
    for old_num, new_num in mapping.items():
        if isinstance(new_num, dict):
            for instrument, num in new_num.items():
                print(f"    {old_num} ({instrument}) → {num}")
        else:
            print(f"    {old_num} → {new_num}")
    
    # Process the folder
    results = process_processed_folder(processed_folder, dry_run)
    
    if results and dry_run:
        print(f"\n💡 To execute the renames, run:")
        print(f"   python {os.path.basename(__file__)} --execute")


if __name__ == '__main__':
    main()
