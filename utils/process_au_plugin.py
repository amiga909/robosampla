#!/usr/bin/env python3
"""
Process Plugins - Apply Audio Unit (AU) and VST plugins to processed audio samples using pedalboard
Usage: python utils/process_au_plugin.py [folder_path] [options]
"""
import sys
import os
import argparse
import glob
import shutil

# Add parent directory to path to import config and modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from pedalboard import Pedalboard, load_plugin
    from pedalboard.io import AudioFile
    import numpy as np
except ImportError as e:
    print(f"Error: Required dependencies not installed: {e}")
    print("Install with: pip install pedalboard")
    sys.exit(1)

from config import OUTPUT_DIR


def list_available_plugins():
    """List all available Audio Unit and VST plugins on the system, prioritizing AU over VST."""
    try:
        print("Scanning for installed plugins...")
        
        plugins = {}  # Use dict to track plugins by name and avoid duplicates
        
        # First pass: Scan AU plugins (priority)
        au_dirs = [
            "/Library/Audio/Plug-Ins/Components",
            os.path.expanduser("~/Library/Audio/Plug-Ins/Components"),
        ]
        
        for plugin_dir in au_dirs:
            if not os.path.exists(plugin_dir):
                continue
                
            print(f"  Scanning AU plugins in {os.path.basename(plugin_dir)}...")
            
            try:
                for item in os.listdir(plugin_dir):
                    if item.endswith('.component'):
                        plugin_name = os.path.splitext(item)[0]
                        item_path = os.path.join(plugin_dir, item)
                        plugin_display = f"{plugin_name} (AU)"
                        
                        # AU plugins have priority - always add them
                        plugins[plugin_name] = (plugin_display, item_path)
                        print(f"    ✓ {plugin_display}")
            except PermissionError:
                print(f"    ⚠ Permission denied accessing {plugin_dir}")
            except Exception as e:
                print(f"    ⚠ Error scanning {plugin_dir}: {e}")
        
        # Also try to get AU plugins using pedalboard API (if available)
        try:
            from pedalboard import AudioUnitPlugin
            if hasattr(AudioUnitPlugin, 'installed_plugins'):
                au_plugins = AudioUnitPlugin.installed_plugins
                print(f"  Found {len(au_plugins)} AU plugins via pedalboard API")
                
                for plugin_path in au_plugins:
                    plugin_filename = os.path.basename(plugin_path)
                    plugin_name = os.path.splitext(plugin_filename)[0]
                    
                    # Only add if we don't already have this plugin from directory scan
                    if plugin_name not in plugins:
                        plugin_display = f"{plugin_name} (AU)"
                        plugins[plugin_name] = (plugin_display, plugin_path)
                        print(f"    ✓ {plugin_display}")
        except Exception as e:
            print(f"  Note: AudioUnitPlugin API not available: {e}")
        
        # Second pass: Scan VST plugins (only if no AU version exists)
        vst_dirs = [
            "/Library/Audio/Plug-Ins/VST3",
            "/Library/Audio/Plug-Ins/VST",
            os.path.expanduser("~/Library/Audio/Plug-Ins/VST3"),
            os.path.expanduser("~/Library/Audio/Plug-Ins/VST"),
        ]
        
        for plugin_dir in vst_dirs:
            if not os.path.exists(plugin_dir):
                continue
                
            vst_type = "VST3" if "VST3" in plugin_dir else "VST2"
            print(f"  Scanning {vst_type} plugins in {os.path.basename(plugin_dir)}...")
            
            try:
                for item in os.listdir(plugin_dir):
                    if item.endswith('.vst3') or item.endswith('.vst'):
                        plugin_name = os.path.splitext(item)[0]
                        item_path = os.path.join(plugin_dir, item)
                        
                        # Only add VST if no AU version exists
                        if plugin_name not in plugins:
                            plugin_display = f"{plugin_name} ({vst_type})"
                            plugins[plugin_name] = (plugin_display, item_path)
                            print(f"    ✓ {plugin_display}")
                        else:
                            print(f"    - {plugin_name} ({vst_type}) - skipped (AU version exists)")
            except PermissionError:
                print(f"    ⚠ Permission denied accessing {plugin_dir}")
            except Exception as e:
                print(f"    ⚠ Error scanning {plugin_dir}: {e}")
        
        if not plugins:
            print("  No plugins found.")
            return []
        
        # Convert dict values to list and sort by display name
        plugin_list = list(plugins.values())
        plugin_list.sort(key=lambda x: x[0])
        
        print(f"  Found {len(plugin_list)} unique plugins (AU prioritized over VST)")
        return plugin_list
        
    except Exception as e:
        print(f"Error during plugin scan: {e}")
        return []


def load_plugin_universal(plugin_identifier):
    """Load an Audio Unit or VST plugin by name or path using load_plugin."""
    try:
        # Use the universal load_plugin function from pedalboard docs
        plugin = load_plugin(plugin_identifier)
        return plugin
    except Exception as e:
        print(f"Error loading plugin '{plugin_identifier}': {e}")
        return None


def get_plugin_presets(plugin):
    """Get available presets for an AU plugin."""
    try:
        if hasattr(plugin, 'presets') and plugin.presets:
            return list(plugin.presets.keys())
        return []
    except Exception as e:
        print(f"Error getting presets: {e}")
        return []


def apply_plugin_to_file(input_file, output_file, plugin, preset_name=None, sample_rate=44100):
    """Apply AU plugin to a single audio file."""
    try:
        # Load the audio file
        with AudioFile(input_file) as f:
            audio = f.read(f.frames)
            original_sample_rate = f.samplerate
        
        # Create pedalboard with the plugin
        board = Pedalboard([plugin])
        
        # Apply preset if specified
        if preset_name and hasattr(plugin, 'presets') and preset_name in plugin.presets:
            plugin.preset = preset_name
            print(f"    Applied preset: {preset_name}")
        
        # Process the audio
        processed_audio = board(audio, sample_rate=original_sample_rate)
        
        # Save the processed audio
        with AudioFile(output_file, 'w', samplerate=original_sample_rate, num_channels=processed_audio.shape[0]) as f:
            f.write(processed_audio)
        
        print(f"    Processed: {os.path.basename(input_file)} -> {os.path.basename(output_file)}")
        return True
        
    except Exception as e:
        print(f"    Error processing {os.path.basename(input_file)}: {e}")
        return False


def process_patch_with_plugin(patch_folder, plugin, preset_name=None, output_suffix="_fx"):
    """Process all WAV files in a patch folder with AU/VST plugin."""
    patch_name = os.path.basename(patch_folder)
    
    # Get WAV files from patch folder
    wav_files = glob.glob(os.path.join(patch_folder, "*.wav"))
    if not wav_files:
        print(f"  Warning: No WAV files found in {patch_name}")
        return False
    
    # Create output directory
    parent_dir = os.path.dirname(patch_folder)
    output_patch_folder = os.path.join(parent_dir, f"{patch_name}{output_suffix}")
    os.makedirs(output_patch_folder, exist_ok=True)
    print(f"  Created output folder: {patch_name}{output_suffix}")
    
    success_count = 0
    total_files = len(wav_files)
    
    # Process each WAV file
    for wav_file in wav_files:
        filename = os.path.basename(wav_file)
        output_file = os.path.join(output_patch_folder, filename)
        
        success = apply_plugin_to_file(wav_file, output_file, plugin, preset_name)
        if success:
            success_count += 1
    
    print(f"  Processed {success_count}/{total_files} files successfully")
    return success_count > 0


def interactive_plugin_selection():
    """Interactive CLI for selecting AU or VST plugin and preset."""
    print("\n" + "="*60)
    print("PLUGIN SELECTION (AU & VST)")
    print("="*60)
    
    # List available plugins - now returns (name, path) tuples with AU prioritized
    plugins = list_available_plugins()
    
    if not plugins:
        print("No Audio Unit or VST plugins found.")
        print("Make sure you have plugins installed in:")
        print("  • /Library/Audio/Plug-Ins/Components (AU)")
        print("  • /Library/Audio/Plug-Ins/VST3 (VST3)")
        print("  • /Library/Audio/Plug-Ins/VST (VST2)")
        return None, None
    
    print(f"\nAvailable plugins (AU prioritized):")
    for i, (plugin_name, plugin_path) in enumerate(plugins, 1):
        print(f"  {i}. {plugin_name}")
    
    # Let user select plugin
    while True:
        try:
            choice = input(f"\nSelect plugin (1-{len(plugins)}) or 'q' to quit: ").strip()
            if choice.lower() == 'q':
                return None, None
            
            choice_num = int(choice)
            
            if 1 <= choice_num <= len(plugins):
                # User selected from the list - use the full path
                selected_plugin_name, selected_plugin_path = plugins[choice_num - 1]
                selected_plugin_identifier = selected_plugin_path  # Use full path
                print(f"Selected: {selected_plugin_name}")
                break
            else:
                print(f"Please enter a number between 1 and {len(plugins)}")
        except ValueError:
            print("Please enter a valid number or 'q'")
    
    print(f"\nLoading plugin: {selected_plugin_name}")
    plugin = load_plugin_universal(selected_plugin_identifier)
    
    if not plugin:
        print("Failed to load plugin.")
        print("Make sure the plugin path is correct and the plugin is installed.")
        return None, None
    
    # Check for presets
    presets = get_plugin_presets(plugin)
    selected_preset = None
    
    if presets:
        print(f"\nFound {len(presets)} presets for {selected_plugin_name}:")
        print("  0. No preset (use default settings)")
        for i, preset_name in enumerate(presets, 1):
            print(f"  {i}. {preset_name}")
        
        while True:
            try:
                choice = input(f"\nSelect preset (0-{len(presets)}) or 'q' to quit: ").strip()
                if choice.lower() == 'q':
                    return None, None
                
                preset_index = int(choice)
                if preset_index == 0:
                    selected_preset = None
                    break
                elif 1 <= preset_index <= len(presets):
                    selected_preset = presets[preset_index - 1]
                    break
                else:
                    print(f"Please enter a number between 0 and {len(presets)}")
            except ValueError:
                print("Please enter a valid number or 'q'")
    else:
        print(f"\nNo presets available for {selected_plugin_name}")
        selected_preset = None
    
    return plugin, selected_preset


def find_processed_folders(root_folder):
    """Find processed patch folders."""
    processed_folders = []
    
    # Look for _processed directory
    processed_dir = os.path.join(root_folder, "_processed")
    if os.path.exists(processed_dir):
        for item in os.listdir(processed_dir):
            item_path = os.path.join(processed_dir, item)
            if os.path.isdir(item_path):
                # Check if folder contains WAV files
                wav_files = glob.glob(os.path.join(item_path, "*.wav"))
                if wav_files:
                    processed_folders.append(item_path)
    
    return sorted(processed_folders)


def main():
    """Main function with command line argument parsing."""
    parser = argparse.ArgumentParser(
        description="Apply Audio Unit (AU) and VST plugins to processed audio samples using pedalboard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  python utils/process_au_plugin.py                              # Process all patches in _processed
  python utils/process_au_plugin.py _output                     # Process all patches in _output/_processed
  python utils/process_au_plugin.py _output/_processed/House!   # Process specific patch folder

This tool processes audio files that have already been processed by process_audio.py
It looks for folders in '_processed' directories and applies AU or VST plugins to them.

Expected structure:
  _output/
  └── _processed/
      ├── Patch1/
      │   ├── sample1.wav     (processed audio)
      │   └── sample2.wav     (processed audio)
      └── Patch2/
          └── sample1.wav     (processed audio)

Output structure:
  _output/
  └── _processed/
      ├── Patch1_fx/
      │   ├── sample1.wav     (Plugin processed)
      │   └── sample2.wav     (Plugin processed)
      └── Patch2_fx/
          └── sample1.wav     (Plugin processed)
        """
    )
    
    parser.add_argument('folder', nargs='?', default=OUTPUT_DIR,
                       help=f'Path to folder containing _processed patches, or specific processed patch folder (default: {OUTPUT_DIR})')
    
    parser.add_argument('--plugin', type=str,
                       help='Plugin path or name (skip interactive selection)')
    
    parser.add_argument('--preset', type=str,
                       help='Preset name to use with the plugin')
    
    parser.add_argument('--suffix', type=str, default='_fx',
                       help='Suffix for output folders (default: _fx)')
    
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
        # Single processed patch mode
        patches_to_process = [args.folder]
        mode = "single processed patch"
    else:
        # Multi-patch mode - find all processed patch folders
        patches_to_process = find_processed_folders(args.folder)
        mode = "multiple processed patches"
    
    if not patches_to_process:
        if mode == "single processed patch":
            print(f"Error: No WAV files found in '{args.folder}'")
        else:
            print(f"Error: No processed patch folders with WAV files found in '{args.folder}'")
            print("Have you run process_audio.py first to create '_processed' folders?")
        sys.exit(1)
    
    # Plugin selection
    if args.plugin:
        # Command line plugin specified
        plugin = load_plugin_universal(args.plugin)
        if not plugin:
            print(f"Error: Could not load plugin '{args.plugin}'")
            sys.exit(1)
        selected_preset = args.preset
        print(f"Using plugin: {args.plugin}")
        if selected_preset:
            print(f"Using preset: {selected_preset}")
    else:
        # Interactive plugin selection
        plugin, selected_preset = interactive_plugin_selection()
        if not plugin:
            print("No plugin selected. Exiting.")
            sys.exit(0)
    
    # Show processing information
    print("\n" + "="*60)
    print("PLUGIN PROCESSOR (AU & VST)")
    print("="*60)
    print(f"Mode: {mode}")
    print(f"Base folder: {args.folder}")
    print(f"Patches found: {len(patches_to_process)}")
    print(f"Plugin: {plugin}")
    if selected_preset:
        print(f"Preset: {selected_preset}")
    print(f"Output suffix: {args.suffix}")
    
    # List patches
    print(f"\nProcessed patches to enhance:")
    for patch_folder in patches_to_process:
        patch_name = os.path.basename(patch_folder)
        wav_files = glob.glob(os.path.join(patch_folder, "*.wav"))
        print(f"  • {patch_name} ({len(wav_files)} WAV files)")

    # Confirm processing
    total_patches = len(patches_to_process)
    print(f"\n⚡ This will apply plugin to {total_patches} processed patch folder(s).")
    print("Original processed files will remain untouched.")
    print(f"\nProcessing will create new folders with '{args.suffix}' suffix.")
    
    response = input("\nContinue? (y/N): ").strip().lower()
    if response not in ['y', 'yes']:
        print("Processing cancelled.")
        sys.exit(0)
    
    # Process all patches
    print("\n" + "-"*60)
    print("APPLYING PLUGIN...")
    print("-"*60)
    
    success_count = 0
    failed_patches = []
    
    try:
        for i, patch_folder in enumerate(patches_to_process, 1):
            patch_name = os.path.basename(patch_folder)
            print(f"\n[{i}/{total_patches}] Processing: {patch_name}")
            
            success = process_patch_with_plugin(
                patch_folder=patch_folder,
                plugin=plugin,
                preset_name=selected_preset,
                output_suffix=args.suffix
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
            print("✅ ALL PLUGIN PROCESSING COMPLETED SUCCESSFULLY!")
        else:
            print("⚠️  PLUGIN PROCESSING COMPLETED WITH SOME FAILURES")
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
