# RoboSampla - Automated Synthesizer Sampler

An automated tool for sampling synthesizers by playing MIDI notes and recording the audio output.
Edit config.py and patches.json

# Commands

python3 main.py

python3 program_change.py 69

## File Structure

```
robosampla/
├── main.py              # Main application entry point
├── config.py            # Configuration settings
├── midi_utils.py        # MIDI communication utilities
├── audio_utils.py       # Audio recording utilities
├── patch_utils.py       # Patch management utilities
├── recorder.py          # Core recording functionality
├── patches.json         # Patch definitions
├── requirements.txt     # Python dependencies
├── record.py           # Original monolithic file (legacy)
└── README.md           # This file
```

## Usage

### Quick Start

```bash
python main.py
```

### Configuration

Edit `config.py` to set:

- MIDI port name
- Audio device index
- Sample rate
- Patches file location

### Patches

Define your synthesizer patches in `patches.json`. Each patch includes:

- Note range to sample
- MIDI channel, program change, and bank select
- Timing settings (note duration, gaps)
- Velocity settings

## Modules

### main.py

Entry point that orchestrates the entire sampling process.

### config.py

Central configuration for MIDI and audio settings.

### midi_utils.py

- MIDI message sending (note on/off, program change, bank select)
- MIDI port listing
- Note number to name conversion

### audio_utils.py

- Audio device listing and management
- Audio recording with automatic channel detection
- WAV file saving

### patch_utils.py

- JSON patch file loading
- Safe filename generation
- Folder creation for organized output

### recorder.py

- Main recording logic
- Patch playback with optional audio recording
- Orchestrates MIDI and audio operations

## Dependencies

Install required packages:

```bash
pip install -r requirements.txt
```

Required packages:

- mido (MIDI handling)
- sounddevice (audio recording)
- scipy (audio file I/O)
- numpy (audio processing)

## Output Structure

When recording audio, files are organized as:

```
PatchName/
├── C2_36.wav
├── Csharp2_37.wav
├── D2_38.wav
└── ...
```

Each audio file is named with the note name and MIDI number for easy identification.
