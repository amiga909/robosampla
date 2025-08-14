#!/usr/bin/env python3
"""
Deluge Kit XML Generator
Generates XML kit files for Synthstrom Deluge from processed Airbase samples.
"""

import os
import shutil
from pathlib import Path
import re
import wave


def get_drum_samples():
    """Get the list of expected drum sample filenames for a kit."""
    return [
        "1_Kick",
        "2_Snare", 
        "3_LoTom",
        "4_HiTom",
        "5_ClosedHiHat",
        "6_OpenHiHat",
        "7_Clap",
        "8_Rim_Shot",
        "9_Crash",
        "10_Ride"
    ]


def get_wav_info(wav_path):
    """
    Get WAV file information including frame count for endSamplePos.
    
    Args:
        wav_path: Path to the WAV file
        
    Returns:
        dict with 'frames', 'sample_rate', 'channels', 'duration' or None if error
    """
    try:
        with wave.open(str(wav_path), 'rb') as w:
            frames = w.getnframes()
            sample_rate = w.getframerate()
            channels = w.getnchannels()
            duration = frames / sample_rate if sample_rate > 0 else 0
            
            return {
                'frames': frames,
                'sample_rate': sample_rate,
                'channels': channels,
                'duration': duration
            }
    except Exception as e:
        print(f"    ⚠️  Error reading WAV file {wav_path}: {e}")
        return None


def generate_xml_for_patch(template_path, patch_name, patch_dir, output_dir, dry_run=False):
    """
    Generate XML file for a specific patch by replacing template paths.
    
    Args:
        template_path: Path to the KIT001.XML template file
        patch_name: Name of the patch (folder name)
        patch_dir: Path to the patch directory with samples
        output_dir: Directory to save the generated XML
        dry_run: If True, only show what would be done
    """
    # Read template
    with open(template_path, 'r', encoding='utf-8') as f:
        xml_content = f.read()
    
    # Check which samples exist in the patch directory and get their info
    existing_samples = {}
    sample_info = {}
    expected_samples = get_drum_samples()
    
    for sample_base in expected_samples:
        sample_file = f"{sample_base}_{patch_name}.wav"
        sample_path = patch_dir / sample_file
        
        if sample_path.exists():
            # Get WAV file info
            wav_info = get_wav_info(sample_path)
            if wav_info:
                existing_samples[sample_base] = sample_file
                sample_info[sample_base] = wav_info
                #print(f"  ✓ Found: {sample_file} ({wav_info['frames']} samples, {wav_info['duration']:.3f}s)")
            else:
                print(f"  ⚠️  Found but can't read: {sample_file}")
        else:
            print(f"  ✗ Missing: {sample_file}")
    
    if not existing_samples:
        print(f"  ⚠️  No samples found for {patch_name}, skipping XML generation")
        return False
    
    # Replace fileName paths and endSamplePos values in the XML
    # We'll do this in two passes for better reliability
    
    # Pass 1: Replace fileName attributes
    def replace_filename(match):
        full_match = match.group(0)
        # Extract the sample number and type (e.g., "1_Kick")
        sample_match = re.search(r'(\d+_[^_]+)_808State\.wav', full_match)
        if sample_match:
            sample_base = sample_match.group(1)
            if sample_base in existing_samples:
                # Replace with actual patch name and filename
                new_filename = f'fileName="SAMPLES/JomoxAirBaseKits/{patch_name}/{existing_samples[sample_base]}"'
                return new_filename
        return full_match
    
    # Replace all fileName attributes
    xml_content = re.sub(
        r'fileName="SAMPLES/JomoxAirBaseKits/808State/\d+_[^"]+\.wav"',
        replace_filename,
        xml_content
    )
    
    # Pass 2: Replace endSamplePos values
    # We need to match each endSamplePos and figure out which sample it belongs to
    # by looking at the preceding fileName
    
    def replace_end_sample_pos(match):
        full_match = match.group(0)
        current_pos = match.start()
        
        # Look backwards in the XML to find the most recent fileName
        text_before = xml_content[:current_pos]
        filename_match = None
        
        # Find the last fileName before this endSamplePos
        for fm in re.finditer(r'fileName="SAMPLES/JomoxAirBaseKits/' + re.escape(patch_name) + r'/(\d+_[^_]+)_[^"]+\.wav"', text_before):
            filename_match = fm
        
        if filename_match:
            sample_base = filename_match.group(1)
            if sample_base in sample_info:
                new_end_pos = sample_info[sample_base]['frames']
                return f'endSamplePos="{new_end_pos}"'
        
        return full_match
    
    # Replace endSamplePos attributes
    xml_content = re.sub(
        r'endSamplePos="\d+"',
        replace_end_sample_pos,
        xml_content
    )
    
    # Create output filename
    output_file = output_dir / f"{patch_name}.XML"
    
    if dry_run:
        print(f"  → Would create: {output_file}")
        print(f"  → With {len(existing_samples)} samples")
    else:
        # Write the generated XML
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(xml_content)
        print(f"  → Created: {output_file}")
        print(f"  → With {len(existing_samples)} samples")
    
    return True


def main():
    """Main function to process all patches."""
    # Current directory where this script file is located
    current_dir = Path(__file__).parent
    
    # Parent directory (one level up from current script)
    parent_dir = Path(__file__).parent.parent

    template_file = current_dir / "KIT001.XML"   
    processed_dir = parent_dir / "_output_Jomox" / "_processed"
    output_dir = current_dir / "_XML"  # Fixed: was incorrectly using Path(__file__)
    
    # Check if template exists
    if not template_file.exists():
        print(f"❌ Template file not found: {template_file}")
        return
    
    # Check if processed directory exists
    if not processed_dir.exists():
        print(f"❌ Processed directory not found: {processed_dir}")
        return
    
    # Create output directory
    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"📁 Created output directory: {output_dir}")
    
    print(f"🎛️  Deluge Kit XML Generator")
    print(f"📄 Template: {template_file}")
    print(f"📂 Input: {processed_dir}")
    print(f"📂 Output: {output_dir}")
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
    
    # Ask for confirmation
    response = input("Generate XML files? (y/N): ").strip().lower()
    if response not in ['y', 'yes']:
        print("Cancelled.")
        return
    
    # Process each patch
    generated_count = 0
    skipped_count = 0
    skipped_patches = []
    
    for patch_dir in sorted(patch_dirs):
        patch_name = patch_dir.name
        print(f"🎵 Processing: {patch_name}")
        
        try:
            success = generate_xml_for_patch(
                template_file, 
                patch_name, 
                patch_dir, 
                output_dir, 
                dry_run=False
            )
            
            if success:
                generated_count += 1
            else:
                skipped_count += 1
                skipped_patches.append(patch_name)
                
        except Exception as e:
            print(f"  ❌ Error processing {patch_name}: {e}")
            skipped_count += 1
            skipped_patches.append(patch_name)
        
        print()
    
    print(f"✅ Complete!")
    print(f"   Generated: {generated_count} XML files")
    print(f"   Skipped: {skipped_count} patches")
    if skipped_patches:
        print(f"   Skipped patches: {', '.join(skipped_patches)}")
    print(f"   Output directory: {output_dir}")


if __name__ == "__main__":
    main()
