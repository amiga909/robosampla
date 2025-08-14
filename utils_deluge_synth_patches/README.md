# Deluge Synth Patches Generator

This utility generates XML patch files for the Synthstrom Deluge from organized sample folders.

## Overview

The script processes a folder containing subfolders of audio samples (WAV, AIF, AIFF) and generates corresponding XML files that can be loaded as synth patches on the Deluge. Each subfolder becomes a separate patch with sample ranges mapped across MIDI notes.

## Prerequisites

- Node.js installed on your system
- `wavefile` package installed (`npm install wavefile`)

## Installation

1. Navigate to the utils_deluge_synth_patches directory
2. Install dependencies:
   ```bash
   npm install wavefile
   ```

## Usage

```bash
node index.js <processing_folder> <target_folder>
```

### Parameters

- `<processing_folder>`: The local folder containing your sample subfolders
- `<target_folder>`: The folder name to use in Deluge XML file paths (how samples will be referenced on the Deluge)

### Example

```bash
node index.js CasioCZ230S MyDelugeKit
```

This will:

- Process samples from the local `CasioCZ230S` folder
- Generate XML files that reference samples in `SAMPLES/MyDelugeKit/...` paths
- Allow you to organize your local samples differently from how they appear on the Deluge

## Folder Structure

Your local processing folder should be organized like this:

```
CasioCZ230S/                    # <-- processing_folder
├── Patch1/
│   ├── sample1.wav
│   ├── sample2.wav
│   └── sample3.wav
├── Patch2/
│   ├── sample1.wav
│   └── sample2.wav
└── Patch3/
    └── sample1.wav
```

The generated XML files will reference samples using the target folder name:

```xml
<!-- Example path in generated XML -->
<fileName>SAMPLES/MyDelugeKit/Patch1/sample1.wav</fileName>
```

## Output

- **XML Files**: Generated in a dedicated `XML` folder with names like `Patch1.XML`, `Patch2.XML`, etc.
- **Filename Sanitization**: Non-ASCII characters in patch names are converted to underscores for compatibility
- **Sample Mapping**: Samples are automatically mapped to MIDI notes based on filename analysis
- **Deluge Compatibility**: XML files are formatted for direct use with Synthstrom Deluge

## Configuration

You can modify these settings at the top of `index.js`:

- `MIN_SAMPLE_LENGTH`: Minimum sample length threshold (default: 0)
- `DELETE_MIN_SAMPLE_SOURCE`: Whether to delete source folders below minimum length (default: false)
- `DELUGE_SAMPLES_ROOT`: Root path for samples in generated XML (default: "SAMPLES")

## Features

- **Automatic MIDI Mapping**: Samples are mapped to MIDI notes based on filename patterns
- **Sample Range Detection**: Automatically calculates sample start/end positions
- **Transpose Calculation**: Sets appropriate transpose values for each sample
- **Release Time**: Automatically sets envelope release time based on folder name
- **File Validation**: Only processes supported audio formats (WAV, AIF, AIFF)
- **Filename Sanitization**: Converts non-ASCII characters to underscores for file system compatibility
- **Organized Output**: All XML files are generated in a dedicated `XML` folder

## Error Handling

The script will:

- Exit with an error if both folder arguments are not provided
- Show available folders if the specified processing folder doesn't exist
- Skip folders that don't meet minimum sample length requirements
- Display processing statistics upon completion

## Use Cases

This separation of processing and target folders is useful when:

- You want to organize samples locally different from how they appear on the Deluge
- You're processing samples from various sources but want them grouped under a single Deluge folder
- You need to rename the sample collection for the Deluge without reorganizing your local files

## Output Example

```
Processing samples from: CasioCZ230S
Target Deluge folder: MyDelugeKit
Created XML output directory: /path/to/utils_deluge_synth_patches/XML
wavFolder { name: 'Patch1', ... }
wavFolder path /path/to/CasioCZ230S/Patch1
Generated: Patch1.XML
wavFolder { name: 'Patch2', ... }
wavFolder path /path/to/CasioCZ230S/Patch2
Generated: Patch2.XML
stats { lengths: { '0': 3, '1': 2 } }
```

## Notes

- Ensure your `template.XML` file exists in the same directory
- The script expects the `xml-helpers.js` module for XML processing functions
- Generated XML files use the Deluge's expected file path format
