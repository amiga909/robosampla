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
import json
import subprocess

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
    """List all available Audio Unit and VST plugins on the system, prioritizing AU over VST (AU is more reliable)."""
    try:
        print("Scanning for installed plugins...")
        
        plugins = {}  # Use dict to track plugins by name and avoid duplicates
        
        # First pass: Scan AU plugins (priority - they work more reliably)
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
        print(f"  Attempting to load plugin from: {plugin_identifier}")
        
        # Check if the file exists
        if not os.path.exists(plugin_identifier):
            print(f"  Error: Plugin file does not exist at path: {plugin_identifier}")
            return None
        
        # Check if it's a directory (both AU and VST3 plugins are often bundles/directories)
        if os.path.isdir(plugin_identifier):
            print(f"  Plugin is a bundle/directory: {os.path.basename(plugin_identifier)}")
        else:
            print(f"  Plugin is a file: {os.path.basename(plugin_identifier)}")
            
        # Use the simple load_plugin approach from the examples
        plugin = load_plugin(plugin_identifier)
            
        print(f"  Successfully loaded plugin: {type(plugin).__name__}")
        
        # Show some basic plugin info
        if hasattr(plugin, 'name'):
            print(f"  Plugin name: {plugin.name}")
        if hasattr(plugin, 'parameters'):
            param_count = len(plugin.parameters) if plugin.parameters else 0
            print(f"  Parameters available: {param_count}")
            
            # Show available parameter names
            if param_count > 0:
                param_names = list(plugin.parameters.keys())
                print(f"  Parameter names: {', '.join(param_names[:5])}" + 
                      (f" (+{param_count-5} more...)" if param_count > 5 else ""))
            
        return plugin
        
    except Exception as e:
        print(f"Error loading plugin '{plugin_identifier}': {e}")
        
        # Provide more specific troubleshooting advice
        if plugin_identifier.endswith('.vst3'):
            print("  Troubleshooting VST3 plugin:")
            print("  1. VST3 support may be limited on this system")
            print("  2. Try the Audio Unit (AU) version if available")
            print("  3. Make sure the plugin is 64-bit and properly installed")
        elif plugin_identifier.endswith('.vst'):
            print("  Troubleshooting VST2 plugin:")
            print("  1. VST2 support may be limited on this system")  
            print("  2. Try the Audio Unit (AU) version if available")
            print("  3. Some VST2 plugins require additional setup")
        elif plugin_identifier.endswith('.component'):
            print("  Troubleshooting AU plugin:")
            print("  1. Make sure the plugin is in the correct Components directory")
            print("  2. Try running: auval -v to validate Audio Units")
            print("  3. The plugin may need to be re-installed or authorized")
            
        return None


def save_default_preset(plugin):
    """Save plugin's current settings as the default preset."""
    try:
        if not hasattr(plugin, 'name'):
            print(f"  ❌ Plugin has no name attribute")
            return False
            
        plugin_name = plugin.name.replace(' ', '_').replace('/', '_')  # Clean name for filename
        preset_dir = os.path.join(os.path.dirname(__file__), "default_presets")
        os.makedirs(preset_dir, exist_ok=True)
        
        # Save as binary state if available (more complete)
        if hasattr(plugin, 'raw_state'):
            preset_file = os.path.join(preset_dir, f"{plugin_name}_default.bin")
            with open(preset_file, 'wb') as f:
                f.write(plugin.raw_state)
            print(f"  ✅ Saved default preset (binary): {plugin_name}")
            return True
            
        # Fallback to JSON parameters
        elif hasattr(plugin, 'parameters') and plugin.parameters:
            param_value_dict = {parameter_name: getattr(plugin, parameter_name) 
                              for parameter_name in plugin.parameters.keys()}
            
            # Handle WrappedBool objects
            try:
                from pedalboard._pedalboard import WrappedBool
                param_value_dict = {k: (bool(v) if isinstance(v, WrappedBool) else v) 
                                  for k, v in param_value_dict.items()}
            except ImportError:
                try:
                    from pedalboard.pedalboard import WrappedBool
                    param_value_dict = {k: (bool(v) if isinstance(v, WrappedBool) else v) 
                                      for k, v in param_value_dict.items()}
                except ImportError:
                    pass
            
            preset_file = os.path.join(preset_dir, f"{plugin_name}_default.json")
            with open(preset_file, 'w') as f:
                json.dump(param_value_dict, f, indent=2)
            print(f"  ✅ Saved default preset (JSON): {plugin_name}")
            return True
        else:
            print(f"  ❌ Plugin has no saveable state")
            return False
        
    except Exception as e:
        print(f"  ❌ Error saving default preset: {e}")
        return False


def load_default_preset(plugin):
    """Load plugin's default preset if it exists."""
    try:
        if not hasattr(plugin, 'name'):
            return False
            
        plugin_name = plugin.name.replace(' ', '_').replace('/', '_')
        preset_dir = os.path.join(os.path.dirname(__file__), "default_presets")
        
        # Try binary preset first
        bin_preset_file = os.path.join(preset_dir, f"{plugin_name}_default.bin")
        if os.path.exists(bin_preset_file) and hasattr(plugin, 'raw_state'):
            with open(bin_preset_file, 'rb') as f:
                plugin.raw_state = f.read()
            print(f"    ✅ Loaded default preset (binary): {plugin_name}")
            return True
        
        # Try JSON preset
        json_preset_file = os.path.join(preset_dir, f"{plugin_name}_default.json")
        if os.path.exists(json_preset_file):
            with open(json_preset_file, 'r') as f:
                param_value_dict = json.load(f)
            
            for parameter_name, serialized_value in param_value_dict.items():
                if hasattr(plugin, parameter_name):
                    setattr(plugin, parameter_name, serialized_value)
            
            print(f"    ✅ Loaded default preset (JSON): {plugin_name}")
            return True
        
        return False
        
    except Exception as e:
        print(f"    ❌ Error loading default preset: {e}")
        return False


def get_plugin_folder_name(plugin):
    """Get clean folder name for plugin."""
    if hasattr(plugin, 'name'):
        # Clean plugin name for use as folder name
        plugin_name = plugin.name.replace(' ', '_').replace('/', '_').replace('\\', '_')
        return f"_{plugin_name}"
    else:
        return "_plugin"


def apply_plugin_to_file(input_file, output_file, plugin, sample_rate=44100):
    """Apply plugin to a single audio file."""
    try:
        # Load the audio file
        with AudioFile(input_file) as f:
            audio = f.read(f.frames)
            original_sample_rate = f.samplerate
        
        # Create pedalboard with the plugin
        board = Pedalboard([plugin])
        
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


def process_patch_with_plugin(patch_folder, plugin):
    """Process all WAV files in a patch folder with AU/VST plugin."""
    patch_name = os.path.basename(patch_folder)
    
    # Get WAV files from patch folder
    wav_files = glob.glob(os.path.join(patch_folder, "*.wav"))
    if not wav_files:
        print(f"  Warning: No WAV files found in {patch_name}")
        return False
    
    # Create _plugins directory in the same parent directory as the input patch
    parent_dir = os.path.dirname(patch_folder)
    plugins_dir = os.path.join(parent_dir, "_plugins")
    os.makedirs(plugins_dir, exist_ok=True)
    
    plugin_suffix = get_plugin_folder_name(plugin)
    
    # Check if folder already has this plugin suffix to avoid duplicates like slamlow_FuzzPlus3_FuzzPlus3
    if patch_name.endswith(plugin_suffix):
        # Folder already has this plugin suffix, use same name
        output_folder_name = patch_name
        print(f"  Re-processing existing plugin folder: {patch_name}")
    else:
        # Create new folder name with plugin suffix
        output_folder_name = f"{patch_name}{plugin_suffix}"
        print(f"  Processing with plugin suffix: {plugin_suffix}")
    
    output_patch_folder = os.path.join(plugins_dir, output_folder_name)
    
    # Remove existing folder if it exists (overwrite)
    if os.path.exists(output_patch_folder):
        shutil.rmtree(output_patch_folder)
        print(f"  Removed existing folder: _plugins/{output_folder_name}")
    
    os.makedirs(output_patch_folder, exist_ok=True)
    print(f"  Created output folder: _plugins/{output_folder_name}")
    
    success_count = 0
    total_files = len(wav_files)
    
    # Process each WAV file
    for wav_file in wav_files:
        filename = os.path.basename(wav_file)
        output_file = os.path.join(output_patch_folder, filename)
        
        success = apply_plugin_to_file(wav_file, output_file, plugin)
        if success:
            success_count += 1
    
    print(f"  Processed {success_count}/{total_files} files successfully")
    
    # Return both success status and the output folder path
    return (success_count > 0, output_patch_folder)


def interactive_plugin_selection():
    """Interactive CLI for selecting AU or VST plugin with simplified preset handling."""
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
        return None
    
    print(f"\nAvailable plugins (AU prioritized):")
    for i, (plugin_name, plugin_path) in enumerate(plugins, 1):
        print(f"  {i}. {plugin_name}")
    
    # Let user select plugin
    while True:
        try:
            choice = input(f"\nSelect plugin (1-{len(plugins)}) or 'q' to quit: ").strip()
            if choice.lower() == 'q':
                return None
            
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
        return None
    
    # Try to load default preset if it exists
    preset_loaded = load_default_preset(plugin)
    if not preset_loaded:
        print("    No default preset found, using factory settings")
    
    # Ask if user wants to adjust settings
    if hasattr(plugin, 'show_editor'):
        adjust_settings = input(f"\nWould you like to adjust plugin settings? (y/N): ").strip().lower()
        if adjust_settings in ['y', 'yes']:
            print("Opening plugin editor... Close the editor window when you're done adjusting parameters.")
            try:
                plugin.show_editor()
                print("Plugin editor closed.")
                
                # Show current parameter values
                if hasattr(plugin, 'parameters') and plugin.parameters:
                    print(f"\nCurrent parameter values:")
                    param_value_dict = {parameter_name: getattr(plugin, parameter_name) 
                                      for parameter_name in plugin.parameters.keys()}
                    for param_name, param_value in param_value_dict.items():
                        print(f"  {param_name}: {param_value}")
                
                # Ask if user wants to save these settings as default
                save_default = input(f"\nSave these settings as default for future use? (y/N): ").strip().lower()
                if save_default in ['y', 'yes']:
                    save_default_preset(plugin)
                        
            except Exception as e:
                print(f"Error opening plugin editor: {e}")
                print("Continuing with current settings...")
    
    return plugin


def run_process_audio_on_folder(plugin_folder):
    """Run process_audio.py on a plugin-processed folder."""
    try:
        # Get the path to process_audio.py (should be in utils directory)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        process_audio_script = os.path.join(script_dir, "process_audio.py")
        
        if not os.path.exists(process_audio_script):
            print(f"    ❌ process_audio.py not found at {process_audio_script}")
            return False
        
        folder_name = os.path.basename(plugin_folder)
        print(f"    🎵 Running process_audio.py on {folder_name}...")
        
        # Run process_audio.py with the plugin folder as input and --yes flag to skip prompts
        # Change to the parent directory (project root) for proper imports
        project_root = os.path.dirname(script_dir)
        cmd = [sys.executable, process_audio_script, plugin_folder, "--yes"]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)
        
        if result.returncode == 0:
            print(f"    ✅ Audio processing completed successfully")
            return True
        else:
            print(f"    ❌ Audio processing failed:")
            if result.stderr:
                print(f"        Error: {result.stderr.strip()}")
            if result.stdout:
                print(f"        Output: {result.stdout.strip()}")
            return False
            
    except Exception as e:
        print(f"    ❌ Error running process_audio.py: {e}")
        return False


def find_processed_folders(root_folder):
    """Find processed patch folders in both _processed and _plugins directories."""
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
    
    # Also look for _plugins directory (for re-processing plugin folders)
    plugins_dir = os.path.join(root_folder, "_plugins")
    if os.path.exists(plugins_dir):
        for item in os.listdir(plugins_dir):
            item_path = os.path.join(plugins_dir, item)
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
  python utils/process_plugins.py                               # Process all patches in _processed
  python utils/process_plugins.py _output                      # Process all patches in _output/_processed
  python utils/process_plugins.py _output/_processed/House!    # Process specific patch folder

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

Output structure (using FuzzPlus3 plugin as example):
  _output/
  ├── _processed/
  │   ├── Patch1/             (original processed audio)
  │   └── Patch2/             (original processed audio)
  ├── _plugins/               (plugin effects from _processed folder)
  │   ├── Patch1_FuzzPlus3/
  │   └── Patch2_FuzzPlus3/
  └── other_folders...

  If processing from a specific folder:
  some_folder/
  ├── patch_files...
  └── _plugins/               (plugin effects created here)
      └── folder_name_FuzzPlus3/

Note: Plugin folders are created in '_plugins' directory alongside the source folder. Existing folders will be overwritten.
        """
    )
    
    parser.add_argument('folder', nargs='?', default=OUTPUT_DIR,
                       help=f'Path to folder containing _processed patches, or specific processed patch folder (default: {OUTPUT_DIR})')
    
    parser.add_argument('--plugin', type=str,
                       help='Plugin path or name (skip interactive selection)')
    
    parser.add_argument('--skip-audio-processing', action='store_true',
                       help='Skip running process_audio.py on plugin folders')
    
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
            print("Or use folders from '_plugins' directory to re-process plugin effects.")
        sys.exit(1)
    
    # Plugin selection
    if args.plugin:
        # Command line plugin specified
        plugin = load_plugin_universal(args.plugin)
        if not plugin:
            print(f"Error: Could not load plugin '{args.plugin}'")
            sys.exit(1)
        # Try to load default preset
        load_default_preset(plugin)
        print(f"Using plugin: {args.plugin}")
    else:
        # Interactive plugin selection
        plugin = interactive_plugin_selection()
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
    plugin_suffix = get_plugin_folder_name(plugin)
    print(f"Output suffix: {plugin_suffix}")
    
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
    print(f"\nProcessing will create new folders in '_plugins' directory with '{plugin_suffix}' suffix.")
    print("⚠️  Existing plugin folders in '_plugins' will be overwritten!")
    
    if not args.skip_audio_processing:
        print(f"\n🎵 After plugin processing, process_audio.py will be run on each folder.")
    else:
        print(f"\n⏭️  Audio processing will be skipped (--skip-audio-processing)")
    
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
    plugin_folders_created = []
    
    try:
        for i, patch_folder in enumerate(patches_to_process, 1):
            patch_name = os.path.basename(patch_folder)
            print(f"\n[{i}/{total_patches}] Processing: {patch_name}")
            
            success, output_folder = process_patch_with_plugin(
                patch_folder=patch_folder,
                plugin=plugin
            )
            
            if success:
                success_count += 1
                print(f"  ✅ {patch_name} plugin processing completed successfully")
                
                # Use the actual output folder path returned by the function
                plugin_folders_created.append(output_folder)
            else:
                failed_patches.append(patch_name)
                print(f"  ❌ {patch_name} plugin processing failed")
        
        # Run process_audio.py on successfully created plugin folders (unless skipped)
        audio_success_count = 0
        audio_failed_folders = []
        
        if plugin_folders_created and not args.skip_audio_processing:
            print(f"\n" + "-"*60)
            print(f"RUNNING AUDIO PROCESSING ON PLUGIN FOLDERS...")
            print("-"*60)
            
            for j, plugin_folder in enumerate(plugin_folders_created, 1):
                folder_name = os.path.basename(plugin_folder)
                print(f"\n[{j}/{len(plugin_folders_created)}] Audio processing: {folder_name}")
                
                audio_success = run_process_audio_on_folder(plugin_folder)
                if audio_success:
                    audio_success_count += 1
                else:
                    audio_failed_folders.append(folder_name)
        elif plugin_folders_created and args.skip_audio_processing:
            print(f"\n⏭️  Skipping audio processing as requested")
        
        # Final summary
        print("\n" + "="*60)
        if success_count == total_patches:
            print("✅ ALL PLUGIN PROCESSING COMPLETED SUCCESSFULLY!")
        else:
            print("⚠️  PLUGIN PROCESSING COMPLETED WITH SOME FAILURES")
        print("="*60)
        print(f"Total patches: {total_patches}")
        print(f"Plugin processing successful: {success_count}")
        print(f"Plugin processing failed: {len(failed_patches)}")
        
        if plugin_folders_created and not args.skip_audio_processing:
            print(f"Audio processing successful: {audio_success_count}")
            print(f"Audio processing failed: {len(audio_failed_folders)}")
        elif args.skip_audio_processing:
            print(f"Audio processing: skipped")
        
        if failed_patches:
            print(f"\nFailed plugin processing:")
            for patch_name in failed_patches:
                print(f"  • {patch_name}")
        
        if plugin_folders_created and not args.skip_audio_processing and audio_failed_folders:
            print(f"\nFailed audio processing:")
            for folder_name in audio_failed_folders:
                print(f"  • {folder_name}")
        
        # Exit with error if there were failures
        has_audio_failures = not args.skip_audio_processing and plugin_folders_created and audio_failed_folders
        if failed_patches or has_audio_failures:
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\nProcessing interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
