"""
Configuration settings for the robosampla application.
"""

# Default MIDI parameters (can be overridden in patch JSON files)
DEFAULT_MIDI_CHANNEL = 0
DEFAULT_BANK_MSB = 0
DEFAULT_BANK_LSB = 0
DEFAULT_VELOCITY = 127

# Audio recording settings
SAMPLE_RATE = 44100  # Sample rate in Hz

# Audio processing settings
SILENCE_THRESHOLD_DB = -40.0  # Threshold in dB for silence detection, all audio below this value is treated as silence
FADE_IN_MS = 3.0              # Fade in duration in milliseconds
FADE_OUT_MS = 3.0             # Fade out duration in milliseconds
TARGET_PEAK_DB = -1.0         # Target peak level in dB for normalization
TRIM_END_MS = 100.0           # Duration to trim from end of recording to remove artifacts (in milliseconds)

# Default patch filename
PATCHES_FILE = '_patches.json'

# Output directory for recorded samples
OUTPUT_DIR = '_output'
