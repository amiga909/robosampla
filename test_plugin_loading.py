#!/usr/bin/env python3
"""
Test script to isolate plugin loading issues
"""

from pedalboard import load_plugin
import os

# Test different plugin loading approaches
test_plugins = [
    # Try AU first
    "/Library/Audio/Plug-Ins/Components/FuzzPlus3.component",
    "/Library/Audio/Plug-Ins/Components/GSatPlus.component", 
    "/Library/Audio/Plug-Ins/Components/ValhallaSupermassive.component",
    
    # Try VST3
    "/Library/Audio/Plug-Ins/VST3/FuzzPlus3.vst3",
    "/Library/Audio/Plug-Ins/VST3/GSatPlus.vst3",
    "/Library/Audio/Plug-Ins/VST3/ValhallaSupermassive.vst3",
    
    # Try VST2
    "/Library/Audio/Plug-Ins/VST/GSatPlus.vst",
    "/Library/Audio/Plug-Ins/VST/ValhallaSupermassive.vst",
]

for plugin_path in test_plugins:
    if os.path.exists(plugin_path):
        print(f"\n=== Testing: {os.path.basename(plugin_path)} ===")
        print(f"Path: {plugin_path}")
        print(f"Is directory: {os.path.isdir(plugin_path)}")
        
        try:
            plugin = load_plugin(plugin_path)
            print(f"✅ SUCCESS: Loaded {type(plugin).__name__}")
            
            # Try to get some basic info
            if hasattr(plugin, 'name'):
                print(f"  Plugin name: {plugin.name}")
            if hasattr(plugin, 'parameters'):
                print(f"  Parameters: {list(plugin.parameters.keys())[:5]}...")  # First 5 params
                
            break  # Stop on first success
            
        except Exception as e:
            print(f"❌ FAILED: {e}")
    else:
        print(f"⚠️  Not found: {plugin_path}")

print("\n=== Test completed ===")
