"""
Configuration helper - loads settings from both config.py and local_config.json
"""
import json
import os
import sys

# Import defaults from main config
from config import *

# Local config file (created by setup.py)
LOCAL_CONFIG_FILE = 'local_config.json'


def load_local_config():
    """Load local configuration if it exists."""
    if os.path.exists(LOCAL_CONFIG_FILE):
        try:
            with open(LOCAL_CONFIG_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load local config: {e}")
    return {}


def test_configuration():
    """Test if the current configuration is valid."""
    try:
        # Import the setup module to use its test functions
        utils_path = os.path.join(os.path.dirname(__file__), 'utils')
        if utils_path not in sys.path:
            sys.path.append(utils_path)
        from setup import test_setup
        return test_setup()
    except ImportError:
        print("Warning: Could not import setup module for testing")
        return True  # Assume it's ok if we can't test


def run_setup_if_needed():
    """Run setup if configuration is invalid."""
    if not test_configuration():
        print("Configuration test failed. Starting setup...")
        try:
            import subprocess
            setup_path = os.path.join(os.path.dirname(__file__), 'utils', 'setup.py')
            result = subprocess.run([sys.executable, setup_path])
            return result.returncode == 0
        except Exception as e:
            print(f"Failed to run setup: {e}")
            return False
    return True


# Load local configuration and override defaults
local_config = load_local_config()

# Set device-specific settings from local config or use defaults
AUDIO_DEVICE = local_config.get('audio_device', None)  # None = system default
MIDI_PORT_NAME = local_config.get('midi_port_name', 'No MIDI Port Configured')

# Override sample rate if specified in local config
if 'sample_rate' in local_config:
    SAMPLE_RATE = local_config['sample_rate']
