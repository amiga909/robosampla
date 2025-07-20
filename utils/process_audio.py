#!/usr/bin/env python3
"""
Process Audio - Process audio samples in patch folders
Usage: python utils/process_audio.py [folder_path] [options]
"""
import sys
import os
import argparse
import glob
import shutil

# Add parent directory to path to import config and modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from audio_processor import process_patch_folder
from config import SILENCE_THRESHOLD_DB, FADE_IN_MS, FADE_OUT_MS, TARGET_PEAK_DB, OUTPUT_DIR, SAMPLE_RATE


def process_single_patch(patch_folder, sample_rate, target_peak_db, fade_in_ms, fade_out_ms):
    """Process a single patch folder by copying to a new 'processed_PATCHNAME' folder and processing."""
    patch_name = os.path.basename(patch_folder)
    
    # Get WAV files from root patch folder
    wav_files = glob.glob(os.path.join(patch_folder, "*.wav"))
    if not wav_files:
        print(f"  Warning: No WAV files found in {patch_name}")
        return False
    
    print(f"  Found {len(wav_files)} files to process")
    
    # Create processed folder in the same parent directory as the original
    parent_dir = os.path.dirname(patch_folder)
    processed_folder_name = f"_processed_{patch_name}"
    processed_folder = os.path.join(parent_dir, processed_folder_name)
    
    # Create the processed folder
    os.makedirs(processed_folder, exist_ok=True)
    print(f"  Created processed folder: {processed_folder_name}")
    
    # Copy all WAV files to the processed folder
    for wav_file in wav_files:
        filename = os.path.basename(wav_file)
        dest_path = os.path.join(processed_folder, filename)
        shutil.copy2(wav_file, dest_path)
    
    # Process the processed folder (leaving original untouched)
    success, processing_errors = process_patch_folder(
        patch_folder=processed_folder,
        sample_rate=sample_rate,
        target_peak_db=target_peak_db,
        fade_in_ms=fade_in_ms,
        fade_out_ms=fade_out_ms,
        silence_threshold_db=SILENCE_THRESHOLD_DB
    )
    
    # Report any processing errors
    if processing_errors:
        print(f"    Warnings: {len(processing_errors)} samples had issues")
        for error in processing_errors:
            print(f"      {error['filename']}: {error['description']}")
    
    return success


def find_patch_folders(root_folder):
    """Find all patch folders that contain WAV files."""
    patch_folders = []
    
    # Look for directories that contain WAV files
    for item in os.listdir(root_folder):
        item_path = os.path.join(root_folder, item)
        if os.path.isdir(item_path):
            # Skip already processed folders
            if item.startswith("processed_"):
                continue
            
            # Check if folder contains WAV files
            wav_files = glob.glob(os.path.join(item_path, "*.wav"))
            if wav_files:
                patch_folders.append(item_path)
    
    return sorted(patch_folders)


def main():
    """Main function with command line argument parsing."""
    parser = argparse.ArgumentParser(
        description="Process audio samples in patch folders",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  python utils/process_audio.py                                   # Process all patches in output directory
  python utils/process_audio.py _output                          # Process all patches in _output folder
  python utils/process_audio.py _output/House!                   # Process specific patch folder
  python utils/process_audio.py --dry-run                        # Preview what would be processed

Configuration is loaded from config.py:
  - Target peak level: {TARGET_PEAK_DB} dB
  - Fade in/out: {FADE_IN_MS}/{FADE_OUT_MS} ms  
  - Silence threshold: {SILENCE_THRESHOLD_DB} dB

Structure expected (when no folder specified):
  {OUTPUT_DIR}/
  ├── Patch1/
  │   ├── sample1.wav          (original)
  │   └── sample2.wav          (original)
  └── Patch2/
      └── sample1.wav          (original)

Processed files will be saved to new folders:
  {OUTPUT_DIR}/
  ├── processed_Patch1/
  │   ├── sample1.wav          (processed)
  │   └── sample2.wav          (processed)
  └── processed_Patch2/
      └── sample1.wav          (processed)
        """
    )
    
    parser.add_argument('folder', nargs='?', default=OUTPUT_DIR,
                       help=f'Path to folder containing patches, or specific patch folder (default: {OUTPUT_DIR})')
    
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be processed without making changes')
    
    args = parser.parse_args()
    
    # Validate folder path
    if not os.path.exists(args.folder):
        print(f"Error: Folder '{args.folder}' does not exist")
        sys.exit(1)
    
    if not os.path.isdir(args.folder):
        print(f"Error: '{args.folder}' is not a directory")
        sys.exit(1)
    
    # Determine processing mode
    # Check if this folder directly contains WAV files (single patch mode)
    direct_wav_files = glob.glob(os.path.join(args.folder, "*.wav"))
    
    if direct_wav_files:
        # Single patch mode
        patches_to_process = [args.folder]
        mode = "single patch"
    else:
        # Multi-patch mode - find all patch folders
        patches_to_process = find_patch_folders(args.folder)
        mode = "multiple patches"
    
    if not patches_to_process:
        if mode == "single patch":
            print(f"Error: No WAV files found in '{args.folder}'")
        else:
            print(f"Error: No patch folders with WAV files found in '{args.folder}'")
        sys.exit(1)
    
    # Show processing information
    print("="*60)
    print("AUDIO PROCESSOR")
    print("="*60)
    print(f"Mode: {mode}")
    print(f"Base folder: {args.folder}")
    print(f"Patches found: {len(patches_to_process)}")
    print(f"Target peak: {TARGET_PEAK_DB} dB")
    print(f"Fade in: {FADE_IN_MS} ms")
    print(f"Fade out: {FADE_OUT_MS} ms")
    print(f"Silence threshold: {SILENCE_THRESHOLD_DB} dB")
    
    # List patches
    print(f"\nPatches to process:")
    for patch_folder in patches_to_process:
        patch_name = os.path.basename(patch_folder)
        wav_files = glob.glob(os.path.join(patch_folder, "*.wav"))
        print(f"  • {patch_name} ({len(wav_files)} WAV files)")

    if args.dry_run:
        print(f"\n🔍 DRY RUN MODE - No files will be modified")
        print(f"\nProcessing would include:")
        print(f"  • Copy files to new 'processed_PATCHNAME' folders")
        print(f"  • Silence removal and trimming (threshold: {SILENCE_THRESHOLD_DB} dB)")
        print(f"  • Fade in/out application ({FADE_IN_MS}/{FADE_OUT_MS} ms)")
        print(f"  • Patch-wide normalization to {TARGET_PEAK_DB} dB")
        print("\nRun without --dry-run to actually process the files.")
        return
    
    # Confirm processing
    total_patches = len(patches_to_process)
    print(f"\n⚡ This will process {total_patches} patch folder(s) and create new 'processed_PATCHNAME' folders.")
    print("Original files will remain untouched.")
    response = input("Continue? (y/N): ").strip().lower()
    if response not in ['y', 'yes']:
        print("Processing cancelled.")
        sys.exit(0)
    
    # Process all patches
    print("\n" + "-"*60)
    print("PROCESSING...")
    print("-"*60)
    
    success_count = 0
    failed_patches = []
    
    try:
        for i, patch_folder in enumerate(patches_to_process, 1):
            patch_name = os.path.basename(patch_folder)
            print(f"\n[{i}/{total_patches}] Processing: {patch_name}")
            
            # Use the new non-destructive processing method
            success = process_single_patch(
                patch_folder=patch_folder,
                sample_rate=SAMPLE_RATE,
                target_peak_db=TARGET_PEAK_DB,
                fade_in_ms=FADE_IN_MS,
                fade_out_ms=FADE_OUT_MS
            )
            
            if success:
                success_count += 1
                print(f"  ✅ {patch_name} completed successfully")
            else:
                failed_patches.append(patch_name)
                print(f"  ❌ {patch_name} failed")
        
        # Final summary
        print("\n" + "="*60)
        if success_count == total_patches:
            print("✅ ALL PROCESSING COMPLETED SUCCESSFULLY!")
        else:
            print("⚠️  PROCESSING COMPLETED WITH SOME FAILURES")
        print("="*60)
        print(f"Total patches: {total_patches}")
        print(f"Successful: {success_count}")
        print(f"Failed: {len(failed_patches)}")
        
        if failed_patches:
            print(f"\nFailed patches:")
            for patch_name in failed_patches:
                print(f"  • {patch_name}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\nProcessing interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
