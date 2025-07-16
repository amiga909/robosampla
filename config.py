"""
Configuration settings for the robosampla application.
"""

# MIDI settings
MIDI_PORT_NAME = 'iConnectAudio4+ DIN'

# Audio recording settings
SAMPLE_RATE = 44100  # Sample rate in Hz
AUDIO_DEVICE = 0     # Audio device index (use None for default)

# Audio processing settings
SILENCE_THRESHOLD_DB = -50.0  # Threshold in dB for silence detection, min. DB audible sound must have
FADE_IN_MS = 20.0             # Fade in duration in milliseconds
FADE_OUT_MS = 20.0            # Fade out duration in milliseconds
TARGET_PEAK_DB = -1.0        # Target peak level in dB for patch normalization

# Default patch filename
PATCHES_FILE = '_patches.json'

# Output directory for recorded samples
OUTPUT_DIR = '_output'
