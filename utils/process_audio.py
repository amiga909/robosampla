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
from config import SILENCE_THRESHOLD_DB, FADE_IN_MS, FADE_OUT_MS, TARGET_PEAK_DB, OUTPUT_DIR, UNPROCESSED_FOLDER, SAMPLE_RATE


def process_single_patch(patch_folder, sample_rate, target_peak_db, fade_in_ms, fade_out_ms):
    """Process a single patch folder by copying from unprocessed to root and processing."""
    unprocessed_folder = os.path.join(patch_folder, UNPROCESSED_FOLDER)
    
    if not os.path.exists(unprocessed_folder):
        print(f"  Warning: No '{UNPROCESSED_FOLDER}' subfolder found in {os.path.basename(patch_folder)}")
        return False
    
    # Get unprocessed WAV files
    unprocessed_files = glob.glob(os.path.join(unprocessed_folder, "*.wav"))
    if not unprocessed_files:
        print(f"  Warning: No WAV files found in {os.path.join(os.path.basename(patch_folder), UNPROCESSED_FOLDER)}")
        return False
    
    print(f"  Found {len(unprocessed_files)} unprocessed files")
    
    # Copy unprocessed files to patch root (overwrite processed samples)
    for unprocessed_file in unprocessed_files:
        filename = os.path.basename(unprocessed_file)
        dest_path = os.path.join(patch_folder, filename)
        shutil.copy2(unprocessed_file, dest_path)
    
    # Process the patch folder
    success, processing_errors = process_patch_folder(
        patch_folder=patch_folder,
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
    """Find all patch folders that contain an 'unprocessed' subfolder."""
    patch_folders = []
    
    # Look for directories that contain an 'unprocessed' subfolder
    for item in os.listdir(root_folder):
        item_path = os.path.join(root_folder, item)
        if os.path.isdir(item_path):
            unprocessed_path = os.path.join(item_path, UNPROCESSED_FOLDER)
            if os.path.exists(unprocessed_path) and os.path.isdir(unprocessed_path):
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
  │   ├── sample1.wav          (processed)
  │   ├── sample2.wav          (processed)
  │   └── {UNPROCESSED_FOLDER}/
  │       ├── sample1.wav      (original)
  │       └── sample2.wav      (original)
  └── Patch2/
      ├── sample1.wav          (processed)
      └── {UNPROCESSED_FOLDER}/
          └── sample1.wav      (original)
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
    unprocessed_subfolder = os.path.join(args.folder, UNPROCESSED_FOLDER)
    
    if direct_wav_files or os.path.exists(unprocessed_subfolder):
        # Single patch mode
        patches_to_process = [args.folder]
        mode = "single patch"
    else:
        # Multi-patch mode - find all patch folders
        patches_to_process = find_patch_folders(args.folder)
        mode = "multiple patches"
    
    if not patches_to_process:
        if mode == "single patch":
            print(f"Error: No WAV files or '{UNPROCESSED_FOLDER}' folder found in '{args.folder}'")
        else:
            print(f"Error: No patch folders with '{UNPROCESSED_FOLDER}' subfolders found in '{args.folder}'")
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
        unprocessed_folder = os.path.join(patch_folder, UNPROCESSED_FOLDER)
        if os.path.exists(unprocessed_folder):
            unprocessed_files = glob.glob(os.path.join(unprocessed_folder, "*.wav"))
            print(f"  • {patch_name} ({len(unprocessed_files)} unprocessed files)")
        else:
            direct_files = glob.glob(os.path.join(patch_folder, "*.wav"))
            print(f"  • {patch_name} ({len(direct_files)} files, no {UNPROCESSED_FOLDER} folder)")
    
    if args.dry_run:
        print(f"\n🔍 DRY RUN MODE - No files will be modified")
        print(f"\nProcessing would include:")
        print(f"  • Copy files from '{UNPROCESSED_FOLDER}' folders to patch roots")
        print(f"  • Silence removal and trimming (threshold: {SILENCE_THRESHOLD_DB} dB)")
        print(f"  • Fade in/out application ({FADE_IN_MS}/{FADE_OUT_MS} ms)")
        print(f"  • Patch-wide normalization to {TARGET_PEAK_DB} dB")
        print("\nRun without --dry-run to actually process the files.")
        return
    
    # Confirm processing
    total_patches = len(patches_to_process)
    print(f"\n⚠️  This will process {total_patches} patch folder(s) and overwrite processed samples!")
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
            
            # Check if this is a single patch with unprocessed folder
            unprocessed_folder = os.path.join(patch_folder, UNPROCESSED_FOLDER)
            if os.path.exists(unprocessed_folder):
                success = process_single_patch(
                    patch_folder=patch_folder,
                    sample_rate=SAMPLE_RATE,
                    target_peak_db=TARGET_PEAK_DB,
                    fade_in_ms=FADE_IN_MS,
                    fade_out_ms=FADE_OUT_MS
                )
            else:
                # Process directly (no unprocessed folder)
                print(f"  No '{UNPROCESSED_FOLDER}' folder, processing files directly")
                success, processing_errors = process_patch_folder(
                    patch_folder=patch_folder,
                    sample_rate=SAMPLE_RATE,
                    target_peak_db=TARGET_PEAK_DB,
                    fade_in_ms=FADE_IN_MS,
                    fade_out_ms=FADE_OUT_MS,
                    silence_threshold_db=SILENCE_THRESHOLD_DB
                )
                
                # Report any processing errors
                if processing_errors:
                    print(f"    Warnings: {len(processing_errors)} samples had issues")
                    for error in processing_errors:
                        print(f"      {error['filename']}: {error['description']}")
            
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
