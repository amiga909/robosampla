# Enhanced Preset System for Pedalboard Plugins

Based on **GitHub Issue #187: Save and Load Presets Automatically for VST3 Plugins?**

## Problem Summary

The original preset system in your `process_plugins.py` was limited to only `.vstpreset` files for VST3 plugins, and many users reported issues with:

- Not all plugins exposing their parameters
- Limited preset format support
- VST preset compatibility issues
- No way to save custom parameter settings

## Solutions Implemented

### 1. **JSON Parameter Presets** (GitHub Issue #187 Method)

- **Source**: Discussion by @psobot in GitHub issue #187
- **How it works**: Saves/loads individual plugin parameters as JSON
- **Advantages**: Human-readable, cross-plugin compatible, parameter-specific
- **Usage**: Perfect for sharing specific parameter configurations

```python
# Save parameters as JSON
param_value_dict = {parameter_name: getattr(plugin, parameter_name)
                   for parameter_name in plugin.parameters.keys()}
```

### 2. **Binary Raw State Presets** (GitHub PR #297 Method)

- **Source**: GitHub PR #297 merged in pedalboard v0.9.6
- **How it works**: Saves/loads complete plugin internal state as binary data
- **Advantages**: Captures ALL plugin state including UI state and hidden parameters
- **Usage**: Complete plugin state backup/restore

```python
# Save complete plugin state
with open("preset.bin", "wb") as f:
    f.write(plugin.raw_state)
```

### 3. **WrappedBool Handling** (GitHub Issue Fix)

- **Problem**: Boolean parameters caused JSON serialization errors
- **Solution**: Unwrap boolean values before JSON serialization
- **Code**: Handles both old and new pedalboard import paths

```python
from pedalboard._pedalboard import WrappedBool  # New path
param_value_dict = {k: (bool(v) if isinstance(v, WrappedBool) else v)
                   for k, v in param_value_dict.items()}
```

## New Features Added

### 1. **Multiple Preset Types**

- **VST Presets**: Traditional `.vstpreset` files
- **JSON Presets**: Parameter-based presets (human-readable)
- **Binary Presets**: Complete plugin state (comprehensive)

### 2. **Interactive Preset Creation**

After using `show_editor()`, users can now:

- Save current settings as JSON preset (parameters only)
- Save current settings as binary preset (complete state)
- Choose preset format based on plugin capabilities

### 3. **Enhanced Preset Discovery**

The system now scans for:

- External `.vstpreset` files in standard locations
- JSON presets in `utils/presets/`
- Binary presets in `utils/raw_presets/`

### 4. **Automatic Preset Format Selection**

- If plugin supports `raw_state`: Offers both JSON and binary options
- If plugin only has parameters: Uses JSON format
- Fallback to VST presets for compatible plugins

## File Structure

```
utils/
├── presets/              # JSON parameter presets
│   └── my_preset.json
├── raw_presets/          # Binary state presets
│   └── my_preset.bin
└── process_plugins.py    # Enhanced with preset system
```

## Usage Examples

### Interactive Workflow

```bash
python utils/process_plugins.py
# 1. Select plugin
# 2. Open editor with show_editor()
# 3. Adjust parameters in GUI
# 4. Save as preset (JSON or binary)
# 5. Select saved preset for processing
```

### Programmatic Usage

```python
from utils.process_plugins import save_plugin_preset, load_plugin_preset

# Save current plugin state
save_plugin_preset(plugin, "my_settings", "json")     # Parameters only
save_plugin_preset(plugin, "my_settings", "binary")   # Complete state

# Load preset
load_plugin_preset(plugin, "JSON Preset: my_settings")
load_plugin_preset(plugin, "Binary Preset: my_settings")
```

## Advantages Over Original System

| Feature                    | Original | Enhanced                    |
| -------------------------- | -------- | --------------------------- |
| Preset formats             | VST only | VST + JSON + Binary         |
| Parameter capture          | Limited  | Complete via GitHub methods |
| Cross-plugin compatibility | Poor     | Excellent (JSON)            |
| UI state preservation      | No       | Yes (Binary)                |
| User creation              | No       | Yes (Interactive)           |
| Human readable             | No       | Yes (JSON)                  |
| Error handling             | Basic    | Robust with fallbacks       |

## Compatibility

- **AU Plugins**: Full support with parameter and raw_state access
- **VST3 Plugins**: Full support where compatible
- **VST2 Plugins**: Parameter support (limited raw_state)
- **Older Pedalboard**: Graceful fallbacks for missing features

## GitHub References

- **Issue #187**: Original preset discussion and JSON method
- **PR #297**: Binary raw_state implementation
- **Various comments**: WrappedBool fixes and import path updates

This implementation combines the best solutions from the GitHub discussion to provide a comprehensive preset system that works reliably across different plugin formats and pedalboard versions.
