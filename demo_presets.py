#!/usr/bin/env python3
"""
Demo script showing how to use the enhanced preset system based on GitHub discussion
"""

import sys
import os
sys.path.append('utils')

from process_plugins import (
    list_available_plugins, 
    load_plugin_universal, 
    save_plugin_preset, 
    load_plugin_preset,
    get_plugin_presets
)

def demo_preset_workflow():
    """Demonstrate the complete preset workflow from GitHub discussion."""
    print("="*60)
    print("PRESET SYSTEM DEMO (Based on GitHub Issue #187)")
    print("="*60)
    
    # Load a plugin
    plugins = list_available_plugins()
    if not plugins:
        print("No plugins found")
        return
    
    plugin_name, plugin_path = plugins[0]  # Use first plugin
    print(f"\nLoading plugin: {plugin_name}")
    plugin = load_plugin_universal(plugin_path)
    
    if not plugin:
        print("Failed to load plugin")
        return
    
    # Show original parameters
    print(f"\n📋 Original parameter values:")
    if hasattr(plugin, 'parameters') and plugin.parameters:
        original_params = {param_name: getattr(plugin, param_name) 
                         for param_name in plugin.parameters.keys()}
        for param_name, param_value in original_params.items():
            print(f"  {param_name}: {param_value}")
    
    # Modify some parameters (simulate user editing)
    print(f"\n🎛️  Modifying parameters...")
    if hasattr(plugin, 'parameters') and plugin.parameters:
        param_names = list(plugin.parameters.keys())
        if 'distortion' in param_names:
            setattr(plugin, 'distortion', 0.8)
            print(f"  Changed distortion to: 0.8")
        if 'frequency' in param_names:
            setattr(plugin, 'frequency', 0.8)  # Keep within 0.0-1.0 range
            print(f"  Changed frequency to: 0.8")
        if 'level' in param_names:
            setattr(plugin, 'level', 0.7)
            print(f"  Changed level to: 0.7")
        if 'resonance' in param_names:
            setattr(plugin, 'resonance', 0.3)
            print(f"  Changed resonance to: 0.3")
    
    # Save as JSON preset (GitHub method)
    print(f"\n💾 Saving JSON preset...")
    success = save_plugin_preset(plugin, "demo_json_preset", "json")
    
    # Save as binary preset (GitHub PR #297 method)
    print(f"\n💾 Saving binary preset...")
    success = save_plugin_preset(plugin, "demo_binary_preset", "binary")
    
    # Reset parameters to original values
    print(f"\n🔄 Resetting to original values...")
    if hasattr(plugin, 'parameters') and plugin.parameters:
        for param_name, original_value in original_params.items():
            setattr(plugin, param_name, original_value)
        print(f"  Parameters reset to original values")
    
    # Show current (reset) parameters
    print(f"\n📋 Current parameter values (after reset):")
    if hasattr(plugin, 'parameters') and plugin.parameters:
        for param_name in plugin.parameters.keys():
            current_value = getattr(plugin, param_name)
            print(f"  {param_name}: {current_value}")
    
    # Test preset discovery
    print(f"\n🔍 Discovering available presets...")
    presets = get_plugin_presets(plugin)
    for preset in presets:
        print(f"  Found: {preset}")
    
    # Load JSON preset
    if any("JSON Preset: demo_json_preset" in p for p in presets):
        print(f"\n📂 Loading JSON preset...")
        success = load_plugin_preset(plugin, "JSON Preset: demo_json_preset")
        
        print(f"\n📋 Parameter values after loading JSON preset:")
        if hasattr(plugin, 'parameters') and plugin.parameters:
            for param_name in plugin.parameters.keys():
                current_value = getattr(plugin, param_name)
                print(f"  {param_name}: {current_value}")
    
    # Reset again and test binary preset
    print(f"\n🔄 Resetting again for binary preset test...")
    if hasattr(plugin, 'parameters') and plugin.parameters:
        for param_name, original_value in original_params.items():
            setattr(plugin, param_name, original_value)
    
    # Load binary preset  
    if any("Binary Preset: demo_binary_preset" in p for p in presets):
        print(f"\n📂 Loading binary preset...")
        success = load_plugin_preset(plugin, "Binary Preset: demo_binary_preset")
        
        print(f"\n📋 Parameter values after loading binary preset:")
        if hasattr(plugin, 'parameters') and plugin.parameters:
            for param_name in plugin.parameters.keys():
                current_value = getattr(plugin, param_name)
                print(f"  {param_name}: {current_value}")
    
    print(f"\n✅ Demo complete! Check utils/presets/ and utils/raw_presets/ for saved files.")

if __name__ == '__main__':
    demo_preset_workflow()
