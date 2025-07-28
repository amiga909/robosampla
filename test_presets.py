#!/usr/bin/env python3
"""
Test script for the enhanced preset system based on GitHub discussion
"""

import sys
import os
sys.path.append('utils')

from process_plugins import list_available_plugins, load_plugin_universal, get_plugin_presets

def test_preset_system():
    """Test the enhanced preset system functionality."""
    print("="*60)
    print("TESTING ENHANCED PRESET SYSTEM")
    print("="*60)
    
    # Test plugin discovery
    print("\n1. Testing plugin discovery...")
    plugins = list_available_plugins()
    
    if not plugins:
        print("No plugins found. Cannot test preset system.")
        return
    
    print(f"Found {len(plugins)} plugins")
    
    # Test loading the first plugin
    print(f"\n2. Testing plugin loading with first plugin...")
    plugin_name, plugin_path = plugins[0]
    print(f"Loading: {plugin_name}")
    
    plugin = load_plugin_universal(plugin_path)
    if not plugin:
        print("Failed to load plugin")
        return
    
    print(f"✅ Successfully loaded: {type(plugin).__name__}")
    
    # Test preset discovery
    print(f"\n3. Testing preset discovery...")
    presets = get_plugin_presets(plugin)
    print(f"Found {len(presets)} presets:")
    for preset in presets:
        print(f"  • {preset}")
    
    # Test parameter access (from GitHub discussion)
    print(f"\n4. Testing parameter access (GitHub issue #187 method)...")
    if hasattr(plugin, 'parameters') and plugin.parameters:
        print(f"Plugin has {len(plugin.parameters)} parameters:")
        param_value_dict = {parameter_name: getattr(plugin, parameter_name) 
                          for parameter_name in plugin.parameters.keys()}
        for param_name, param_value in list(param_value_dict.items())[:5]:  # Show first 5
            print(f"  {param_name}: {param_value}")
        if len(param_value_dict) > 5:
            print(f"  ... and {len(param_value_dict)-5} more parameters")
    else:
        print("Plugin has no accessible parameters")
    
    # Test raw_state support (GitHub PR #297)
    print(f"\n5. Testing raw_state support (GitHub PR #297)...")
    if hasattr(plugin, 'raw_state'):
        try:
            state_size = len(plugin.raw_state)
            print(f"✅ Plugin supports raw_state: {state_size} bytes")
        except Exception as e:
            print(f"❌ Error accessing raw_state: {e}")
    else:
        print("❌ Plugin doesn't support raw_state")
    
    print(f"\n6. Summary:")
    print(f"  Plugin loaded: ✅")
    print(f"  Parameters accessible: {'✅' if hasattr(plugin, 'parameters') and plugin.parameters else '❌'}")
    print(f"  Raw state support: {'✅' if hasattr(plugin, 'raw_state') else '❌'}")
    print(f"  Editor support: {'✅' if hasattr(plugin, 'show_editor') else '❌'}")
    print(f"  Presets found: {len(presets)}")

if __name__ == '__main__':
    test_preset_system()
